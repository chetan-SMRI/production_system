import frappe
from frappe import _
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
    # duplicate check - if same item is already present in project, then through error
    seen = set()
    for item in project.items:
        name = item.item_name.strip() + ' (UID: ' + str(item.uid).strip() + ')'
        if name in seen:
            frappe.throw(f"Duplicate item found: {name}")
        seen.add(name)
    if not seen:
        frappe.throw("No items found in project to generate item tasks for.")

    file_doc = frappe.get_doc("File", {"file_url": project.template_file})
    file_path = file_doc.get_full_path()
    df = pd.read_excel(file_path)

    project.initialised_item_tasks = 1
    project.save(ignore_permissions=True)
    frappe.db.commit()


    for item in project.items:
        for _, row in df.iterrows():
            task_type = clean(row.get("Task Type"))
            dependency_type = clean(row.get("Dependency Type"), "None").strip()
            name = item.item_name.strip() + ' (UID: ' + str(item.uid).strip() + ')'
            # ✅ Create only Item tasks with no dependency
            if task_type == "Item" and (not dependency_type or dependency_type == "None"):
                create_task_from_row(project, row, dependency_type, item=name, furniture_type=item.furniture_type)

@frappe.whitelist()
def add_new_item_using_button(project_name,item_name,quantity, uid,furniture_type):
    project = frappe.get_doc("Production Project", project_name)
    for item in project.items:
        if item.item_name == item_name:
            frappe.throw(f"Item '{item_name}' already exists in project '{project_name}'.")
    name = item_name.strip() + ' (UID: ' + str(uid).strip() + ')'

    project.append("items",{
        "item_name":item_name,
        "qty":quantity,
        "uid": uid,
        "furniture_type": furniture_type
    })
    project.save(ignore_permissions=True)
    frappe.db.commit()  
    if not project.template_file:
        frappe.throw("No Excel template attached to project.")

    file_doc = frappe.get_doc("File", {"file_url": project.template_file})
    file_path = file_doc.get_full_path()
    df = pd.read_excel(file_path)

    for _, row in df.iterrows():
        task_type = clean(row.get("Task Type"))
        dependency_type = clean(row.get("Dependency Type"), "None").strip()

        # ✅ Create only Item tasks with no dependency
        if task_type == "Item" and (not dependency_type or dependency_type == "None"):
            create_task_from_row(project, row, dependency_type, item=name,furniture_type=furniture_type)



@frappe.whitelist()
def remove_item_using_button(project_name, item_name):
    """
    Remove an item row from Production Project.items and remove associated
    Production Task rows (task_type == "Item") for that project+item.

    Returns a dict with what was removed / skipped.
    """
    if not project_name or not item_name:
        frappe.throw("project_name and item_name are required.")

    # Load project (fresh)
    project = frappe.get_doc("Production Project", project_name)

    # Remove matching child rows from items (iterate over a slice copy)
    removed_any = False
    name = ""
    for child in project.items[:]:
        # comparing trimmed values helps avoid whitespace mismatch
        if (child.get("item_name") or "").strip() == (item_name or "").strip():
            name = child.item_name.strip() + ' (UID: ' + str(child.uid).strip() + ')'
            project.remove(child)
            removed_any = True

    if not removed_any:
        # nothing removed
        return {"ok": False, "message": f"Item '{item_name}' not found on project '{project_name}'."}

    # Save & commit the project
    project.save(ignore_permissions=True)
    frappe.db.commit()

    # Now find related Production Task rows
    tasks = frappe.get_all(
        "Production Task",
        filters={
            "project": project_name,
            "item": name,
            "task_type": "Item",
        },
        fields=["name", "status"],
    )

    deleted = []
    # skipped = []
    errors = []

    for t in tasks:
        try:
            status = (t.get("status") or "").strip()
            # Do NOT delete completed/closed tasks by default
            # if status in ("Completed", "Closed"):
            #     skipped.append({"name": t["name"], "reason": "Completed/Closed"})
            #     continue

            # Delete the task (force=True to bypass permissions if necessary)
            frappe.delete_doc("Production Task", t["name"], force=True, ignore_permissions=True)
            deleted.append(t["name"])
        except Exception as e:
            # Log and continue — avoids aborting the whole operation for one failure
            frappe.log_error(f"Failed to delete Production Task {t['name']}: {e}", "remove_item_using_button")
            errors.append({"name": t["name"], "error": str(e)})

    frappe.db.commit()

    return {
        "ok": True,
        "message": f"Removed item '{item_name}' from project '{project_name}'.",
        "deleted_tasks": deleted,
        "errors": errors,
    }

