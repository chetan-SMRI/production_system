// Copyright (c) 2025, CHETAN NAHAR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Production Project", {
	refresh(frm) {
		const user = frappe.session.user;
		const roles = frappe.user_roles || [];

		// check if current user is System Manager
		const isSystemManager = roles.includes("System Manager");
		const isStudioManager = roles.includes("Production Studio Manager");

		// check if current user is the project manager of this project
		const isProjectManager = frm.doc.project_manager === user;

		if (isSystemManager || isStudioManager || isProjectManager) {
			// Black "Create a Task" button with a plus icon

			frm.add_custom_button(
				'<i class="fa fa-plus"></i> Create a Task',
				() => open_create_direct_task_dialog(frm),
				__("Tasks")
			)
				.removeClass("btn-default")
				.addClass("btn-dark");

			// Red "Delete a Task" button with a trash icon
			frm.add_custom_button(
				'<i class="fa fa-trash"></i> Delete a Task',
				() => open_delete_direct_task_dialog(frm),
				__("Tasks")
			)
				.removeClass("btn-default")
				.addClass("btn-danger");

		}
		if (isSystemManager){
			frm.add_custom_button(
				"Delete Project",
				() => delete_project(frm),
			).removeClass("btn-default").addClass("btn-danger");
		}
	},

	generate_item_tasks(frm) {
		if (frm.is_dirty()) {
			frappe.msgprint("Please save the project before generating item tasks.");
			return;
		}
		if (!frm.doc.items || frm.doc.items.length === 0) {
			frappe.msgprint("No items found in the project to generate tasks.");
			return;
		}
		frappe.msgprint({
			title: __("Generate Item Tasks"),
			message: __("Are you sure you want to continue and list if finalized?"),
			primary_action: {
				label: __("Confirm"),
				action(values) {
					frappe.call({
						method: "production_system.api.generate_item_tasks",
						args: {
							project_name: frm.doc.name,
						},
						freeze: true,
						freeze_message: __("Generating Item Tasks..."),
						callback: function (r) {
							if (!r.exc) {
								frappe.msgprint({
									title: __("Success"),
									message: __("Item tasks have been initialized successfully."),
									indicator: "green",
								});
							}
						},
						exception: function (r) {
							frappe.msgprint({
								title: __("Error"),
								message: __(r.exc),
								indicator: "red",
							});
						},
					});
				},
			},
		});
	},
	add_new_item(frm) {
		if (frm.is_dirty()) {
			frappe.msgprint("Please save the project before adding a new item.");
			return;
		}
		open_add_item_dialog(frm);
	},
	remove_a_item(frm) {
		if (frm.is_dirty()) {
			frappe.msgprint("Please save the project before removing an item.");
			return;
		}
		open_remove_item_dialog(frm);
	},
});


