// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Progress', {
	setup: function(frm) {
		frm.get_docfield("table_8").allow_bulk_edit = 1;		
			
			
	},
	onload: function(frm) {
		frm.set_query("project", function() {
			return {
				"filters": {
					"is_group": 0,
					"priority": 'HIgh',
					
				}
			};
		});

	},
	
});
