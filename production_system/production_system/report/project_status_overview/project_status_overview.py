# Copyright (c) 2026, CHETAN NAHAR and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate


def execute(filters=None):
	filters = filters or {}

	projects_filter = filters.get("projects")
	user = filters.get("user")
	milestone = filters.get("milestone")
	type = filters.get("type")
	start_date = filters.get("start_date")
	end_date = filters.get("end_date")

	columns = [
		{"label": "Project", "fieldname": "project", "fieldtype": "Link", "width": 200, "options": "Production Project"},
		{"label": "Assigned", "fieldname": "assigned", "fieldtype": "HTML", "width": 100},
		{"label": "Completed", "fieldname": "completed", "fieldtype": "HTML", "width": 100},
		{"label": "Pending", "fieldname": "pending", "fieldtype": "HTML", "width": 100},
		{"label": "Avg Delay (Completed)", "fieldname": "avg_delay_completed", "fieldtype": "Float", "width": 200},
		{"label": "Avg Delay (Incompleted)", "fieldname": "avg_delay_incompleted", "fieldtype": "Float", "width": 200},
	]

	data = []
	today = getdate(nowdate())

	# -----------------------------------
	# Step 1: Get Projects
	# -----------------------------------

	if projects_filter:
		projects = projects_filter
		if isinstance(projects, str):
			projects = [projects]

	else:
		if user:
			projects = frappe.get_all(
				"Production Task",
				filters={"assigned_to": user},
				distinct=True,
				pluck="project"
			)
		else:
			projects = frappe.get_all(
				"Production Project",
				fields=["name"],
				pluck="name"
			)

	# -----------------------------------
	# Step 2: Process Each Project
	# -----------------------------------

	for project in projects:

		base_filters = {
			"project": project
		}

		# Apply user filter only if user exists
		if user:
			base_filters["assigned_to"] = user

		if milestone:
			base_filters["milestone"] = milestone

		if type:
			base_filters["type"] = type

		# Date filtering
		if start_date and end_date:
			base_filters["start_date"] = ["between", [start_date, end_date]]

		elif start_date:
			base_filters["start_date"] = (">=", start_date)

		elif end_date:
			base_filters["start_date"] = ("<=", end_date)

		tasks = frappe.get_all(
			"Production Task",
			filters=base_filters,
			fields=[
				"name",
				"status",
				"due_date",
				"completion_time"
			]
		)

		if not tasks:
			continue

		assigned_count = len(tasks)
		completed_count = 0
		pending_count = 0

		completed_delays = []
		incompleted_delays = []

		for task in tasks:

			if not task.due_date:
				continue

			due_date = getdate(task.due_date)

			# Completed tasks
			if task.status in ["Completed", "Cancelled"]:

				completed_count += 1

				if task.completion_time:

					completion_date = getdate(task.completion_time)

					delay = (completion_date - due_date).days
					delay = max(delay, 0)  # normalize early completion

					completed_delays.append(delay)

			else:

				pending_count += 1

				delay = (today - due_date).days
				delay = max(delay, 0)  # normalize future tasks

				incompleted_delays.append(delay)

		# Averages
		avg_delay_completed = (
			sum(completed_delays) / len(completed_delays)
			if completed_delays else 0
		)

		avg_delay_incompleted = (
			sum(incompleted_delays) / len(incompleted_delays)
			if incompleted_delays else 0
		)

		# Links
		user_query = f"&assigned_to={user}" if user else ""

		assigned_link = f"/app/production-task?project={project}{user_query}"
		completed_link = f"/app/production-task?project={project}{user_query}&status=%5B%22in%22%2C%5B%22Completed%22%2C%22Cancelled%22%2Cnull%5D%5D"
		pending_link = f"/app/production-task?project={project}{user_query}&status=%5B%22in%22%2C%5B%22Pending%22%2C%22In+Progress%22%2Cnull%5D%5D"

		data.append({
			"project": project,
			"assigned": f"<a href='{assigned_link}'>{assigned_count}</a>",
			"completed": f"<a href='{completed_link}'>{completed_count}</a>",
			"pending": f"<a href='{pending_link}'>{pending_count}</a>",
			"avg_delay_completed": round(avg_delay_completed, 2),
			"avg_delay_incompleted": round(avg_delay_incompleted, 2),
		})

	return columns, data