function delete_project(frm) {
	frappe.confirm(
				__(
					"Are you sure about deleting the project? (Note: This will also delete very task created.)"
				),
				function () {
					frappe.call({
						method: "production_system.apis.project_apis.delete_project",
						args: {
							project_name: frm.doc.name,
						},
						timeout: 600000,
						freeze: true,
						freeze_message: __("Deleting project..."),
						callback: function (r) {
							if (r.exc) {
								frappe.msgprint({ title: __('Error'), message: __('Deletion failed. See console for details.'), indicator: 'red' });
								console.error(r.exc);
								return;
							}
							const msg = (r.message && r.message.message) ? r.message.message : __('Deletion request completed.');
							window.location.href = "/app/production-project";
							frappe.msgprint({ title: __('Done'), message: msg, indicator: 'green' });
							try { frm.reload_doc(); } catch (e) { console.warn(e); }
						},
					});
				},
				function () {
					// cancelled
				}
			);
	d.show();
}
// Opens "Add New Item" dialog and calls server on submit
function open_add_item_dialog(frm) {
	let parsed_items = [];

	const d = new frappe.ui.Dialog({
		title: __("Add New Item"),
		fields: [
			{
				fieldtype: "Select",
				fieldname: "mode",
				label: __("Mode"),
				options: ["Single", "Bulk"],
				default: "Single",
				reqd: 1,
				change: function () {
					toggle_fields();
				},
			},

			// -------- SINGLE MODE --------
			{
				fieldtype: "Section Break",
				label: __("Single Item"),
				fieldname: "single_section",
			},
			{
				fieldtype: "Data",
				fieldname: "item_name",
				label: __("Item Name"),
			},
			{
				fieldtype: "Data",
				fieldname: "uid",
				label: __("UID"),
			},
			{
				fieldtype: "Link",
				fieldname: "furniture_type",
				label: __("Furniture Type"),
				options: "Furniture Type",
			},
			{
				fieldtype: "Int",
				fieldname: "quantity",
				label: __("Quantity"),
				default: 1,
			},

			// -------- BULK MODE --------
			{
				fieldtype: "Section Break",
				label: __("Bulk Upload"),
				fieldname: "bulk_section",
			},
			{
				fieldtype: "Attach",
				fieldname: "csv_file",
				label: __("Upload CSV"),
			},
			{
				fieldtype: "HTML",
				fieldname: "preview_html",
			},
		],

		primary_action_label: __("Save"),
		primary_action(values) {
			if (values.mode === "Single") {
				create_single(values);
			} else {
				create_bulk();
			}
		},
	});

	// ---------------- TOGGLE ----------------
	function toggle_fields() {
		let mode = d.get_value("mode");

		let single = mode === "Single";
		let bulk = mode === "Bulk";

		["item_name", "uid", "furniture_type", "quantity", "single_section"].forEach(f =>
			d.set_df_property(f, "hidden", !single)
		);
		d.set_df_property("bulk_section", "hidden", !bulk);
		d.set_df_property("csv_file", "hidden", !bulk);
		d.set_df_property("preview_html", "hidden", !bulk);
	}

	// ---------------- SINGLE ----------------
	function create_single(values) {
		if (!values.item_name || !values.quantity || !values.furniture_type || !values.uid) {
			frappe.msgprint(__("Please fill required fields."));
			return;
		}

		frappe.call({
			method: "production_system.api.add_new_item_using_button",
			args: {
				project_name: frm.doc.name,
				item_name: values.item_name,
				uid: values.uid,
				furniture_type: values.furniture_type,
				quantity: values.quantity,
			},
			freeze: true,
			callback: () => {
				d.hide();
				frm.reload_doc();
			},
		});
	}

	// ---------------- BULK PARSE ----------------
	d.fields_dict.csv_file.df.onchange = function () {
		let file = d.get_value("csv_file");
		if (!file) return;

		fetch(file)
			.then(res => res.text())
			.then(text => {
				parsed_items = parse_csv(text);
				render_preview(parsed_items);
			});
	};

	function parse_csv(text) {
		let lines = text.split("\n").map(l => l.trim());

		// -------- STEP 1: FIND START AFTER ------
		let dashIndex = lines.findIndex(l => l.includes("------"));

		if (dashIndex !== -1) {
			lines = lines.slice(dashIndex + 1);
		}

		// remove empty lines
		lines = lines.filter(l => l);

		if (!lines.length) return [];

		// -------- STEP 2: ENSURE CSV FORMAT
		// Must contain commas
		if (!lines[0].includes(",")) {
			frappe.msgprint(__("Invalid CSV format. Please upload a proper comma-separated file."));
			return [];
		}

		// -------- STEP 3: REMOVE HEADER
		let header = lines[0].toLowerCase();
		if (
			header.includes("item") &&
			header.includes("uid")
		) {
			lines.shift();
		}

		// -------- STEP 4: PARSE
		let data = [];

		lines.forEach((line, index) => {
			let row = line.split(",").map(v => v.trim());

			// Skip invalid rows
			if (!row[0] || !row[1]) return;

			data.push({
				item_name: row[0],
				uid: row[1],
				furniture_type: row[2],
				quantity: parseInt(row[3] || 1),
			});
		});

		return data;
	}

	function render_preview(items) {
		let html = `<table class="table table-bordered">
			<tr>
				<th>Item Name</th>
				<th>UID</th>
				<th>Furniture Type</th>
				<th>Qty</th>
			</tr>`;

		items.forEach(i => {
			html += `<tr>
				<td>${i.item_name}</td>
				<td>${i.uid}</td>
				<td>${i.furniture_type}</td>
				<td>${i.quantity}</td>
			</tr>`;
		});

		html += "</table>";

		d.fields_dict.preview_html.$wrapper.html(html);
	}

	// ---------------- BULK CREATE ----------------
	function create_bulk() {
		if (!parsed_items.length) {
			frappe.msgprint(__("Please upload valid CSV."));
			return;
		}

		frappe.call({
			method: "production_system.api.bulk_add_items",
			args: {
				project_name: frm.doc.name,
				items: parsed_items,
			},
			freeze: true,
			freeze_message: __("Creating Items..."),
			callback: () => {
				d.hide();
				frm.reload_doc();
			},
		});
	}

	d.show();
	toggle_fields();
}
function open_remove_item_dialog(frm) {
	// Collect items from child table (ensure child table exists)
	const items = Array.isArray(frm.doc.items) ? frm.doc.items : [];

	if (!items.length) {
		frappe.msgprint({
			title: __("No items"),
			message: __("There are no items to remove from this project."),
			indicator: "orange",
		});
		return;
	}

	// Build options: show "item_code - item_name" or just item_name depending on your fields
	// We'll include both for clarity but send item_name to the backend. Adjust as needed.
	const options = items.map((r) => {
		// prefer item_name or item_code if present
		const name = r.item_name || r.item_code || r.name;
		const label = r.item_code ? `${r.item_code} — ${name}` : name;
		return { label, value: name };
	});

	const d = new frappe.ui.Dialog({
		title: __("Remove an Item"),
		fields: [
			{
				fieldtype: "Select",
				fieldname: "item_to_remove",
				label: __("Select Item"),
				reqd: 1,
				options: options.map((o) => o.label), // Select expects array of display strings
				description: __("Choose the item you want to remove from this project."),
			},
		],
		primary_action_label: __("Remove"),
		primary_action(values) {
			if (!values.item_to_remove) {
				frappe.msgprint(__("Please select an item to remove."));
				return;
			}

			// Resolve the selected display label back to the stored value (item_name)
			const selectedLabel = values.item_to_remove;
			const found = options.find((o) => o.label === selectedLabel);
			const item_name = found ? found.value : selectedLabel;

			// Call server
			frappe.call({
				method: "production_system.api.remove_item_using_button",
				args: {
					project_name: frm.doc.name,
					item_name: item_name,
				},
				freeze: true,
				freeze_message: __("Removing Item..."),
				callback: function (r) {
					if (!r.exc) {
						d.hide();
						frappe.msgprint({
							title: __("Success"),
							message: __("Item removed successfully."),
							indicator: "green",
						});
						// Refresh the form to update child table view
						frm && frm.reload_doc && frm.reload_doc();
					}
				},
			});
		},
	});
	d.get_primary_btn().removeClass("btn-primary").addClass("btn-danger");

	// Show dialog
	d.show();
}

