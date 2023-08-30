// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Priority Project', {
	get_details: function(frm) {
		return frappe.call({
			method: "get_details",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("items");
				frm.refresh_fields();
			}
		});
	},
	onload: function(frm) {
		frm.set_query("parent_project", function() {
			return {
				"filters": {
					"is_group": 1,
					
					
				}
			};
		});

	},
	setup: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;		
			
		
			
	},	
});
