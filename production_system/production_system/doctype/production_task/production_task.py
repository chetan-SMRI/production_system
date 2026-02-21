import frappe
from frappe.model.document import Document
from frappe.utils import today,now
import pandas as pd
from production_system.api import create_task_from_row,clean
class ProductionTask(Document):
    def validate(doc):
        if doc.status == "Completed" or doc.status == "Cancelled":
            on_task_completed(doc)
            doc.completion_time = now()
            doc.completed_by = frappe.session.user
        if doc.is_parent:
            doc.update_parent_progress()
    
    def on_update(doc):
        update_milestone_progress(doc)
        if doc.is_child:
            pt = frappe.get_doc('Production Task', doc.parent_task)
            pt.update_parent_progress()
            pt.save()

    
    def update_parent_progress(doc):
        child_tasks = frappe.get_all('Production Task', [['parent_task', '=', doc.name]], ['name','status'])
        total_tasks = len(child_tasks)
        completed_tasks = 0
        for each in child_tasks:
            if each.get('status') in ['Completed','Cancelled']:
                completed_tasks += 1
        if total_tasks == 0:
            perc = 0
            # doc.percentage_completion = 0
            doc.status = 'Pending'
        else:
            doc.status = 'Pending'
            perc = 100*(completed_tasks/total_tasks)
            # doc.percentage_completion = perc
            if perc > 0 and perc < 100:
                doc.status = 'In Progress'
            elif perc == 100:
                doc.status = 'Completed'
        # doc.save()
    # def on_trash(doc):
    #     update_milestone_progress(doc)
    

# def update_parent_progress(doc):
#     pt = frappe.get_doc('Production Task', doc.parent_task)
#     pt.calculate_parent_progress()

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
            name = it.item_name.strip() + ' (UID: ' + str(it.uid).strip() + ')'
            found = frappe.get_value("Production Task",
                                   {
                                       "project": project.name,
                                       "item": name,
                                       "task_subject": dep_target,
                                       "task_type": "Item"
                                   },
                                   ["name","status"],
                                   as_dict=True
                                   )
            
            if found and found.get("name") == task.name:
                found['status'] = task.status
            if (not found or found.get("status") not in ["Completed", "Cancelled"]):
                all_items_ok = False
                break
            else:
                print("Creating Aggregate Task")

        if all_items_ok:
            # create the aggregate project task
            create_task_from_row(project, raw, dependency_type="Aggregate")

    # finally commit any changes
    frappe.db.commit()










def update_milestone_progress(doc, method=None):
    """Update milestones & project percentage when a Task is completed/cancelled."""
    if not doc.project:
        return

    project = frappe.get_doc("Production Project", doc.project)
    recalc_project_progress(project)


import pandas as pd

def get_direct_tasks_for_milestone(project, milestone_name):
    task_list = []
    for direct_task in project.direct_tasks:
        if direct_task.milestone == milestone_name:
            task_list.append(direct_task.task)
    return task_list

def recalc_project_progress(project):
    """Recalculate milestone % and project % from Excel template + Task status."""
    # if isinstance(project, str):
    #     project = frappe.get_doc("Production Project", project)

    # load excel template
    if not project.template_file:
        frappe.throw("No template file attached")

    file_doc = frappe.get_doc("File", {"file_url": project.template_file})
    file_path = file_doc.get_full_path()
    df = pd.read_excel(file_path).fillna("")

    total_weighted = 0
    total_weights = 0

    for milestone in project.milestones:
        # ---- expected count from template ----
        template_rows = df[df["Milestone"].astype(str).str.strip() == milestone.milestone_name.strip()]
        base_count = len(template_rows)
        item_tasks = df[df["Milestone"].astype(str).str.strip() == milestone.milestone_name.strip()][df["Task Type"].astype(str).str.strip() == "Item"]

        direct_task_count = len(get_direct_tasks_for_milestone(project,milestone.milestone_name)) # get if any direct task also exists for the milestone(manually created task)
        base_count += direct_task_count
        item_task_count = len(item_tasks)
        print(base_count,item_task_count)
        project_task_count = base_count - item_task_count
        if project.initialised_item_tasks:
            expected_tasks = project_task_count + (item_task_count * len(project.items))
        else:
            expected_tasks = base_count
        print("Milestone", milestone.milestone_name,project_task_count,item_task_count,direct_task_count)
        # ---- actual status from Task doctype ----
        completed = frappe.db.count("Production Task", {
            "project": project.name,
            "milestone": milestone.milestone_name,
            "status": ["in", ["Completed", "Cancelled"]],
            "is_parent": False
        })
        open_tasks = frappe.db.count("Production Task", {
            "project": project.name,
            "milestone": milestone.milestone_name,
            "status": ["not in", ["Completed", "Cancelled"]],
            "is_parent": False
        })

        # any remaining = not yet created
        not_created = expected_tasks - (completed + open_tasks)
        if not_created < 0:
            not_created = 0

        # ---- percentage ----
        milestone.percentage_completion = round((completed / expected_tasks) * 100, 2) if expected_tasks else 0
        # print(milestone.milestone_name,milestone.percentage_completion, completed , expected_tasks)
        milestone.status = (
            "Completed" if milestone.percentage_completion == 100 else
            "In Progress" if milestone.percentage_completion > 0 else
            "Pending"
        )

        # ---- project weighted contribution ----
        total_weighted += (milestone.percentage_completion or 0) * (milestone.weight or 1)
        total_weights += (milestone.weight or 1)

    project.percentage_completion = round(total_weighted / total_weights, 2) if total_weights else 0
    project.save(ignore_permissions=True)
    frappe.db.commit()
    return project
