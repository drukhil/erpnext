// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/*
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
2.0.190419       SHIV		                        2019/04/19         JE issue while submitting
--------------------------------------------------------------------------------------------------------------------------                                                                          
*/

cur_frm.add_fetch("employee", "employee_name", "employee_name")
cur_frm.add_fetch("employee", "employee_subgroup", "grade")
cur_frm.add_fetch("employee", "designation", "designation")
cur_frm.add_fetch("employee", "department", "department")
cur_frm.add_fetch("employee", "division", "division")
cur_frm.add_fetch("employee", "branch", "branch")
cur_frm.add_fetch("employee", "cost_center", "cost_center")

frappe.ui.form.on('Travel Authorization', {
	setup: function(frm) {
		//frm.get_docfield("items").allow_bulk_edit = 1;		
		frm.get_field('items').grid.editable_fields = [
			{fieldname: 'date', columns: 2},
			{fieldname: 'from_place', columns: 2},
			{fieldname: 'to_place', columns: 2},
			{fieldname: 'halt_at', columns: 2},
			{fieldname: 'till_date', columns: 2},
		];
		frm.get_field('details').grid.editable_fields = [
			{fieldname: 'date', columns: 2},
			{fieldname: 'from_place', columns: 2},
			{fieldname: 'to_place', columns: 2},
			{fieldname: 'halt_at', columns: 2},
			{fieldname: 'till_date', columns: 2},
		];
	},
	
	refresh: function(frm) {
		//show the document status field and submit button
		if (in_list(user_roles, "Expense Approver") && frappe.session.user == frm.doc.supervisor) {
			frm.toggle_display("document_status", frm.doc.docstatus==0);
			frm.toggle_reqd("document_status", frm.doc.docstatus==0);
		}
		
		if (frm.doc.docstatus == 1 && !frm.doc.travel_claim && frm.doc.workflow_state == "Approved") {
			frm.add_custom_button("Create Travel Claim", function() {
				if(frm.doc.end_date_auth < get_today()){
					frappe.model.open_mapped_doc({
						method: "erpnext.hr.doctype.travel_authorization.travel_authorization.make_travel_claim",
						frm: cur_frm
					})
				} else {
					frappe.msgprint(__('Claim is allowed only after travel completion date i.e., {0}', [frm.doc.end_date_auth]));
				}
			}).addClass((frm.doc.end_date_auth < get_today()) ? "btn-success" : "btn-danger");
		}

		if(frm.doc.docstatus == 1) {
			frm.toggle_display("document_status", 1);
		}
		
		if(frm.doc.__islocal){
			frm.set_value("advance_journal", "");
			frm.set_value("cancellation_reason", "");
		}
		
		cur_frm.set_df_property("items", "read_only", frm.doc.travel_claim ? 1 : 0)
	},
	//Auto calculate next date on form render
	"items_on_form_rendered": function(frm, grid_row, cdt, cdn) {
		var row = cur_frm.open_grid_row();
		if(!row.grid_form.fields_dict.date.value) {
			if(frm.doc.items.length > 1) {
				var d = ''
				if(frm.doc.items[frm.doc.items.length - 2].halt == 1) {
					d = frappe.datetime.add_days(frm.doc.items[frm.doc.items.length - 2].till_date, 1)
				}else {
					d = frappe.datetime.add_days(frm.doc.items[frm.doc.items.length - 2].date, 1)
				}
				d = d.toString()
				row.grid_form.fields_dict.date.set_value(d.substring(8) + "-" + d.substring(5, 7) + "-" + d.substring(0, 4))
				//row.grid_form.fields_dict.date.refresh()
			}
		}
	},
	onload: function(frm) {
		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today());
		}

		frm.set_query("supervisor", function() {
			return {
				query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
				filters: {
					employee: frm.doc.employee
				}
			};
		});

		frm.set_query("employee", erpnext.queries.employee);
	},
	"need_advance": function(frm) {
		frm.toggle_reqd("estimated_amount", frm.doc.need_advance==1);
		frm.toggle_reqd("currency", frm.doc.need_advance==1);
		frm.toggle_reqd("advance_amount", frm.doc.need_advance==1);
		calculate_advance(frm);
	},
	"advance_amount": function(frm) {
		if(frm.doc.advance_amount && !frm.doc.estimated_amount){
			msgprint("Total Estimated Amount required for advance request");
		}
		// if (frm.doc.advance_amount > frm.doc.estimated_amount * 0.9) {
		// 	msgprint("Advance amount cannot be greater than 90% of the estimated amount");
		// 	//frm.set_value("advance_amount", 0)
		// }
		if(frm.doc.currency == "BTN") {
			frm.set_value("advance_amount_nu", flt(frm.doc.advance_amount))
		}
		else {
			update_advance_amount(frm)
		}
		calculate_advance(frm);
	},
	"document_status": function(frm) {
		if(frm.doc.document_status == "Rejected") {
			frm.toggle_reqd("purpose")
		}
	},
	"make_traveil_claim": function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.hr.doctype.travel_authorization.travel_authorization.make_travel_claim",
			frm: cur_frm
		})
	},
	"currency": function(frm) {
		if(frm.doc.currency == "BTN") {
			frm.set_value("advance_amount_nu", flt(frm.doc.advance_amount))
		}
		else {
			update_advance_amount(frm)
		}
	}
});

