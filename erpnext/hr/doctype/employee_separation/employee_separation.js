// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.on('Employee Separation', {
	setup: function(frm) {
		cur_frm.add_fetch('employee','employee_name','employee_name');
		cur_frm.add_fetch('employee','department','department');
		cur_frm.add_fetch('employee','designation','designation');
		cur_frm.add_fetch('employee','employee_subgroup','employee_grade');
	},
	refresh: function(frm) {
		if(cur_frm.doc.docstatus == 1 && cur_frm.doc.employee_benefits_status == "Not Claimed" && cur_frm.doc.clearance_acquired == 1){
			frm.add_custom_button("Create Employee Benefit", function(){
				frappe.model.open_mapped_doc({
					method: "erpnext.hr.doctype.employee_separation.employee_separation.make_employee_benefit",
					frm: me.frm
				})
			});
		}
		if(cur_frm.doc.docstatus == 1 && cur_frm.doc.employee_benefits_status == "Not Claimed" && cur_frm.doc.clearance_acquired == 0){
			frm.add_custom_button("Create Employee Clearance", function(){
				frappe.model.open_mapped_doc({
					method: "erpnext.hr.doctype.employee_separation.employee_separation.make_separation_clearance",
					frm: me.frm
				})
			});
		}
	}
});
