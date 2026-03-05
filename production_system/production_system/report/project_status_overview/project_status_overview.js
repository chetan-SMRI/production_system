// Copyright (c) 2026, CHETAN NAHAR and contributors
// For license information, please see license.txt

frappe.query_reports["Project Status Overview"] = {
	"filters": [
		{
			fieldname: "projects",
			label: __("Select Project(s)"),
			fieldtype: "MultiSelectList",
			options: "Production Project",
			get_data: function (txt) {
				console.log(frappe.db.get_link_options("Production Project", txt));
				return frappe.db.get_link_options("Production Project", txt);
			},
			reqd: 1
		},
		{
			fieldname: "user",
			label: __("Select User"),
			fieldtype: "Link",
			options: "User",
			reqd: 1
		},
	]
};
