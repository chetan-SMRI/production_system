// Copyright (c) 2025, CHETAN NAHAR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Production Task", {
	refresh(frm) {
		if(frm.doc.status === "Completed" || frm.doc.status === "Cancelled") {
			frm.disable_save();
		}
		// Wait for sidebar to render
		setTimeout(() => {
			// Hide the full Assigned To section
			$(".form-assignments").hide();
		}, 0);
	},
});
