import frappe


def link_project(name):
	return f"<a href='/app/production-project/{name}' style='font-weight:500'>{name}</a>"


def execute(filters=None):
	filters = filters or {}

	furniture_type = filters.get("furniture_type")
	projects_filter = filters.get("projects")
	start_date = filters.get("start_date")
	end_date = filters.get("end_date")

	columns = [
		{
			"label": "Furniture Type",
			"fieldname": "furniture_type",
			"fieldtype": "HTML",
			"width": 250
		},
		{
			"label": "Project",
			"fieldname": "project",
			"fieldtype": "HTML",
			"width": 250
		},
		{
			"label": "Quantity",
			"fieldname": "qty",
			"fieldtype": "HTML",
			"width": 250
		}
	]

	data = []

	# --------------------------------
	# Load Projects
	# --------------------------------

	project_filters = {}

	if projects_filter:
		project_filters["name"] = ["in", projects_filter]

	if start_date and end_date:
		project_filters["start_date"] = ["between", [start_date, end_date]]

	projects = frappe.get_all(
		"Production Project",
		filters=project_filters,
		fields=["name"]
	)

	# --------------------------------
	# Aggregate Furniture Counts
	# --------------------------------

	furniture_map = {}

	for proj in projects:

		proj_doc = frappe.get_doc("Production Project", proj.name)

		for item in proj_doc.items:

			ftype = item.furniture_type

			if furniture_type and ftype != furniture_type:
				continue

			if ftype not in furniture_map:
				furniture_map[ftype] = {}

			if proj.name not in furniture_map[ftype]:
				furniture_map[ftype][proj.name] = 0

			furniture_map[ftype][proj.name] += item.qty or 0

	# --------------------------------
	# Build Report UI
	# --------------------------------

	for ftype, projects_data in furniture_map.items():

		total = 0

		# Furniture Header
		if not furniture_type:
			data.append({
				"furniture_type": f"<b style='font-size:14px'>{ftype}</b>",
				"project": "",
				"qty": ""
			})

		for proj, qty in projects_data.items():

			total += qty

			data.append({
				"furniture_type": "" if not furniture_type else ftype,
				"project": link_project(proj),
				"qty": f"{qty}"
			})

		# Spacer row
		data.append({
			"furniture_type": "",
			"project": "",
			"qty": ""
		})

		# TOTAL row
		data.append({
			"furniture_type": "",
			"project": "<b style='font-size:13px'>TOTAL</b>",
			"qty": f"<b style='font-size:13px'>{total}</b>"
		})

		# Bigger spacing between furniture groups
		data.append({
			"furniture_type": "",
			"project": "",
			"qty": ""
		})

	return columns, data