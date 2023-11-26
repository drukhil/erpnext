// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("employee", "employee_name", "employee_name")
cur_frm.add_fetch("employee", "employee_subgroup", "grade")
cur_frm.add_fetch("employee", "designation", "designation")
cur_frm.add_fetch("employee", "department", "department")
cur_frm.add_fetch("employee", "division", "division")
cur_frm.add_fetch("employee", "branch", "branch")
cur_frm.add_fetch("employee", "cost_center", "cost_center")


frappe.ui.form.on('Vehicle Requisition', {
	onload: function(frm) {
		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today());
		}
		if(cur_frm.doc.head > 4){
			frm.set_df_property("additional_mto", "hidden", 0);
		}else{
			frm.set_df_property("additional_mto", "hidden", 1);
		}
	},
	refresh: function(frm) {
		cur_frm.set_query("travel_authorization", function() {
			return {
				"filters": {
			"employee": frm.doc.employee
				}
			};
		});
		if ((frm.doc.__islocal) || (frm.doc.workflow_state == 'Draft'))  {
			frm.set_df_property("mto", "hidden", 1);
			frm.set_df_property("additional_mto", "hidden", 1);
			
        }
				if(!frm.doc.__islocal && in_list(user_roles, "Fleet Manager")) {
					frm.set_df_property("driver", "read_only", 0)
					frm.set_df_property("second_driver", "read_only", 0)
					frm.set_df_property("equipment", "read_only", 0)
					frm.set_df_property("second_vehicle", "read_only", 0)
					
						}
		cur_frm.set_query("equipment", function() {
			return {
				"filters": {
			"branch": frm.doc.branch
				}
			};
		});
		cur_frm.set_query("second_vehicle", function() {
			return {
				"filters": {
			"branch": frm.doc.branch
				}
			};
		});
		cur_frm.set_query("driver", function() {
			return {
				
					filters: [
						['Employee', 'designation', 'in', ['Operator', 'Driver', 'GCE-NC2 (Driver)', "Admin. Assistant", 'GCE-NC2 (Light Driver)']],
						['Employee', 'branch', '=', frm.doc.branch],
						
						['Employee', 'status', '=', 'Active']
						]
				
			};
		});
		cur_frm.set_query("second_driver", function() {
			return {
				
					filters: [
						['Employee', 'designation', 'in', ['Operator', 'Driver', 'GCE-NC2 (Driver)', "Admin. Assistant", 'GCE-NC2 (Light Driver)']],
						['Employee', 'branch', '=', frm.doc.branch],
						
						['Employee', 'status', '=', 'Active']
						]
				
			};
		});
		


	},
	return_date: function() {
		if(cur_frm.doc.travel_date) {
			calculate_duration(cur_frm, cur_frm.doc.travel_date, cur_frm.doc.return_date);
	//cur_frm.set_value('total_duration', frappe.datetime.get_day_diff(cur_frm.doc.expected_end_date, cur_frm.doc.expected_start_date) + 1)
		}
	},
	head: function(frm){
		console.log(cur_frm.doc.head);
		if(cur_frm.doc.head > 4){
			frm.set_df_property("additional_mto", "hidden", 0);
		}else{
			frm.set_df_property("additional_mto", "hidden", 1);
		}
		
	}
});

frappe.ui.form.on("Vehicle Requisition", "after_save", function(frm, cdt, cdn){
	if(in_list(user_roles, "Fleet Manager")){
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
													send_mail: true,
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

function calculate_duration(cur_frm, from_date, to_date) {
	frappe.call({
			method: "erpnext.maintenance.doctype.vehicle_requisition.vehicle_requisition.calculate_durations",
			 args: {
					"from_date": from_date,
					"to_date": to_date
			   },
			callback: function(r) {
					if(r.message) {
						cur_frm.set_value('duration', r.message);
		}
	}
	})
}