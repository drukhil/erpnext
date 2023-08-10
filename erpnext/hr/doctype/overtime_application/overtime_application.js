// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("employee", "employee_name", "employee_name")
cur_frm.add_fetch("employee", "branch", "branch")

frappe.ui.form.on('Overtime Application', {
	onload: function(frm) {
		if(!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today())
		}
	},
	refresh: function(frm){
		//enable_disable(frm);
	},
	approver: function(frm) {
		if(frm.doc.approver){
			frm.set_value("approver_name", frappe.user.full_name(frm.doc.approver));
		}
	},
	employee: function(frm) {
		if (frm.doc.employee) {
			frappe.call({
				method: "erpnext.hr.doctype.employee.employee.get_overtime_rate",
				args: {
					employee: frm.doc.employee,
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value("rate", r.message)
					}
				}
			})
		}
	},
	rate: function(frm) {
		frm.set_value("total_amount", frm.doc.rate * frm.doc.total_hours)
	},
});

//Overtime Item  Details
frappe.ui.form.on("Overtime Application Item", {
	"number_of_hours": function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn);
	},
	items_remove: function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn);
	},
	//added by cety to check for holiday and double the rate by 50% on 31/07/2022
	"date": function(frm, cdt, cdn){
		check_holidays(frm, cdt, cdn);
	}
})

function calculate_time(frm, cdt, cdn) {
	var total_time = 0;
	frm.doc.items.forEach(function(d) {
		if(d.number_of_hours) {
			total_time += d.number_of_hours
		}	
	})
	frm.set_value("total_hours", total_time)
	frm.set_value("total_amount", total_time * frm.doc.rate)
	cur_frm.refresh_field("total_hours")
	cur_frm.refresh_field("total_amount")
}

function toggle_form_fields(frm, fields, flag){
	fields.forEach(function(field_name){
		frm.set_df_property(field_name, "read_only", flag);
	});
	
	if(flag){
		frm.disable_save();
	} else {
		frm.enable_save();
	}
}

function enable_disable(frm){
	var toggle_fields = [];
	var meta = frappe.get_meta(frm.doctype);

	for(var i=0; i<meta.fields.length; i++){
		if(meta.fields[i].hidden === 0 && meta.fields[i].read_only === 0 && meta.fields[i].allow_on_submit === 0){
			toggle_fields.push(meta.fields[i].fieldname);
		}
	}
	
	toggle_form_fields(frm, toggle_fields, 1);
	
	if(frm.doc.__islocal){
		toggle_form_fields(frm, toggle_fields, 0);
	}
	else {
		// Request Creator
		if(in_list(user_roles, "Employee") && (frm.doc.workflow_state.indexOf("Draft") >= 0 || frm.doc.workflow_state.indexOf("Rejected") >= 0)){
			if(frappe.session.user === frm.doc.owner){
				toggle_form_fields(frm, toggle_fields, 0);
			}
		}
		
		// OT Supervisor
		if(in_list(user_roles, "OT Supervisor") && frm.doc.workflow_state.indexOf("Waiting Approval") >= 0){
			if(frappe.session.user != frm.doc.owner){
				toggle_form_fields(frm, toggle_fields, 0);
			}
		}
		
		// OT Approver
		if(in_list(user_roles, "OT Approver") && frm.doc.workflow_state.indexOf("Verified by Supervisor") >= 0){
			toggle_form_fields(frm, toggle_fields, 0);
		}
	}
}

/*
frappe.ui.form.on("Overtime Application", "before_save", function(frm){
	if(in_list(user_roles, "Request User") || in_list(user_roles, "Request Manager")){
		if(frm.doc.workflow_state == 'Rejected' && !frm.doc.rejection_reason){
			frm.set_df_property("rejection_reason", "read_only", 0);
			frm.toggle_reqd(["rejection_reason"], 1);
		}
	}
});
*/

frappe.ui.form.on("Overtime Application", "after_save", function(frm, cdt, cdn){
	if(in_list(user_roles, "OT Supervisor") || in_list(user_roles, "OT Approver")){
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
										fieldname: 'rejection_reason',
										value: frm.doc.rejection_reason ?
											[frm.doc.rejection_reason, '['+String(frappe.session.user)+' '+String(frappe.datetime.nowdate())+']'+' : '+String(args.reason)].join('\n') : frm.doc.workflow_state
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
//#added by cety to check for holiday and double the rate by 50% on 31/07/2022
function check_holidays(frm, cdt, cdn){
	var item = locals[cdt][cdn];
	frappe.call({
		method: "erpnext.hr.doctype.overtime_application.overtime_application.get_holidays",
		args: {
			"employee": frm.doc.employee,
			"date": item.date
		},
		callback: function(r){
			if (r.message){
				item.is_holiday = 1
			}else{
				item.is_holiday = 0
			}
			frm.refresh_field('items')
		}
	})	
}