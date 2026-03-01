import frappe
import pandas as pd
from frappe.utils import add_days, getdate
from frappe.model.document import Document
from whatsapp_web_automation.whatsapp_web_automation.api.send_message import send_message_in_background

class ProductionProject(Document):
    def before_insert(self):
        initialize_milestones(self)
        # whatsapp message on new project
        prod_settings = frappe.get_doc('Production Settings','Production Settings')
        if prod_settings.whatsapp_account and prod_settings.new_proj_template:
            # send whatsapp message
            pm_mobile = frappe.get_value("User",self.project_manager,'mobile_no')
            context_data = self.as_dict()
            send_message_in_background(prod_settings.whatsapp_account,pm_mobile,template=prod_settings.new_proj_template,whitelabel=False,context=context_data)
    
    def after_insert(self):
        # Run task creation engine on project creation
        create_initial_tasks(self)
        
    def before_save(self):
        if self.percentage_completion == 100:
            self.status = "Closed"
        else:
            self.status = "Open"


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
        if (task_type == "Project" or task_type == "Project-Parent") and (not dependency_type or dependency_type == "None"):
            task = frappe.new_doc("Production Task")
            task.project = project.name
            task.milestone = clean(row.get("Milestone"))
            task.type = clean(row.get("Type"))
            task.task_subject = clean(row.get("Task Subject"))
            task.task_type = "Project" if clean(row.get("Task Type")) == "Project-Parent" else clean(row.get("Task Type"))
            task.assigned_to = project.project_manager
            task.is_parent = True if clean(row.get("Task Type")) == "Project-Parent" else False

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

            task.type = clean(row.get("Type"), "None")
            task.status = "Pending"

            task.insert(ignore_permissions=True)

    frappe.db.commit()

import openpyxl

import frappe
import openpyxl

def initialize_milestones(doc):
    """
    Initialize milestones in Production Project from uploaded template_file (Excel).
    """

    if not doc.template_file:
        frappe.throw("No template file found in this Production Project")

    # Get file path from File doctype
    file_doc = frappe.get_doc("File", {"file_url": doc.template_file})
    filepath = frappe.get_site_path("private", "files", file_doc.file_name)

    # Load Excel
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active  # assuming first sheet has milestones

    milestone_names = []
    for row in ws.iter_rows(min_row=2, values_only=True):  
        # assuming excel has milestone_name in first column
        milestone = row[0]  # <-- milestone column index (0=A, 1=B, etc.)
        if milestone and milestone not in milestone_names:
            milestone_names.append(milestone)


    if not milestone_names:
        frappe.throw("No milestones found in template file")

    total = len(milestone_names)
    weight_each = round(100 / total, 2) if total else 0

    # Clear existing milestones in table
    doc.set("milestones", [])

    for idx, ms in enumerate(milestone_names, start=1):
        doc.append("milestones", {
            "milestone_name": ms,
            "sequence": idx,
            "status": "Pending",
            "percentage_completion": 0,
            "weight": weight_each
        })

    # doc.save(ignore_permissions=True)
    # frappe.db.commit()
    return {"success": True, "milestones_created": total}
