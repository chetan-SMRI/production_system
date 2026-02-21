# This will contain all project relation APIs.
import frappe

BATCH_SIZE = 200
def _batched_get_all(doctype, filters, fields=["name"], batch_size=BATCH_SIZE):
    start = 0
    while True:
        rows = frappe.get_all(doctype, filters=filters, fields=fields, limit_page_length=batch_size, limit_start=start)
        if not rows:
            break
        for r in rows:
            yield r
        if len(rows) < batch_size:
            break
        start += batch_size

@frappe.whitelist()
def delete_project(project_name):
	for row in _batched_get_all("Production Task", {"project": project_name}, fields=["name"]):
		try:
			frappe.delete_doc("Production Task", row.name, force=True, ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Failed to delete  {row.name}: {e}", "delete_project")
	frappe.db.commit()
	
	try:
		if frappe.db.exists("Production Project", project_name):
			frappe.delete_doc("Production Project", project_name, ignore_permissions=True, force=True)
			frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Failed to delete Production Project {project_name}: {e}", "delete_project")


@frappe.whitelist()
def get_project_milestones(project_name):
    pr_doc = frappe.get_doc('Production Project', project_name)
    milestones = []
    for milestone in pr_doc.milestones:
        milestones.append(milestone.milestone_name)
    return milestones