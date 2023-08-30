// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
/*
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
2.0		  		  SHIV		     2017/08/15         					Project Name & Task are added at 'Timesheet' level
																			inorder to provide flexibility in task based
																			progress logging.
2.0				  SHIV           2017/09/10                             Fields from_date, to_date, days are created for
																			days based progress.							
--------------------------------------------------------------------------------------------------------------------------                                                                          
*/
cur_frm.add_fetch('employee', 'employee_name', 'employee_name');

frappe.ui.form.on("Timesheet", {
	setup: function(frm) {
		// ++++++++++++++++++++ Ver 1.0 BEGINS ++++++++++++++++++++
		// Following code is commented by SHIV on 2017/08/11		
		/*
		frm.get_field('time_logs').grid.editable_fields = [
			{fieldname: 'billable', columns: 1},
			{fieldname: 'project', columns: 3},
			{fieldname: 'activity_type', columns: 2},
			{fieldname: 'from_time', columns: 3},
			{fieldname: 'hours', columns: 1}
		];
		*/

		// Follwoing code is added by SHIV on 2017/08/11
		frm.get_field('time_logs').grid.editable_fields = [
			{fieldname: 'description', columns: 3},
			{fieldname: 'from_date', columns: 2},
			{fieldname: 'to_date', columns: 2},
			{fieldname: 'days', columns: 1},
			{fieldname: 'target_quantity', columns: 1},
			{fieldname: 'target_quantity_complete', columns: 1},
		];
		
		frm.fields_dict.task.get_query = function() {
			return {
				filters:{
					'project': frm.doc.project
				}
			}
		}
		// +++++++++++++++++++++ Ver 1.0 ENDS +++++++++++++++++++++
		
		frm.fields_dict.employee.get_query = function() {
			return {
				filters:{
					'status': 'Active'
				}
			}
		}

		frm.fields_dict['time_logs'].grid.get_field('task').get_query = function(frm, cdt, cdn) {
			child = locals[cdt][cdn];
			return{
				filters: {
					'project': child.project,
					'status': ["!=", "Closed"]
				}
			}
		}
	},

	onload: function(frm){
		if (frm.doc.__islocal && frm.doc.time_logs) {
			calculate_time_and_amount(frm);
		}
	},

	refresh: function(frm) {
		if(frm.doc.docstatus==1) {
			if(!frm.doc.sales_invoice && frm.doc.total_billing_amount > 0){
				frm.add_custom_button(__("Make Sales Invoice"), function() { frm.trigger("make_invoice") },
					"icon-file-alt");
			}

			/*if(!frm.doc.salary_slip && frm.doc.employee){
				frm.add_custom_button(__("Make Salary Slip"), function() { frm.trigger("make_salary_slip") },
					"icon-file-alt");
			} */
		}

		// ++++++++++++++++++++ Ver 1.0 BEGINS ++++++++++++++++++++
		if(frappe.model.can_read("Project")) {
			frm.add_custom_button(__("Project"), function() {
				frappe.route_options = {"name": frm.doc.project}
				frappe.set_route("Form", "Project", frm.doc.project);
			}, __("View"), true);
		}
		
		if(frappe.model.can_read("Task")) {
			frm.add_custom_button(__("Task"), function() {
				frappe.route_options = {"name": frm.doc.task}
				frappe.set_route("Form", "Task", frm.doc.task);
			}, __("View"), true);
		}
		// +++++++++++++++++++++ Ver 1.0 ENDS +++++++++++++++++++++		
	},

	make_invoice: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.timesheet.timesheet.make_sales_invoice",
			frm: frm
		});
	},

	make_salary_slip: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.timesheet.timesheet.make_salary_slip",
			frm: frm
		});
	},
})

