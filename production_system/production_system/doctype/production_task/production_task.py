import frappe
from frappe.model.document import Document
import pandas as pd
from production_system.api import create_task_from_row,clean
class ProductionTask(Document):
    def validate(doc):
        if doc.status == "Completed" or doc.status == "Cancelled":
            on_task_completed(doc)

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
        print(dep_type)
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
            # try with child docname (it.name), fallback to an item_code field if present
            found = frappe.get_all("Production Task",
                                   filters={
                                       "project": project.name,
                                       "item": it.name,
                                       "task_subject": dep_target,
                                       "task_type": "Item"
                                   },
                                   fields=["status"],
                                   limit=1)
            if not found and it.get("item_code"):
                found = frappe.get_all("Production Task",
                                       filters={
                                           "project": project.name,
                                           "item": it.get("item_code"),
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