// Call this from refresh(frm) or wherever you need it
function open_delete_direct_task_dialog(frm) {
	const direct_tasks = Array.isArray(frm.doc.direct_tasks) ? frm.doc.direct_tasks : [];

	if (!direct_tasks.length) {
		frappe.msgprint({
			title: __("No manual tasks"),
			message: __("There are no manually created tasks linked to this project."),
			indicator: "orange",
		});
		return;
	}

	// Build select options: show "TASKNAME — Subject (status)" for clarity,
	// but send back the task link (name) as the selected value.
	const options = direct_tasks.map((dt) => {
		const task_link = dt.task || dt.task_name || "";
		const label_parts = [];
		if (task_link) label_parts.push(task_link);
		if (dt.milestone) label_parts.push(`Milestone: ${dt.milestone}`);
		if (dt.task_subject) label_parts.push(dt.task_subject);
		if (dt.status) label_parts.push(`(${dt.status})`);
		const label = label_parts.join(" — ");
		return { value: task_link, label: label || task_link };
	});

	// If some entries have empty task link, filter them out
	const optionsFiltered = options.filter((o) => o.value);

	const d = new frappe.ui.Dialog({
		title: __("Delete Manually Created Task"),
		fields: [
			{
				fieldtype: "Select",
				fieldname: "task_to_delete",
				label: __("Select Task"),
				reqd: 1,
				options: optionsFiltered.map((o) => o.label),
			},
		],
		primary_action_label: __("Delete"),
		primary_action(values) {
			if (!values.task_to_delete) {
				frappe.msgprint(__("Please select a task to delete."));
				return;
			}
			// resolve label back to task name
			const selectedLabel = values.task_to_delete;
			const found = optionsFiltered.find((o) => o.label === selectedLabel);
			const task_name = found ? found.value : selectedLabel;

			frappe.confirm(
				__(
					"Delete task {0} ? This will remove the link from the project and delete the task.",
					[task_name]
				),
				function () {
					frappe.call({
						method: "production_system.api.delete_direct_task",
						args: {
							project_name: frm.doc.name,
							task_name: task_name,
						},
						freeze: true,
						freeze_message: __("Deleting task..."),
						callback: function (r) {
							if (!r.exc && r.message && r.message.ok) {
								d.hide();
								frappe.show_alert({
									message: __("Task deleted"),
									indicator: "green",
								});
								// reload to reflect removed row
								frm.reload_doc && frm.reload_doc();
							} else {
								const msg =
									(r.message && r.message.message) ||
									__("Could not delete task");
								frappe.msgprint({
									title: __("Error"),
									message: msg,
									indicator: "red",
								});
							}
						},
					});
				},
				function () {
					// cancelled
				}
			);
		},
	});

	// Make the primary action button red
	// (works even before showing)
	d.show();
	// After show, replace btn classes
	setTimeout(() => {
		try {
			d.get_primary_btn().removeClass("btn-primary").addClass("btn-danger");
		} catch (err) {
			/* ignore if not found */
		}
	}, 50);
}