frappe.ui.form.on("Timesheet Detail", {	
	percent_complete: function(frm){
		calculate_time_and_amount(frm);
	},

	target_quantity_complete: function(frm, cdt, cdn){
		var child = locals[cdt][cdn];
		
		/*
		if(child.target_quantity_complete > child.target_quantity){
			msgprint(__("Achieved value cannot be more than Target value."));
			//frappe.model.set_value(cdt, cdn, "target_quantity_complete",child.target_quantity);
		}
		*/
		calculate_target_quantity_complete(frm);
	},
		
	time_logs_add: function(frm, cdt, cdn){
		populate_dates(frm, cdt, cdn);
	},	
		
	time_logs_remove: function(frm, cdt, cdn) {
		calculate_time_and_amount(frm);
		calculate_target_quantity_complete(frm);
		calculate_tot_days(frm, cdt, cdn);
	},

	from_time: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn)
	},
	
	to_time: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];

		if(frm._setting_hours) return;
		frappe.model.set_value(cdt, cdn, "hours", moment(child.to_time).diff(moment(child.from_time),
			"seconds") / 3600);
		//frappe.model.set_value(cdt, cdn, "days", (moment(child.to_time).startOf('day').diff(moment(child.from_time).startOf('day'),'days') || 0)+1);
	},	
	
	hours: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn)
	},

	// ++++++++++++++++++++ Ver 1.0 BEGINS ++++++++++++++++++++
	// Following functions created by SHIV on 10/09/2017
	from_date: function(frm, cdt, cdn){
		calculate_days(frm, cdt, cdn);
		calculate_tot_days(frm, cdt, cdn);
	},

	to_date: function(frm, cdt, cdn){
		calculate_days(frm, cdt, cdn);
		calculate_tot_days(frm, cdt, cdn);
	},	
	// +++++++++++++++++++++ Ver 1.0 ENDS +++++++++++++++++++++
	billing_rate: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	costing_rate: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	billable: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	activity_type: function(frm, cdt, cdn) {
		child = locals[cdt][cdn];
		frappe.call({
			method: "erpnext.projects.doctype.timesheet.timesheet.get_activity_cost",
			args: {
				employee: frm.doc.employee,
				activity_type: child.activity_type
			},
			callback: function(r){
				if(r.message){
					frappe.model.set_value(cdt, cdn, 'billing_rate', r.message['billing_rate']);
					frappe.model.set_value(cdt, cdn, 'costing_rate', r.message['costing_rate']);
					calculate_billing_costing_amount(frm, cdt, cdn)
				}
			}
		})
	}
});

// ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++
// Following function created by SHIV on 13/09/2017
var populate_dates = function(frm, cdt, cdn){
	var tl = frm.doc.time_logs || [];
	var child = locals[cdt][cdn];
	var flag = 0, balance_quantity = 0.0, total_quantity = 0.0;
	
	for(idx in tl){
		if (tl[idx].from_date){
			flag += 1;
		}
		total_quantity += parseFloat(tl[idx].target_quantity_complete || 0);
	}
	
	if (total_quantity >= parseFloat(frm.doc.target_quantity)){
		balance_quantity = 0.0;
	}
	else {
		balance_quantity = parseFloat(frm.doc.target_quantity || 0)-total_quantity;
	}
	
	if (frm.doc.docstatus != 1 && flag == 0){
		cur_frm.clear_table("time_logs");
		var row = frappe.model.add_child(frm.doc, "Timesheet Detail", "time_logs");
		row.from_date 		= frm.doc.exp_start_date;
		row.to_date 		= frm.doc.exp_end_date;
		row.days      		= (moment(row.to_date).diff(moment(row.from_date),'days') || 0)+1;
		row.target_quantity = parseFloat(balance_quantity);
	} else if(frm.doc.docstatus != 1 && flag > 0){
		min = tl.reduce(function(prev, curr){
						if(curr.from_date){
							return moment(prev.from_date).toDate() < moment(curr.from_date).toDate() ? prev : curr;
						} else {
							return prev;
						}
					});		

		max = tl.reduce(function(prev, curr){
						if(curr.to_date){
							return moment(prev.to_date).toDate() > moment(curr.to_date).toDate() ? prev : curr;
						} else {
							return prev;
						}
					});	
					
		if (min.from_date > frm.doc.exp_start_date && max.to_date < frm.doc.exp_end_date){
			frappe.model.set_value(cdt, cdn, "from_date", frm.doc.exp_start_date);
			frappe.model.set_value(cdt, cdn, "to_date", moment(min.from_date).add(-1,"days"));
			frappe.model.set_value(cdt, cdn, "target_quantity", balance_quantity);
			
			var row = frappe.model.add_child(frm.doc, "Timesheet Detail", "time_logs");
			row.from_date 		= moment(max.to_date).add(1,"days");
			row.to_date   		= frm.doc.exp_end_date;
			row.days      		= (moment(row.to_date).diff(moment(row.from_date),'days') || 0)+1;
			row.target_quantity = parseFloat(balance_quantity);
		} else if(min.from_date > frm.doc.exp_start_date){
			frappe.model.set_value(cdt, cdn, "from_date", frm.doc.exp_start_date);
			frappe.model.set_value(cdt, cdn, "to_date", moment(min.from_date).add(-1,"days"));
			frappe.model.set_value(cdt, cdn, "target_quantity", balance_quantity);
		} else if (max.to_date < frm.doc.exp_end_date){
			frappe.model.set_value(cdt, cdn, "from_date", moment(max.to_date).add(1,"days"));
			frappe.model.set_value(cdt, cdn, "to_date", frm.doc.exp_end_date);		
			frappe.model.set_value(cdt, cdn, "target_quantity", balance_quantity);
		}
	}
	
	/*




	*/
	//frappe.model.set_value("Timesheet Detail", tl[0].name, 'from_date', frm.doc.exp_start_date);


	/*
	if (!min.from_date && !max.to_date){
		//frappe.model.set_value(cdt, cdn, 'from_date', frm.doc.exp_start_date);
		frappe.model.set_value("Timesheet Detail", tl[0].name, 'from_date', frm.doc.exp_start_date);
	}
*/	
}
// +++++++++++++++++++++ Ver 2.0 ENDS +++++++++++++++++++++

