// Copyright (c) 2025, CHETAN NAHAR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Production Project", {
    refresh(frm) {
        // hide button if item tasks already initialized
        if (frm.doc.initialised_item_tasks) {
            frm.remove_custom_button("Generate Item Tasks");
        }
    },

    generate_item_tasks(frm) {
        if (!frm.doc.name) {
            frappe.msgprint("Please save the project before generating item tasks.");
            return;
        }
        frappe.msgprint({
            title: __('Generate Item Tasks?'),
            message: __("Are you sure you want to continue? Once submitted, you will not be able to add or edit items."),
            primary_action: {
                label: __('Confirm'),
                action(values) {
                    frappe.call({
            method: "production_system.api.generate_item_tasks",
            args: {
                project_name: frm.doc.name
            },
            freeze: true,
            freeze_message: __("Generating Item Tasks..."),
            callback: function(r) {
                if (!r.exc) {
                    frappe.msgprint({
                        title: __("Success"),
                        message: __("Item tasks have been initialized successfully."),
                        indicator: "green"
                    });

                    // ✅ mark flag
                    frm.set_value("initialised_item_tasks", 1);
					frm.save();
                }
            }
        });
                }
            }
        });
    }
});