function open_create_direct_task_dialog(frm) {
	const milestone_rows = Array.isArray(frm.doc.milestones) ? frm.doc.milestones : [];
	const milestone_options = milestone_rows.map((r) =>
		(r.milestone_name || r.name || "").toString()
	);

	const d = new frappe.ui.Dialog({
		title: __("Create Task"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "project",
				label: __("Production Project"),
				options: "Production Project",
				reqd: 1,
				hidden: 1,
				default: frm.doc.name
			},
			{
				fieldtype: "Link",
				fieldname: "parent_task",
				label: __("Select Parent"),
				options: "Production Task",
				get_query: function() {
					return {
						filters: [
							["Production Task", "project", "=", frm.doc.name],
							["Production Task", "is_parent", "=", true],
						]
					};
				}
			},
			{
				fieldtype: "Data",
				fieldname: "task_subject",
				label: __("Task Subject"),
				reqd: 1,
			},
			{
				fieldtype: "Select",
				fieldname: "milestone",
				label: __("Milestone"),
				options: milestone_options.length
					? milestone_options
					: ["No milestones available"],
				reqd: 1,
				default: milestone_options[0]
			},
			{
				fieldtype: "Date",
				fieldname: "start_date",
				label: __("Start Date"),
				reqd: 1,
				default: "Today"
			},
			{ fieldtype: "Date", fieldname: "due_date", label: __("Due Date"), reqd: 1 },
			{
				fieldtype: "Link",
				options: "User",
				fieldname: "assigned_to",
				label: __("Assign To"),
			},
			{
				fieldtype: "Attach",
				fieldname: "attachment",
				label: __("Attachment"),
			},
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			// Validation
			if (!values.task_subject) return frappe.msgprint(__("Please enter a Task Subject."));
			if (!values.start_date || !values.due_date)
				return frappe.msgprint(__("Please enter both start and due dates."));
			if (frappe.datetime.get_diff(values.due_date, values.start_date) < 0)
				return frappe.msgprint(__("Due Date must be the same or after Start Date."));
			if (!values.milestone || values.milestone === "No milestones available")
				return frappe.msgprint(__("Please select a milestone."));

			// Call server API to create task and link it on the project
			frappe.call({
				method: "production_system.api.create_direct_task",
				args: {
					project_name: values.project,
					task_subject: values.task_subject,
					start_date: values.start_date,
					due_date: values.due_date,
					assigned_to: values.assigned_to || "",
					milestone: values.milestone,
					attachment: values.attachment,
					parent_task: values.parent_task
				},
				freeze: true,
				freeze_message: __("Creating task and linking to project..."),
				callback: function (r) {
					if (!r.exc && r.message && r.message.ok) {
						d.hide();
						frappe.show_alert({
							message: __("Task created"),
							indicator: "green",
						});
						// Optionally reload or refresh the form to show new direct_tasks row
						frm.reload_doc && frm.reload_doc();
					} else {
						const msg =
							(r.message && r.message.message) || __("Could not create task");
						frappe.msgprint({
							title: __("Error"),
							message: msg,
							indicator: "red",
						});
					}
				},
			});
		},
	});
	d.show();
}
