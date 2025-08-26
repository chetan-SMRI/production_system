import frappe
import pandas as pd
from frappe.utils import add_days, getdate,nowdate

def clean(val, default=None):
    """Convert pandas NaN/None to clean Python values."""
    if pd.isna(val):
        return default
    if isinstance(val, str) and val.strip().lower() == "nan":
        return default
    return val

@frappe.whitelist()
def generate_item_tasks(project_name):
    project = frappe.get_doc("Production Project", project_name)
    if not project.template_file:
        frappe.throw("No Excel template attached to project.")

    file_doc = frappe.get_doc("File", {"file_url": project.template_file})
    file_path = file_doc.get_full_path()
    df = pd.read_excel(file_path)

    for item in project.items:
        for _, row in df.iterrows():
            task_type = clean(row.get("Task Type"))
            dependency_type = clean(row.get("Dependency Type"), "None").strip()

            # ✅ Create only Item tasks with no dependency
            if task_type == "Item" and (not dependency_type or dependency_type == "None"):
                create_task_from_row(project, row, dependency_type, item=item.item_name)

def create_task_from_row(project, row, dependency_type=None, item=None):
    """
    Create a Production Task from an excel row. Skip if identical task already exists.
    Returns the task doc (existing or new).
    """
    task_subject = str(clean(row.get("Task Subject"), "")).strip()
    task_type = str(clean(row.get("Task Type"), "")).strip()
    milestone = clean(row.get("Milestone"))
    assigned_to = clean(row.get("Assigned To"))
    dependency_target = clean(row.get("Dependency Target"))

    # Duplicate check (project + task_subject + task_type + optional item)
    filters = {"project": project.name, "task_subject": task_subject, "task_type": task_type}
    if item:
        filters["item"] = item

    existing = frappe.get_all("Production Task", filters=filters, fields=["name"], limit=1)
    if existing:
        return frappe.get_doc("Production Task", existing[0]["name"])

    task = frappe.new_doc("Production Task")
    task.project = project.name
    task.milestone = milestone
    task.task_subject = task_subject
    task.task_type = task_type
    if item:
        task.item = item
    task.assigned_to = assigned_to
    task.status = "Pending"

    # TAT / dates
    tat_days = clean(row.get("TAT (in days)"))
    try:
        if tat_days not in (None, "", "None"):
            tat_days = int(tat_days)
            tat_based_on = str(clean(row.get("TAT Based On"), "Task Creation Date")).strip()
            if tat_based_on == "Project Start Date" and project.get("start_date"):
                start_dt = getdate(project.start_date)
            else:
                start_dt = getdate(nowdate())
            task.start_date = start_dt
            task.due_date = add_days(start_dt, tat_days)
    except Exception:
        # ignore bad TAT values
        pass

    task.insert(ignore_permissions=True)
    frappe.db.commit()
    return task
