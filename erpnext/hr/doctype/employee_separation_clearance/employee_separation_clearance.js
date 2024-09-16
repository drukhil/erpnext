// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Separation Clearance', {
	refresh: function(frm) {
		frappe.call({
			method: "check_logged_in_user_role",
			doc:frm.doc,
			callback: function(r){     
				console.log(r.message)
				toggle_remarks_display(frm, r.message[0], r.message[1], r.message[2], r.message[3], r.message[4])
			}
		})
	},
	onload: function(frm){
		if(frm.doc.approvers_set == 0){
			frappe.call({
				method: "set_approvers",
				doc:frm.doc,
				callback: function(r){
					frm.refresh_fields();
				}
			})
		}
	},
});
var toggle_remarks_display = function(frm, supervisor, fd, erp, hra, adm){
	frm.set_df_property("supervisor_remarks","read_only",supervisor);
	frm.set_df_property("supervisor_clearance","read_only",supervisor);
	frm.set_df_property("finance_head_remarks","read_only",fd);
	frm.set_df_property("finance_clearance","read_only",fd);
	frm.set_df_property("erp_remarks","read_only",erp);
	frm.set_df_property("erp_clearance","read_only",erp);
	frm.set_df_property("hr_remarks","read_only",hra);
	frm.set_df_property("hra_clearance","read_only",hra);
	frm.set_df_property("adm_remarks","read_only",adm);
	frm.set_df_property("adm_clearance","read_only",adm);
}
