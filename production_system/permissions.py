import frappe


def task_permission_query(user=None):
	"""
	Return SQL WHERE fragment (string) to restrict Production Task list results
	according to the rules:
	- System Manager: no restriction (return None)
	- If task.project has project_manager == user -> visible
	- If user has role 'Projects User' and task.assigned_to == user -> visible
	"""
	if not user:
		user = frappe.session.user

	roles = frappe.get_roles(user)
	# System Manager -> no restriction
	if "System Manager" in roles or "Production Studio Manager" in roles:
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
		clauses.append(f"`tabProduction Task`.assigned_to = {user_escaped}")

	# Combine clauses with OR
	if clauses:
		return "(" + " OR ".join(clauses) + ")"

	# No clauses -> deny everything (shouldn't happen because system manager returned earlier)
	return "1=0"


def task_has_permission(doc, user=None, ptype=None):
	"""
	Per-doc permission check for a Production Task doc object.
	Returns True/False.
	"""
	if not user:
		user = frappe.session.user

	# System Manager -> full access
	roles = frappe.get_roles(user)
	if "System Manager" in roles or "Production Studio Manager" in roles:
		return True

	# If the task's project has project_manager == user -> access allowed
	project_name = doc.get("project")
	if project_name:
		pm = frappe.db.get_value("Production Project", project_name, "project_manager")
		if pm and pm == user:
			return True

	# If user has 'Projects User' role and is assigned_to on task -> allowed
	if "Projects User" in roles:
		assigned = (doc.get("assigned_to") or "").strip()
		if assigned == user:
			return True

	# Otherwise deny
	return False


def project_permission_query(user=None):
    """
    Return SQL WHERE fragment (string) to restrict Production Project list results:
      - System Manager/Studio Manager: no restriction (None)
      - If project.project_manager == user -> visible
      - If user has role 'Projects User' and there exists a Production Task in that project
        with assigned_to == user -> visible
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)
    if "System Manager" in roles or "Production Studio Manager" in roles:
        return None

    user_escaped = frappe.db.escape(user)

    clauses = []
    # Project manager clause
    clauses.append(f"IFNULL(`tabProduction Project`.project_manager, '') = {user_escaped}")

    # Projects User clause: project has at least one Production Task assigned to user
    if "Projects User" in roles:
        clauses.append(
            "`tabProduction Project`.name IN ("
            "SELECT `tabProduction Task`.project FROM `tabProduction Task` "
            f"WHERE `tabProduction Task`.project = `tabProduction Project`.name "
            f"AND IFNULL(`tabProduction Task`.assigned_to, '') = {user_escaped}"
            ")"
        )

    if clauses:
        return "(" + " OR ".join(clauses) + ")"

    return "1=0"


def project_has_permission(doc, user=None, ptype=None):
    """
    Per-doc permission check for Production Project.
    Returns True/False.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)
    if "System Manager" in roles or "Production Studio Manager" in roles:
        return True

    # Project manager can view
    project_manager = (doc.get("project_manager") or "").strip()
    if project_manager == user:
        return True

    # Projects User role: allowed if any task in this project is assigned to this user
    if "Projects User" in roles:
        exists = frappe.db.exists(
            "Production Task",
            {"project": doc.name, "assigned_to": user}
        )
        if exists:
            return True

    return False
