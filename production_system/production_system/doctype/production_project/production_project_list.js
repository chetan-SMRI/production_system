frappe.listview_settings["Production Project"] = {
	onload: function(listview) {

		listview.page.add_action_item(__("View Milestone Overview"), function() {

			const selected = listview.get_checked_items();

			if (selected.length === 0) {
				frappe.msgprint("Please select at least one project.");
				return;
			}

			const project_names = selected.map(d => d.name);

			frappe.set_route("query-report", "Project Milestone Overview", {
				projects: JSON.stringify(project_names)
			});

		});

	},
};