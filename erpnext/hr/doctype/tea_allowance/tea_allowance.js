// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("branch", "cost_center", "cost_center");

frappe.ui.form.on('Tea Allowance', {
	refresh: function(frm) {
		if(frm.doc.docstatus===1){
			frm.add_custom_button(__('Accounting Ledger'), function(){
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
		}		

	},
	"btn_get_eligible_employee": function(frm) {
		if(frm.doc.start_date && frm.doc.end_date && frm.doc.allowance_amount){
			return frappe.call({
				method: "get_details",
				doc: frm.doc,
				callback: function(r, rt) {
					frm.refresh_field("items");
					frm.refresh_fields();
				},
				freeze: true,
				freeze_message: "Loading Details..... Please Wait"
			});
		}else{
			frappe.msgprint("Start Date, End Date and Tea Allowance Amount  is Mandatory");
		}
	},
	"branch": function(frm) {
		frappe.model.get_value('HR Settings', {'name': 'HR Settings'}, 'tea_allowance',
		  function(d) {
		    cur_frm.set_value("allowance_amount", d.tea_allowance);
		});
	},
	"start_date": function(frm) {
		frm.clear_table("items");
        	frm.refresh_fields();
	}
});