frappe.ui.form.on("Travel Authorization Item", {
	"date": function(frm, cdt, cdn) {
		var item = locals[cdt][cdn];
		
		if (!item.halt) {
			if (item.date != item.till_date || !item.till_date) {
				frappe.model.set_value(cdt, cdn, "temp_till_date", item.till_date);
				frappe.model.set_value(cdt, cdn, "till_date", item.date);
			}
		} else {
			if (item.till_date < item.date) {
				msgprint("Till Date cannot be earlier than From Date");
				frappe.model.set_value(cdt, cdn, "till_date", "");
			}
		}
		
		if (item.till_date >= item.date) {
                        frappe.model.set_value(cdt, cdn, "no_days", 1 + cint(frappe.datetime.get_day_diff(item.till_date, item.date)))
                }
		/*
		if(item.till_date){
			if (item.till_date >= item.date) {
				frappe.model.set_value(cdt, cdn, "no_days", 1 + cint(frappe.datetime.get_day_diff(item.till_date, item.date)))
			}
			else{
				msgprint("Till Date cannot be earlier than From Date")
				frappe.model.set_value(cdt, cdn, "till_date", "")
			}
		} else {
			if(!item.halt) {
				frappe.model.set_value(cdt, cdn, "till_date", item.date);
			}
		}
		*/
		if(frm.doc.need_advance) {
                        calculate_advance(frm);
                }

	},
		
	"till_date": function(frm, cdt, cdn) {
		var item = locals[cdt][cdn]
		if (item.till_date >= item.date) {
			frappe.model.set_value(cdt, cdn, "no_days", 1 + cint(frappe.datetime.get_day_diff(item.till_date, item.date)))
		}
		else {
			if(item.till_date) {
				msgprint("Till Date cannot be earlier than From Date")
				frappe.model.set_value(cdt, cdn, "till_date", "")
			}
		}
	},
	
	"halt": function(frm, cdt, cdn) {
		var item = locals[cdt][cdn]
		cur_frm.toggle_reqd("till_date", item.halt);
		if(!item.halt) {
			//frappe.model.set_value(cdt, cdn, "no_days", 1)
			frappe.model.set_value(cdt, cdn, "temp_till_date", (item.till_date || item.date));
			frappe.model.set_value(cdt, cdn, "till_date", item.date)
			frappe.model.set_value(cdt, cdn, "from_place", item.temp_from_place);
			frappe.model.set_value(cdt, cdn, "to_place", item.temp_to_place);
			frappe.model.set_value(cdt, cdn, "temp_halt_at", item.halt_at);
			frappe.model.set_value(cdt, cdn, "halt_at", "");
		} else {
			frappe.model.set_value(cdt, cdn, "temp_from_place", item.from_place);
			frappe.model.set_value(cdt, cdn, "temp_to_place", item.to_place);
			frappe.model.set_value(cdt, cdn, "from_place", "");
			frappe.model.set_value(cdt, cdn, "to_place", "");
			frappe.model.set_value(cdt, cdn, "halt_at", item.temp_halt_at);
			frappe.model.set_value(cdt, cdn, "till_date", item.temp_till_date || item.date);
		}
	},
	items_remove: function(frm)
                {
                if(frm.doc.need_advance) {
                        calculate_advance(frm);
                }
        }

});


function calculate_advance(frm) {
         frm.call({
                        method: "set_estimate_amount",
                        doc: frm.doc
                });
        }

function update_advance_amount(frm) {
	frappe.call({
		method: "erpnext.hr.doctype.travel_authorization.travel_authorization.get_exchange_rate",
		args: {
			"from_currency": frm.doc.currency,
			"to_currency": "BTN"
		},
		callback: function(r) {
			if(r.message) {
				frm.set_value("advance_amount_nu", flt(frm.doc.advance_amount) * flt(r.message));
				/* ++++++++++ Ver 2.0.190419 Begins ++++++++++*/
				// Following lines commented as they are getting updated with null values and also serves no purpose
				//frm.set_value("advance_amount", format_currency(flt(frm.doc.advance_amount), frm.doc.currency))
				//frm.set_value("estimated_amount", format_currency(flt(frm.doc.estimated_amount), frm.doc.currency))
				/* ++++++++++ Ver 2.0.190419 Ends ++++++++++++*/
			}
		}
	})
}

frappe.form.link_formatters['Employee'] = function(value, doc) {
	return value
}

/*frappe.ui.form.on("Travel Authorization","before_cancel", function(frm) {
	var d = frappe.prompt({
		fieldtype: "Select",
		fieldname: "cancellation_reason",
		options: ["Change In Travel Plan","Wrong Data Entry", "Others"],
		reqd: 1,
		description: __("*This information shall be used for determining the frequency of TA cancellation")},
		function(data) {
			cur_frm.set_value("cancellation_reason",data.cancellation_reason);
			refresh_many(["cancellation_reason"]);
		},
		"Select the REASON why you are cancelling the Travel Authorization", 
		__("Update")
	);
})*/

frappe.ui.form.on("Travel Authorization", "after_save", function(frm, cdt, cdn){
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
