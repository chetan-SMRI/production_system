import frappe
from frappe.model.document import Document
import pandas as pd
from production_system.api import create_task_from_row,clean
class ProductionTask(Document):
    def validate(doc):
        if doc.status == "Completed" or doc.status == "Cancelled":
            on_task_completed(doc)
            update_milestone_progress(doc)

def on_task_completed(task):
    """
    When a task is marked Completed — create dependent tasks according to the excel template.
    This will:
      - create Task dependencies (project-level tasks)
      - create Task(Item) dependencies (item-level tasks for the same item)
      - create Aggregate (project) tasks once every item has the required item-task in Completed state
    """
    # load project
    if not getattr(task, "project", None):
        return
    project = frappe.get_doc("Production Project", task.project)

    if not project.template_file:
        # nothing to do if no template attached
        return

    file_doc = frappe.get_doc("File", {"file_url": project.template_file})
    df = pd.read_excel(file_doc.get_full_path()).fillna("")

    # Normalize completed task subject for comparisons
    completed_subject = (task.task_subject or "").strip()

    # 1) Create Task (project-level) or Task(Item) (item-level) when dependency target matches completed_subject
    for _, raw in df.iterrows():
        dep_type = str(clean(raw.get("Dependency Type"), "")).strip()
        dep_target = str(clean(raw.get("Dependency Target"), "")).strip()
        if not dep_type or not dep_target:
            continue

        # Project-level dependency
        if dep_type == "Task" and dep_target == completed_subject:
            create_task_from_row(project, raw, dependency_type="Task")

        # Item-level dependency -> only when the completed task is an Item task
        if dep_type == "Task(Item)" and task.task_type == "Item" and dep_target == completed_subject:
            # create for the same item as the completed task
            create_task_from_row(project, raw, dependency_type="Task(Item)", item=task.item)

    # 2) Handle Aggregate rows: ensure every project item has the dependency_target task and is Completed
    for _, raw in df.iterrows():
        dep_type = str(clean(raw.get("Dependency Type"), "")).strip()
        if dep_type != "Aggregate":
            continue
        
        dep_target = str(clean(raw.get("Dependency Target"), "")).strip()     # the item-task subject we wait for
        aggregate_subject = str(clean(raw.get("Task Subject"), "")).strip()   # the project-level task to create

        # skip if aggregate task already exists
        exists = frappe.get_all("Production Task",
                                filters={"project": project.name, "task_subject": aggregate_subject, "task_type": clean(raw.get("Task Type"), "Project")},
                                fields=["name"],
                                limit=1)
        if exists:
            continue
        
        
        # verify for every item in project.items that:
        #  - there exists an Item task with subject == dep_target
        #  - AND its status == "Completed"
        all_items_ok = True
        if not project.items:
            continue
        
        for it in project.items or []:
            # try with child docname (it.item_name)
            found = frappe.get_all("Production Task",
                                   filters={
                                       "project": project.name,
                                       "item": it.item_name,
                                       "task_subject": dep_target,
                                       "task_type": "Item"
                                   },
                                   fields=["status"],
                                   limit=1)
            
            if not found or found[0].get("status") != "Completed":
                all_items_ok = False
                break

        if all_items_ok:
            # create the aggregate project task
            create_task_from_row(project, raw, dependency_type="Aggregate")

    # finally commit any changes
    frappe.db.commit()










def update_milestone_progress(doc, method=None):
    """Update milestones & project percentage when a Task is completed/cancelled."""
    if not doc.project or doc.doctype != "Task":
        return

    project = frappe.get_doc("Production Project", doc.project)
    recalc_project_progress(project)


@frappe.whitelist()
def recalc_project_progress(project):
    """Recalculate all milestones & overall project completion %."""
    if isinstance(project, str):
        project = frappe.get_doc("Production Project", project)

    total_weighted = 0
    total_weights = 0

    for milestone in project.milestones:  # child table inside Production Project
        expected_tasks = get_expected_task_count(project, milestone)
        completed, open_tasks = get_actual_task_status(project, milestone)

        not_created = expected_tasks - (completed + open_tasks)
        milestone.progress = (completed / expected_tasks * 100) if expected_tasks else 0

        # Weight contribution
        total_weighted += (milestone.progress or 0) * (milestone.weight or 1)
        total_weights += (milestone.weight or 1)

    # Update overall project completion %
    project.percentage_completion = total_weighted / total_weights if total_weights else 0
    project.save(ignore_permissions=True)
    return project


def get_expected_task_count(project, milestone):
    """Return how many tasks *should* exist for this milestone."""
    template_tasks = [t for t in project.template_file if t.milestone == milestone.milestone_name]
    base_count = len(template_tasks)

    if project.initialised_item_tasks:
        return base_count * len(project.items)
    return base_count


def get_actual_task_status(project, milestone):
    """Return (completed_count, open_count) for this milestone."""
    filters = {"project": project.name, "milestone": milestone.milestone_name}
    tasks = frappe.get_all("Task", filters=filters, fields=["status"])

    completed = sum(1 for t in tasks if t.status == "Completed")
    open_tasks = sum(1 for t in tasks if t.status not in ["Completed", "Cancelled"])
    return completed, open_tasks
