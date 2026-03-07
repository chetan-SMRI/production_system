// Copyright (c) 2026, CHETAN NAHAR and contributors
// For license information, please see license.txt

frappe.query_reports["Project Furniture Overview"] = {
	"filters": [
		{
			fieldname: "furniture_type",
			label: __("Select Furniture Type"),
			fieldtype: "Link",
			options: "Furniture Type",
		},
		{
			fieldname: "start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			reqd: 1
		},
		{
			fieldname: "end_date",
			label: __("End Date"),
			fieldtype: "Date",
			reqd: 1
		},
	]
};
