# Copyright (c) 2026, CHETAN NAHAR
# For license information, please see license.txt

import frappe


def progress_bar(percent):
	percent = percent or 0

	color = "#22c55e"

	if percent < 40:
		color = "#ef4444"
	elif percent < 70:
		color = "#f59e0b"

	return f"""
	<div style="width:390px;background:#e5e7eb;border-radius:6px;overflow:hidden;height:18px;position:relative;">
		<div style="width:{percent}%;background:{color};height:100%;"></div>
		<div style="
			position:absolute;
			top:0;
			left:0;
			width:100%;
			height:100%;
			display:flex;
			align-items:center;
			justify-content:center;
			font-weight:700;
			font-size:13px;
			color:#000;">
			{percent}%
		</div>
	</div>
	"""


def execute(filters=None):
	filters = filters or {}

	projects_filter = filters.get("projects")
	start_date = filters.get("start_date")
	end_date = filters.get("end_date")

	columns = [
		{
			"label": "Project",
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Production Project",
			"width": 220
		},
		{
			"label": "Project Manager",
			"fieldname": "project_manager",
			"fieldtype": "Link",
			"options": "User",
			"width": 180
		},
		{
			"label": "Milestone",
			"fieldname": "milestone",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"label": "Progress",
			"fieldname": "progress",
			"fieldtype": "HTML",
			"width": 420
		}
	]

	data = []

	# -----------------------------------
	# Step 1: Build project filters
	# -----------------------------------

	project_filters = {}

	if projects_filter:
		project_filters["name"] = ["in", projects_filter]

	if start_date and end_date:
		project_filters["start_date"] = ["between", [start_date, end_date]]
	elif start_date:
		project_filters["start_date"] = [">=", start_date]
	elif end_date:
		project_filters["start_date"] = ["<=", end_date]

	projects = frappe.get_all(
		"Production Project",
		filters=project_filters,
		fields=["name", "project_manager", "percentage_completion"]
	)

	# -----------------------------------
	# Step 2: Build rows
	# -----------------------------------

	for proj in projects:

		proj_doc = frappe.get_doc("Production Project", proj.name)

		# Project row
		data.append({
			"project": proj_doc.name,
			"project_manager": proj_doc.project_manager,
			"milestone": "",
			"progress": progress_bar(proj_doc.percentage_completion)
		})

		# Milestones
		for milestone in proj_doc.milestones:

			data.append({
				"project": "",
				"project_manager": "",
				"milestone": f"↳ {milestone.milestone_name}",
				"progress": progress_bar(milestone.percentage_completion)
			})

	return columns, data