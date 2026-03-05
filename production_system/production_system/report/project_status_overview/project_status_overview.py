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


	columns = [
		{"label": "Project", "fieldname": "project", "fieldtype": "Link", "width": 200, "options": "Production Project"},
		{"label":"Assigned", "fieldname":"assigned", "fieldtype":"Int", "width":100},
		{"label": "Completed", "fieldname": "completed", "fieldtype": "Int", "width": 100},
		{"label": "Pending", "fieldname": "pending", "fieldtype": "Int", "width": 100},
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
		# Get all projects where user has at least one task
		projects = frappe.get_all(
			"Production Task",
			filters={"assigned_to": user},
			distinct=True,
			pluck="project"
		)

	# -----------------------------------
	# Step 2: Process Each Project
	# -----------------------------------
	for project in projects:
		base_filters = {
			"project": project,
			"assigned_to": user
		}
		if milestone:
			base_filters["milestone"] = milestone
		if type:
			base_filters["type"] = type

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

		assigned = len(tasks)
		completed = 0
		pending = 0

		completed_delays = []
		incompleted_delays = []

		for task in tasks:
			if not task.due_date:
				continue

			due_date = getdate(task.due_date)

			# Completed (including Cancelled)
			if task.status in ["Completed", "Cancelled"]:
				completed += 1

				if task.completion_time:
					completion_date = getdate(task.completion_time)
					delay = (completion_date - due_date).days
					print(f"Task {task.name} -> Completed with delay of {delay} days")
					completed_delays.append(delay)

			else:
				pending += 1
				delay = (today - due_date).days
				incompleted_delays.append(delay)

		avg_delay_completed = (
			sum(completed_delays) / len(completed_delays)
			if completed_delays else 0
		)

		avg_delay_incompleted = (
			sum(incompleted_delays) / len(incompleted_delays)
			if incompleted_delays else 0
		)

		data.append({
			"project": project,
			"assigned": assigned,
			"completed": completed,
			"pending": pending,
			"avg_delay_completed": round(avg_delay_completed, 2),
			"avg_delay_incompleted": round(avg_delay_incompleted, 2),
		})

	return columns, data
