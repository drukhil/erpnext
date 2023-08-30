// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee','employee_name','employee_name');
cur_frm.add_fetch('employee','company','company');
<<<<<<< HEAD
cur_frm.add_fetch('verifier', 'employee_name', 'verifier_name');
=======
>>>>>>> 481acce0b0473e02e508b18258351a662b38a341

frappe.ui.form.on("Leave Application", {
	onload: function(frm) {
		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today());
		}

		frm.set_query("leave_approver", function() {
			return {
				query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
				filters: {
					employee: frm.doc.employee
				}
			};
		});
<<<<<<< HEAD
	
		
=======

>>>>>>> 481acce0b0473e02e508b18258351a662b38a341
		frm.set_query("employee", erpnext.queries.employee);

		if(frm.doc.__islocal) {
			frm.trigger("get_employee_branch_costcenter");
        }		
	},

	/*refresh: function(frm) {
		if (frm.is_new()) {
			frm.set_value("status", "Open");
			frm.trigger("calculate_total_days");
		}
				
		if(!frm.doc.__islocal && in_list(user_roles, "Approver")){
			if(frappe.session.user == frm.doc.leave_approver){
				frm.toggle_display("status", true);
			}
			else{
				frm.toggle_display("status", false);
			}
		}
		else{
			frm.toggle_display("status", false);
		}
	},*/

	leave_approver: function(frm) {
		if(frm.doc.leave_approver){
			frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
		}
	},

	employee: function(frm) {
<<<<<<< HEAD
		/*frappe.call({
                        'method': 'erpnext.custom_workflow.approver_list',
                        'args': {'employee': frm.doc.employee },
                       callback: function(r){
                           if (r.message) {
                                //cur_frm.set_value("leave_approver", r.message.verifier);    
                                //cur_frm.set_value("approver", r.message.approver);    
				//cur_frm.set_df_property("next_depreciation_date", "hidden", true);
                                 }
                        }
                })
	
		frappe.call({
			method: "erpnext.custom_workflow.validate_workflow_states",
			doc: frm.doc
		})
		frm.trigger("get_employee_branch_costcenter")
		frm.trigger("get_leave_balance");*/
=======
		frm.trigger("get_employee_branch_costcenter")
		frm.trigger("get_leave_balance");
>>>>>>> 481acce0b0473e02e508b18258351a662b38a341
	},

	leave_type: function(frm) {
		frm.trigger("get_leave_balance");
	},

	half_day: function(frm) {
		if (frm.doc.from_date) {
			frm.set_value("to_date", frm.doc.from_date);
			frm.trigger("calculate_total_days");
		}
	},
	include_half_day: function(frm) {
		if (frm.doc.from_date) {
			frm.trigger("calculate_total_days");
		}
	},
	from_date: function(frm) {
		if (cint(frm.doc.half_day)==1) {
			frm.set_value("to_date", frm.doc.from_date);
		}
		frm.trigger("get_leave_balance");
		frm.trigger("calculate_total_days");
	},

	to_date: function(frm) {
		if (cint(frm.doc.half_day)==1 && cstr(frm.doc.from_date) && frm.doc.from_date != frm.doc.to_date) {
			msgprint(__("To Date should be same as From Date for Half Day leave"));
			frm.set_value("to_date", frm.doc.from_date);
		}

		frm.trigger("calculate_total_days");
	},

	get_employee_branch_costcenter: function(frm){
		/*
		if((frm.doc.docstatus==0 || frm.doc.__islocal) && frm.doc.employee){
			frappe.call({
						method: "erpnext.custom_utils.get_user_info",
						args: {"employee": frm.doc.employee},
						callback(r) {
								cur_frm.set_value("cost_center", r.message.cost_center);
								cur_frm.set_value("branch", r.message.branch);
						}
			});
		}
		*/
		if((frm.doc.docstatus==0 || frm.doc.__islocal) && frm.doc.employee){
			cur_frm.add_fetch("employee", "branch", "branch");
			cur_frm.add_fetch("employee", "cost_center", "cost_center");
		}
	},
	
	get_leave_balance: function(frm) {
		//if(frm.doc.docstatus==0 && frm.doc.employee && frm.doc.leave_type && frm.doc.from_date) {
		if(frm.doc.docstatus==0 && frm.doc.employee && frm.doc.leave_type) {
			return frappe.call({
				method: "erpnext.hr.doctype.leave_application.leave_application.get_leave_balance_on",
				args: {
					employee: frm.doc.employee,
					ason_date: frm.doc.from_date || frappe.datetime.get_today(),
					leave_type: frm.doc.leave_type,
					consider_all_leaves_in_the_allocation_period: true
				},
				callback: function(r) {
					if (!r.exc && r.message) {
						frm.set_value('leave_balance', parseFloat(r.message));
					}
					else{
						frm.set_value('leave_balance', 0.0);
					}
				}
			});
		}
	},

	calculate_total_days: function(frm) {
		if(frm.doc.from_date && frm.doc.to_date) {
			if (cint(frm.doc.half_day)==1) {
				frm.set_value("total_leave_days", 0.5);
			} else if (frm.doc.employee && frm.doc.leave_type){
				// server call is done to include holidays in leave days calculations
				return frappe.call({
					method: 'erpnext.hr.doctype.leave_application.leave_application.get_number_of_leave_days',
					args: {
						"employee": frm.doc.employee,
						"leave_type": frm.doc.leave_type,
						"from_date": frm.doc.from_date,
						"to_date": frm.doc.to_date,
						//"half_day": frm.doc.half_day
					},
					callback: function(r) {
						if (r && r.message) {
							if(frm.doc.include_half_day == 1) {
								frm.set_value('total_leave_days', r.message - 0.5);
							} else {
								frm.set_value('total_leave_days', r.message);
							}
							frm.trigger("get_leave_balance");
							cur_frm.refresh_field("total_leave_days")
						}
					}
				});
			}
		}
	},

});

