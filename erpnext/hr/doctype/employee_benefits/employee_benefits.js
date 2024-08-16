// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Benefits', {
	refresh: function(frm) {
		cur_frm.add_custom_button(__('Bank Entries'), function() {
			frappe.route_options = {
				"Journal Entry Account.reference_type": me.frm.doc.doctype,
				"Journal Entry Account.reference_name": me.frm.doc.name,
			};
			frappe.set_route("List", "Journal Entry");
		}, __("View"));

	},
	onload: function(frm) {
		if(!frm.doc.posting_date) {
			cur_frm.set_value("posting_date", get_today())
		}
	}
});
frappe.ui.form.on("Separation Item", {
	
	"benefit_type": function(frm, cdt, cdn) {
		set_amount(frm, cdt, cdn);
	},
				
});
var set_amount = function(frm, cdt, cdn){
	var item = locals[cdt][cdn];
	frappe.call({
		method: "erpnext.hr.doctype.employee_benefits.employee_benefits.set_amount",
		args: {
			"benefit_type": item.benefit_type,
			"employee":cur_frm.doc.employee
			

		},
		callback: function(r) {
			if(r.message) {
				console.log(r.message)
				frappe.model.set_value(cdt, cdn, "amount", flt(r.message))
				cur_frm.refresh_field("amount")
			}
		}
	})
}