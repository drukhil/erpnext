// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("cost_center", "branch", "branch")
cur_frm.add_fetch("branch", "expense_bank_account", "expense_bank_account");
frappe.ui.form.on('Process Overtime Payment', {
	setup: function (frm) {
	    frm.get_field("items").grid.editable_fields = [
	      { fieldname: "employee_name", columns: 2 },
	      { fieldname: "bank_name", columns: 2 },
	      { fieldname: "bank_account", columns: 2 },
	      { fieldname: "total_ot_amount", columns: 3 },
	    ];
	  },
	
	refresh: function(frm) {
		if(!frm.doc.posting_date){
			frm.set_value("posting_date", get_today());
		}
		cur_frm.set_query("cost_center", function() {
			return {
		    	"filters": {
				"is_group": 1
				}
        	       };
                });
		if(frm.doc.docstatus == 1) {
                        cur_frm.add_custom_button(__('Accounting Ledger'), function() {
                                frappe.route_options = {
                                        voucher_no: frm.doc.name,
                                        from_date: frm.doc.posting_date,
                                        to_date: frm.doc.posting_date,
                                        company: frm.doc.company,
                                        group_by_voucher: false
                                };
                                frappe.set_route("query-report", "General Ledger");
                        }, __("View"));
			cur_frm.add_custom_button(__('OT Details'), function() {
                                frappe.route_options = {
                                        ot_reference: frm.doc.name,
                                        from_date: frm.doc.posting_date,
                                        to_date: frm.doc.posting_date,
                                        company: frm.doc.company,
                                        group_by_voucher: false
                                };
                                frappe.set_route("query-report", "OT Detail Report");
                        }, __("View"));
                }

	},

	load_entries: function(frm) {
                return frappe.call({
                        method: "get_ot_details",
                        doc: frm.doc,
                        callback: function(r, rt) {
                                frm.refresh_field("items");
                                frm.refresh_fields();
                        }
                });
        },

});
