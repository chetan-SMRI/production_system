import frappe


def task_permission_query(user=None):
	print('HḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤ')
	"""
	Return SQL WHERE fragment (string) to restrict Production Task list results
	according to the rules:
	- System Manager: no restriction (return None)
	- If task.project has project_manager == user -> visible
	- If user has role 'Projects User' and task.assigned_user == user -> visible
	"""
	if not user:
		user = frappe.session.user

	roles = frappe.get_roles(user)
	# System Manager -> no restriction
	if "System Manager" in roles:
		return None

	user_escaped = frappe.db.escape(user)

	clauses = []

	# Clause: project manager of the parent Production Project
	# we match Production Task.project to Production Project.project_manager = user
	clauses.append(
		"`tabProduction Task`.project IN (SELECT name FROM `tabProduction Project` "
		f"WHERE IFNULL(project_manager, '') = {user_escaped})"
	)

	# Clause: Projects User role -> tasks assigned to this user
	if "Projects User" in roles:
		clauses.append(f"`tabProduction Task`.assigned_user = {user_escaped}")

	# Combine clauses with OR
	if clauses:
		return "(" + " OR ".join(clauses) + ")"

	# No clauses -> deny everything (shouldn't happen because system manager returned earlier)
	return "1=0"


def task_has_permission(doc, user=None, ptype=None):
	print('HḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤHḤ')
	"""
	Per-doc permission check for a Production Task doc object.
	Returns True/False.
	"""
	if not user:
		user = frappe.session.user

	# System Manager -> full access
	roles = frappe.get_roles(user)
	if "System Manager" in roles:
		return True

	# If the task's project has project_manager == user -> access allowed
	project_name = doc.get("project")
	if project_name:
		pm = frappe.db.get_value("Production Project", project_name, "project_manager")
		if pm and pm == user:
			return True

	# If user has 'Projects User' role and is assigned_user on task -> allowed
	if "Projects User" in roles:
		assigned = (doc.get("assigned_user") or "").strip()
		if assigned == user:
			return True

	# Otherwise deny
	return False