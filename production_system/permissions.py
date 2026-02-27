import frappe


def task_permission_query(user=None):
	if not user:
		user = frappe.session.user

	roles = frappe.get_roles(user)

	# Full access roles
	if "System Manager" in roles or "Production Studio Manager" in roles:
		return None

	user_escaped = frappe.db.escape(user)

	clauses = []

	# ---------------- PROJECT MANAGER ----------------
	if "Production Project Manager" in roles:
		# Tasks under projects where user is project manager
		clauses.append(
			"`tabProduction Task`.project IN (SELECT name FROM `tabProduction Project` "
			f"WHERE IFNULL(project_manager, '') = {user_escaped})"
		)

	# ---------------- COMMON (MANAGER + USER) ----------------
	# Assigned to user
	clauses.append(f"`tabProduction Task`.assigned_to = {user_escaped}")

	# Created by user
	clauses.append(f"`tabProduction Task`.owner = {user_escaped}")

	# Combine
	if clauses:
		return "(" + " OR ".join(clauses) + ")"

	return "1=0"

def task_has_permission(doc, user=None, ptype=None):
	if not user:
		user = frappe.session.user

	roles = frappe.get_roles(user)

	# Full access
	if "System Manager" in roles or "Production Studio Manager" in roles:
		return True

	# ---------------- PROJECT MANAGER ----------------
	if "Production Project Manager" in roles:
		project_name = doc.get("project")
		if project_name:
			pm = frappe.db.get_value("Production Project", project_name, "project_manager")
			if pm == user:
				return True

	# ---------------- COMMON ----------------

	# ✅ CURRENT assignment
	if (doc.get("assigned_to") or "").strip() == user:
		return True

	# ✅ OWNER
	if doc.get("owner") == user:
		return True

	# 🔥 NEW: allow reassignment if user WAS previously assigned
	old_doc = frappe.get_doc("Production Task", doc.name)
	print(old_doc, old_doc.assigned_to)
	if old_doc:
		if (old_doc.get("assigned_to") or "").strip() == user:
			return True

	return False


ROLE_MANAGER = "Production Studio Manager"
ROLE_PROJECT_USER = "Production Project User"


def project_permission_query(user=None):
    """
    SQL WHERE clause for Production Project list view:
      - System Manager / Production Studio Manager → full access
      - Project Manager → own projects
      - Production Project User → projects where at least 1 task is assigned
    """

    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    # Full access roles
    if "System Manager" in roles or ROLE_MANAGER in roles:
        return None

    user_escaped = frappe.db.escape(user)
    clauses = []

    # ✅ Project Manager access
    clauses.append(
        f"IFNULL(`tabProduction Project`.project_manager, '') = {user_escaped}"
    )

    # ✅ Project User access (via Production Task assignment)
    if ROLE_PROJECT_USER in roles:
        clauses.append(
            "`tabProduction Project`.name IN ("
            "SELECT `tabProduction Task`.project FROM `tabProduction Task` "
            f"WHERE IFNULL(`tabProduction Task`.assigned_to, '') = {user_escaped}"
            ")"
        )

        # 🔥 OPTIONAL: If you are using Frappe Assignment (ToDo)
        clauses.append(
            "`tabProduction Project`.name IN ("
            "SELECT t.project FROM `tabProduction Task` t "
            "INNER JOIN `tabToDo` td ON td.reference_name = t.name "
            "AND td.reference_type = 'Production Task' "
            f"WHERE td.allocated_to = {user_escaped} "
            "AND td.status != 'Cancelled'"
            ")"
        )

    if clauses:
        return "(" + " OR ".join(clauses) + ")"

    return "1=0"


def project_has_permission(doc, user=None, ptype=None):
    """
    Per-document permission for Production Project:
      - System Manager / Production Studio Manager → full access
      - Project Manager → own project
      - Production Project User → if assigned to at least 1 task
    """

    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    # ✅ Full access
    if "System Manager" in roles or ROLE_MANAGER in roles:
        return True

    # ✅ Project Manager
    if (doc.get("project_manager") or "").strip() == user:
        return True

    # ✅ Project User (via direct field)
    if ROLE_PROJECT_USER in roles:
        exists = frappe.db.exists(
            "Production Task",
            {"project": doc.name, "assigned_to": user}
        )
        if exists:
            return True

        # 🔥 OPTIONAL: If using Assignment (ToDo)
        exists = frappe.db.sql("""
            SELECT 1
            FROM `tabProduction Task` t
            INNER JOIN `tabToDo` td
                ON td.reference_name = t.name
                AND td.reference_type = 'Production Task'
            WHERE t.project = %s
              AND td.allocated_to = %s
              AND td.status != 'Cancelled'
            LIMIT 1
        """, (doc.name, user))

        if exists:
            return True

    return False