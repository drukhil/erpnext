// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Section', {
	refresh: function(frm) {
		cur_frm.set_query("d_name", function() {
			return {
				"filters": {
					"dpt_name": frm.doc.dpt_name,
				}
			}
		});
	},
	dpt_name: function(frm) {
		frm.set_value("d_name","");
	}
});