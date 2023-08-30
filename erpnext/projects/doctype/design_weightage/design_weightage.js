// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("parent_project", "branch", "branch");


frappe.ui.form.on("Design Weightage", "onload", function(frm) {
    frm.fields_dict.items.grid.get_field('parent_project').get_query =
			function() {
				return {
					filters: {
						"is_group" : 1
					}
				}
			}

});