def create_task_from_row(project, row, dependency_type=None, item=None, furniture_type=None):
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
        task.furniture_type = furniture_type
    task.assigned_to = assigned_to
    task.status = "Pending"
    task.type = row.get("Type")

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


@frappe.whitelist()
def create_direct_task(project_name, task_subject, start_date, due_date, assigned_to=None, milestone=None, parent_task=None,attachment=None):
    """
    Creates a Production Task and appends it to Production Project.direct_tasks child table.
    Returns {"ok": True, "task_name": "..."} on success, otherwise raises frappe exceptions.
    """

    # basic validation
    if not project_name:
        frappe.throw("project_name is required")
    if not task_subject:
        frappe.throw("task_subject is required")
    if not start_date or not due_date:
        frappe.throw("start_date and due_date are required")
    if not milestone:
        frappe.throw("milestone is required")

    # Load project (fresh)
    project = frappe.get_doc("Production Project", project_name)

    # Optional: validate milestone exists for this project (if your milestone child table uses field milestone_name)
    milestone_exists = False
    for m in project.get("milestones") or []:
        # adjust field name if different
        name_val = m.get("milestone_name") or m.get("name") or ""
        if str(name_val).strip() == str(milestone).strip():
            milestone_exists = True
            break

    if not milestone_exists:
        # you can either throw or allow; here we throw to ensure consistency
        frappe.throw(f"Milestone '{milestone}' not found on project '{project_name}'")

    # Create the Production Task doc
    task_doc = frappe.get_doc({
        "doctype": "Production Task",
        "project": project_name,
        "task_subject": task_subject,
        "task_type": "Direct",
        "start_date": start_date,
        "due_date": due_date,
        "assigned_to": assigned_to or "",
        "milestone": milestone,
        # set other defaults as needed
        "status": "Pending",
        "attachment": attachment
    })
    if parent_task:
        task_doc.is_child = True
        task_doc.parent_task = parent_task
    # Insert task
    task_doc.insert(ignore_permissions=True)
    # Ensure DB write
    frappe.db.commit()

    # Append to project's direct_tasks child table
    # Adjust child table fieldnames if different. We assume:
    # Production Project has child table field 'direct_tasks' with child fields:
    #  - 'task' (Link to Production Task)
    #  - 'milestone' (Data)
    project = frappe.get_doc("Production Project", project_name)  # reload to get fresh doc
    project.append("direct_tasks", {
        "task": task_doc.name,
        "milestone": milestone
    })
    project.save(ignore_permissions=True)
    frappe.db.commit()

    return {"ok": True, "task_name": task_doc.name, "message": "Task created and linked"}


@frappe.whitelist()
def delete_direct_task(project_name, task_name):
    """
    Remove the task link row from project.direct_tasks, save project,
    then delete the Production Task doc.

    Args:
      project_name (str): Production Project name
      task_name (str): Production Task name (link)
      force (int|str): if truthy, allow delete even if task is Completed/Closed

    Returns:
      dict: {"ok": True, "task_deleted": task_name} or raises frappe exception
    """
    if not project_name or not task_name:
        return {"ok": False, "message": _("project_name and task_name are required.")}


    # load project (fresh)
    project = frappe.get_doc("Production Project", project_name)
    # find and remove matching direct_tasks row(s)
    removed = False
    for row in project.get("direct_tasks")[:]:
        # row.task may be the link field
        if (row.get("task") or "").strip() == (task_name or "").strip():
            project.remove(row)
            removed = True

    if not removed:
        # nothing removed – return friendly error
        return {"ok": False, "message": _("Task {0} not found in project's direct_tasks", [task_name])}

    # save project changes
    project.save(ignore_permissions=True)
    frappe.db.commit()

    # delete the task doc
    try:
        frappe.delete_doc("Production Task", task_name, force=True, ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Failed deleting Production Task {task_name}: {e}", "delete_direct_task")
        return {"ok": False, "message": _("Failed to delete task: {0}", [str(e)])}

    return {"ok": True, "task_deleted": task_name, "message": _("Task deleted")}
