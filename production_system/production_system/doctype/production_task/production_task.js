// Copyright (c) 2025, CHETAN NAHAR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Production Task", {
	refresh(frm) {
		if(frm.doc.status === "Completed" || frm.doc.status === "Cancelled") {
			frm.disable_save();
		}
	},
});
