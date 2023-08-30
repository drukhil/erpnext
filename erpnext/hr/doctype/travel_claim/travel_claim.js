// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Travel Claim', {
	"items_on_form_rendered": function(frm, grid_row, cdt, cdn) {
		/*var row = cur_frm.open_grid_row();
		if(!row.grid_form.fields_dict.dsa_per_day.value) {
			row.grid_form.fields_dict.dsa.set_value(frm.doc.dsa_per_day)
                	row.grid_form.fields_dict.dsa.refresh()
		}*/
	},
	refresh: function(frm) {
		if(frm.doc.docstatus == 1) {
			cur_frm.set_df_property("hr_approval", "hidden", 0)
			cur_frm.set_df_property("supervisor_approval", "hidden", 0)

			if(frappe.model.can_read("Journal Entry")) {
				cur_frm.add_custom_button('Bank Entries', function() {
					frappe.route_options = {
						"Journal Entry Account.reference_type": frm.doc.doctype,
						"Journal Entry Account.reference_name": frm.doc.name,
					};
					frappe.set_route("List", "Journal Entry");
				}, __("View"));
			}
		}
	},
	onload: function(frm) {
		cur_frm.set_df_property("supervisor_approval", "hidden", 1)
		cur_frm.set_df_property("hr_approval", "hidden", 1)
		cur_frm.set_df_property("claim_status", "hidden", 1)
		
		frm.set_query("supervisor", function() {
			return {
				query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
				filters: {
					employee: frm.doc.employee
				}
			};
		});
		/*
		if (in_list(user_roles, "Approver") && frappe.session.user == frm.doc.supervisor) {
			cur_frm.set_df_property("supervisor_approval", "hidden", 0)
			cur_frm.set_df_property("claim_status", "hidden", 0)
		}
		if (in_list(user_roles, "HR Manager") || in_list(user_roles, "HR Support"))  {
			cur_frm.set_df_property("hr_approval", "hidden", 0)
			cur_frm.set_df_property("claim_status", "hidden", 0)
		}
		*/

		if(frm.doc.docstatus == 1) {
			//cur_frm.set_df_property("hr_approval", "hidden", 0)
			//cur_frm.set_df_property("supervisor_approval", "hidden", 0)

			//if(frappe.model.can_read("Journal Entry")) {
				cur_frm.add_custom_button('Bank Entries', function() {
					frappe.route_options = {
						"Journal Entry Account.reference_type": frm.doc.doctype,
						"Journal Entry Account.reference_name": frm.doc.name,
					};
					frappe.set_route("List", "Journal Entry");
				});
			//}
		}
		
		if(frm.doc.docstatus < 2 || frm.doc.__islocal){
			var ti = frm.doc.items || [];
			var total = 0.0;

			frm.doc.items.forEach(function(d) {
				if(!d.quarantine) { 
				total += parseFloat(d.actual_amount || 0.0)}
			})
			
			if(parseFloat(total) != parseFloat(frm.doc.claim_amount)){
				frm.set_value("claim_amount", parseFloat(total));
			}
		}
		
	},

	"extra_claim_amount": function(frm) {
		frm.set_value("total_claim_amount", frm.doc.extra_claim_amount + frm.doc.claim_amount)
	},
	"claim_amount": function(frm) {
                frm.set_value("total_claim_amount", frm.doc.claim_amount + frm.doc.extra_claim_amount);
                frm.set_value("balance_amount", frm.doc.total_claim_amount - frm.doc.advance_amount);

        },
});

frappe.ui.form.on("Travel Claim Item", {
	"form_render": function(frm, cdt, cdn) {
		if (frm.doc.__islocal) {
			var item = frappe.get_doc(cdt, cdn)
			if (item.halt == 0) {
				var df = frappe.meta.get_docfield("Travel Claim Item","distance", cur_frm.doc.name);
				frappe.model.set_value(cdt, cdn, "distance", "")
				//df.display = 0;
			}	
		
			if(item.currency != "BTN") {
				frappe.model.set_value(cdt, cdn, "amount", format_currency(flt(item.amount), item.currency))
			}
		}
	},
	"currency": function(frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"dsa": function(frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"mileage_rate": function(frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"distance": function(frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"dsa_percent": function(frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"actual_amount": function(frm, cdt, cdn) {
		var total = 0;
		frm.doc.items.forEach(function(d) {
			if(!d.quarantine) { 
			total += d.actual_amount }
		})
		frm.set_value("claim_amount", total)
	}
})

function do_update(frm, cdt, cdn) {
	//var item = frappe.get_doc(cdt, cdn)
	var item = locals[cdt][cdn]
	/*if (item.last_day) {
		item.dsa_percent = 0
	} */
	var amount = flt((item.dsa_percent/100 * item.dsa) + item.mileage_rate * item.distance)
	if (item.halt == 1) {
		amount = flt((item.dsa_percent/100 * item.dsa) * item.no_days)
	}
	if(item.currency != "BTN") {
		frappe.call({
			method: "erpnext.hr.doctype.travel_authorization.travel_authorization.get_exchange_rate",
			args: {
				"from_currency": item.currency,
				"to_currency": "BTN"
			},
			callback: function(r) {
				if(r.message) {
					frappe.model.set_value(cdt, cdn, "exchange_rate", flt(r.message))
					frappe.model.set_value(cdt, cdn, "actual_amount", flt(r.message) * amount)
				}
			}
		})
	}
	else {
		frappe.model.set_value(cdt, cdn, "actual_amount", amount)
	}
	
	frappe.model.set_value(cdt, cdn, "amount", format_currency(amount, item.currency))
	refresh_field("amount")	

}

frappe.ui.form.on("Travel Claim", "after_save", function(frm, cdt, cdn){
        if(in_list(user_roles, "Approver")){
                if (frm.doc.workflow_state && frm.doc.workflow_state.indexOf("Rejected") >= 0){
                        frappe.prompt([
                                {
                                        fieldtype: 'Small Text',
                                        reqd: true,
                                        fieldname: 'reason'
                                }],
                                function(args){
                                        validated = true;
                                        frappe.call({
                                                method: 'frappe.core.doctype.communication.email.make',
                                                args: {
                                                        doctype: frm.doctype,
                                                        name: frm.docname,
                                                        subject: format(__('Reason for {0}'), [frm.doc.workflow_state]),
                                                        content: args.reason,
                                                        send_mail: false,
                                                        send_me_a_copy: false,
                                                        communication_medium: 'Other',
                                                        sent_or_received: 'Sent'
                                                },
                                                callback: function(res){
                                                        if (res && !res.exc){
                                                                frappe.call({
                                                                        method: 'frappe.client.set_value',
                                                                        args: {
                                                                                doctype: frm.doctype,
                                                                                name: frm.docname,
                                                                                fieldname: 'reason',
                                                                                value: frm.doc.reason ?
                                                                                        [frm.doc.reason, '['+String(frappe.session.user)+' '+String(frappe.datetime.nowdate())+']'+' : '+String(args.reason)].join('\n') : frm.doc.workflow_state
                                                                        },
                                                                        callback: function(res){
                                                                                if (res && !res.exc){
                                                                                        frm.reload_doc();
                                                                                }
                                                                        }
                                                                });
}
                                                }
                                        });
                                },
                                __('Reason for ') + __(frm.doc.workflow_state),
                                __('Save')
                        )
                }
        }
});