//custom Scripts
frappe.ui.form.on("Leave Application", "before_save", function(frm) {
    if (!frm.doc.employee_name && frm.doc.employee) {
        frappe.call({
            'method': 'frappe.client.get',
            'args': {
                  'doctype': 'Employee',
                  'filters': {
                       'name': frm.doc.employee
                  },
                  'fields':['employee_name', 'name']
             },
             callback: function(r){
                  if (r.message) {
                     cur_frm.set_value("employee_name", r.message.employee_name);
                     cur_frm.set_value("employee", r.message.name);
                     refresh_field('employee_name');
                     refresh_field('employee');
                  }
             }
          });
    }
});

frappe.ui.form.on("Leave Application", "onload", function(frm) {
    if (!frm.doc.employee_name && frm.doc.employee) {
        frappe.call({
            'method': 'frappe.client.get',
            'args': {
                  'doctype': 'Employee',
                  'filters': {
                       'name': frm.doc.employee
                  },
                  'fields':['employee_name', 'name']
             },
             callback: function(r){
                  if (r.message) {
                     cur_frm.set_value("employee_name", r.message.employee_name);
                     cur_frm.set_value("employee", r.message.name);
                     refresh_field('employee_name');
                     refresh_field('employee');
                  }
             }
          });
    }
});

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
            if(in_list(user_roles, "Employee") && (frm.doc.workflow_state.indexOf("Draft") >= 0 || frm.doc.workflow_state.indexOf("Rejected") >= 0)) {                         if (frappe.session.user == frm.doc.owner){
                                           	toggle_form_fields(frm, toggle_fields, 0);
                         	                    }                                                                     	                                    }
                                                               	                                                    
                                                            	                                                                    
           
                                                                 	                                                                                    // Request Approver
                                                                   	                                                                                                    if(in_list(user_roles, "Approver") && frm.doc.workflow_state.indexOf("Waiting Approval") >= 0){
                                                                  	                                                                                                                        if (frappe.session.user != frm.doc.owner){
                                                                   	                                                                                                                                            	toggle_form_fields(frm, toggle_fields, 0);
                                                                   	                                                                                                          }
                                                                      	                                                                                            }
                  }
	}

frappe.ui.form.on("Leave Application", "after_save", function(frm, cdt, cdn){
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
