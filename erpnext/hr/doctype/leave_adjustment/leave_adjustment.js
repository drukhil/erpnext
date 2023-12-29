// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Leave Adjustment', {
	refresh: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;
	},
	get_employees: function(frm) {
		return frappe.call({
			method: "get_employees",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("items");
				frm.refresh_fields();
			}
		});
	}
});