calculate_end_time = function(frm, cdt, cdn){
	var child = locals[cdt][cdn];

	var d = moment(child.from_time);
	d.add(child.hours, "hours");
	//console.log(moment(child.from_time).startOf('day').toDate());
	frm._setting_hours = true;
	frappe.model.set_value(cdt, cdn, "to_time", d.format(moment.defaultDatetimeFormat));
	frm._setting_hours = false;

	calculate_billing_costing_amount(frm, cdt, cdn)
}

// ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++
// Following function created by SHIV on 10/09/2017
calculate_days = function(frm, cdt, cdn){
	var child = locals[cdt][cdn];
	
	if(child.to_date){
		frappe.model.set_value(cdt, cdn, "days", (moment(child.to_date).diff(moment(child.from_date),'days') || 0)+1);
	}
	else {
		frappe.model.set_value(cdt, cdn, "days", 0);
	}	
}

calculate_tot_days = function(frm, cdt, cdn){
	var tl = frm.doc.time_logs || [];
	total_days = 0;

	for(var i=0; i<tl.length; i++) {
		if (tl[i].days) {
			total_days += (tl[i].days || 0);
		}
	}
	
	if(total_days){
		cur_frm.set_value("total_days", total_days);
	}
	
}
// +++++++++++++++++++++ Ver 2.0 ENDS +++++++++++++++++++++

var calculate_billing_costing_amount = function(frm, cdt, cdn){
	child = locals[cdt][cdn]
	billing_amount = costing_amount = 0.0;

	if(child.hours && child.billable){
		billing_amount = (child.hours * child.billing_rate);
		costing_amount = flt(child.costing_rate * child.hours);
	}

	frappe.model.set_value(cdt, cdn, 'billing_amount', billing_amount);
	frappe.model.set_value(cdt, cdn, 'costing_amount', costing_amount);
	calculate_time_and_amount(frm)
}

// ++++++++++++++++++++ Ver 1.0 BEGINS ++++++++++++++++++++
// Following function created by SHIV on 2017/08/17
var calculate_target_quantity_complete = function(frm){
	var tl = frm.doc.time_logs || [];
	total_target_quantity_complete = 0.0;
	total_work_quantity_complete = 0.0;
	
	for(var i=0; i<tl.length; i++) {
		if (tl[i].target_quantity_complete) {
			total_target_quantity_complete += parseFloat(tl[i].target_quantity_complete || 0);
		}
	}
	
	cur_frm.set_value("work_quantity_complete",parseFloat(frm.doc.work_quantity)*(parseFloat(total_target_quantity_complete)/(frm.doc.target_quantity || 1)));
	
	/*
	// Commented on 2018/15/05 because child records somehow not getting docstatus=2 even when parent is cancelled.
	frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Timesheet Detail",
				filters: {
					task: frm.doc.task,
					docstatus: ["<",2]
				},
				fields:["parent","target_quantity_complete"]
			},
			callback: function(r){
				$.each(r.message, function(i, d){
					if (d.parent != frm.doc.name){
						total_target_quantity_complete += parseFloat(d.target_quantity_complete || 0);
					}
				})
				cur_frm.set_value("target_quantity_complete", parseFloat(total_target_quantity_complete));
			}
	});
	*/

	frappe.call({
		method: "erpnext.projects.doctype.timesheet.timesheet.get_target_quantity_complete",
		args: {
			"docname": frm.doc.name,
			"task": frm.doc.task
		},
		callback: function(r){
			if(r.message){
				total_target_quantity_complete += parseFloat(r.message)
				cur_frm.set_value("target_quantity_complete", parseFloat(total_target_quantity_complete));
			}
			else {
				cur_frm.set_value("target_quantity_complete", parseFloat(total_target_quantity_complete));
			}
		}
	});
	
	/*
	frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Task",
				filters: {
					name: frm.doc.task
				},
				fieldname:["target_quantity_complete"]
			},
			callback: function(r){
				cur_frm.set_value("target_quantity_complete", (r.message.target_quantity_complete || 0) + (total_target_quantity_complete || 0));
			}
	})
	*/
}
// +++++++++++++++++++++ Ver 1.0 ENDS +++++++++++++++++++++	

var calculate_time_and_amount = function(frm) {
	var tl = frm.doc.time_logs || [];
	total_hr = 0;
	total_billing_amount = 0;
	total_costing_amount = 0;
		
	for(var i=0; i<tl.length; i++) {
		if (tl[i].hours) {
			total_hr += tl[i].hours || 0;
			total_billing_amount += tl[i].billing_amount;
			total_costing_amount += tl[i].costing_amount;
		}
	}

	cur_frm.set_value("total_hours", total_hr);
	cur_frm.set_value("total_billing_amount", total_billing_amount);
	cur_frm.set_value("total_costing_amount", total_costing_amount);
}
