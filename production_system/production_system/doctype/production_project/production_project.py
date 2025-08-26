import frappe
import pandas as pd
from frappe.utils import add_days, getdate
from frappe.model.document import Document

class ProductionProject(Document):
    def after_insert(self):
        # Run task creation engine on project creation
        create_initial_tasks(self)


def clean(val, default=None):
    """Convert pandas NaN/None to clean Python values."""
    if pd.isna(val):
        return default
    if isinstance(val, str) and val.strip().lower() == "nan":
        return default
    return val


def create_initial_tasks(project):
    """
    Reads the project template excel (attached to project) and creates tasks 
    with zero dependencies.
    """
    # 1. Locate Excel file
    if not project.template_file:
        frappe.throw("Please attach a Project Template Excel before creating tasks.")

    file_doc = frappe.get_doc("File", {"file_url": project.template_file})
    file_path = file_doc.get_full_path()

    # 2. Load Excel into dataframe
    df = pd.read_excel(file_path)

    for _, row in df.iterrows():
        dependency_type = clean(row.get("Dependency Type"), "None")
        dependency_type = str(dependency_type).strip()
        task_type = clean(row.get("Task Type"))

        tat_based_on = clean(row.get("TAT Based On"), "Task Creation Date")

        # Only create tasks without dependencies
        if task_type == "Project" and (not dependency_type or dependency_type == "None"):
            task = frappe.new_doc("Production Task")
            task.project = project.name
            task.milestone = clean(row.get("Milestone"))
            task.type = clean(row.get("Type"))
            task.task_subject = clean(row.get("Task Subject"))
            task.task_type = clean(row.get("Task Type"))
            task.assigned_to = clean(row.get("Assigned To"))

            # Calculate Expected End Date
            tat_days = clean(row.get("TAT (in days)"))
            tat_days = int(tat_days) if tat_days not in (None, "", "None") else None

            if tat_days:
                if tat_based_on == "Project Start Date" and project.start_date:
                    task.due_date = add_days(getdate(project.start_date), tat_days)
                else:
                    task.due_date = add_days(getdate(frappe.utils.nowdate()), tat_days)

            # Start date = project start date (if available)
            if project.start_date:
                task.start_date = project.start_date

            
            task.status = "Pending"

            task.insert(ignore_permissions=True)

    frappe.db.commit()
