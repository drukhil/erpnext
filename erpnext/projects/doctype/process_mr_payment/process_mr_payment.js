// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("project", "branch", "branch")
cur_frm.add_fetch("project", "cost_center", "cost_center")
cur_frm.add_fetch("cost_center", "branch", "branch")

frappe.ui.form.on('Process MR Payment', {
	setup: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;
	},
	refresh: function(frm) {
		if (frm.doc.payment_jv && frappe.model.can_read("Journal Entry")) {
			cur_frm.add_custom_button(__('Bank Entries'), function() {
				frappe.route_options = {
					"Journal Entry Account.reference_type": me.frm.doc.doctype,
					"Journal Entry Account.reference_name": me.frm.doc.name,
				};
				frappe.set_route("List", "Journal Entry");
			}, __("View"));
		}
	},

	onload: function(frm) {
		if(!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today())	
		}
	},

	project: function(frm) {
		cur_frm.set_df_property("cost_center", "read_only", frm.doc.project ? 1 : 0) 
	},

	load_records: function(frm) {
		//cur_frm.set_df_property("load_records", "disabled",  true);

		//if(frm.doc.from_date && frm.doc.cost_center && frm.doc.employee_type && frm.doc.from_date < frm.doc.to_date) {
		if(frm.doc.cost_center && frm.doc.employee_type) {
			get_records(frm.doc.employee_type, frm.doc.fiscal_year, frm.doc.month, frm.doc.cost_center, frm.doc.branch, frm.doc.name)
		}
	},

	load_employee: function(frm) {
		//load_accounts(frm.doc.company)
		return frappe.call({
			method: "load_employee",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("items");
				frm.refresh_fields();
			}
		});
	},
	// employee_type: function(frm){
	// 	update_is_holiday_overtime_entry(frm);
	// },
	// cost_center: function(frm){
	// 	update_is_holiday_overtime_entry(frm);
	// },
	// fiscal_year: function(frm){
	// 	update_is_holiday_overtime_entry(frm);
	// },
	// month: function(frm){
	// 	update_is_holiday_overtime_entry(frm);
	// }
});

function get_records(employee_type, fiscal_year, month, cost_center, branch, dn) {
	cur_frm.clear_table("items");
	cur_frm.refresh_field("items");
	frappe.call({
		method: "erpnext.projects.doctype.process_mr_payment.process_mr_payment.get_records",
		args: {
			"fiscal_year": fiscal_year,
			"fiscal_month": month,
			"cost_center": cost_center,
			"branch": branch,
			"employee_type": employee_type,
			"dn": dn
		},
		freeze: true,
		freeze_message: "Loading wage details. Please Wait...",
		callback: function(r) {
			if(r.message) {
				var total_overall_amount = 0;
				var ot_amount = 0; 
				var wages_amount = 0;
				//cur_frm.clear_table("items");
				console.log(r.message);
				r.message.forEach(function(mr) {
					if(mr['number_of_days'] > 0 || mr['number_of_hours'] > 0) {
						var row = frappe.model.add_child(cur_frm.doc, "MR Payment Item", "items");
		
						row.employee_type 	= mr['type'];
						row.employee 		= mr['employee'];
						row.person_name 	= mr['person_name'];
						row.id_card 		= mr['id_card'];
						row.fiscal_year 	= fiscal_year;
						row.month 			= month;
						row.number_of_days 	= mr['number_of_days'];
						row.number_of_hours = flt(mr['number_of_hours']);
						row.number_of_hours_special = flt(mr['number_of_hours_special']);
						row.bank = mr['bank'];
						row.account_no = mr['account_no'];
						row.designation = mr['designation'];
						if(mr['type'] == 'GEP Employee'){
							row.daily_rate      = flt(mr['salary'])/flt(mr['noof_days_in_month']);
							row.hourly_rate     = flt(mr['salary']*1.5)/flt(mr['noof_days_in_month']*8);
							row.total_ot_amount = flt(row.number_of_hours) * flt(row.hourly_rate);
							row.total_wage      = flt(row.daily_rate) * flt(row.number_of_days);
							console.log(row.total_ot_amount);
							if((flt(row.total_wage) > flt(mr['salary']))||(flt(mr['noof_days_in_month']) == flt(mr['number_of_days']))){
								row.total_wage = flt(mr['salary']);
							}
						} else {
							row.daily_rate 	= flt(mr['rate_per_day']);
							row.hourly_rate 	= flt(mr['rate_per_hour']); // Holiday Rate
							row.hourly_rate_normal = flt(mr['rate_per_hour_normal']);
							//row.total_ot_amount = flt(mr['total_ot']);
							//row.total_wage 		= flt(mr['total_wage']);
							row.total_ot_amount = flt(mr['number_of_hours']) * flt(mr['rate_per_hour_normal']) + flt(mr['number_of_hours_special']) * flt(mr['rate_per_hour'])
							row.total_wage 		= flt(mr['rate_per_day']) * flt(mr['number_of_days'])
						}
						
						/*
						if(mr['type'] == 'GEP Employee' && flt(row.total_wage) > flt(mr['salary'])){
							row.total_wage = flt(mr['salary']);
						}
						else if(mr['type'] == 'GEP Employee' && flt(mr['noof_days_in_month']) == flt(mr['number_of_days'])){
							row.total_wage = flt(mr['salary']);
						}
						*/
						
						row.total_amount 	= flt(row.total_ot_amount) + flt(row.total_wage);
						refresh_field("items");

						total_overall_amount += row.total_amount;
						ot_amount 			 += row.total_ot_amount;
						wages_amount 		 += row.total_wage;
					}
				});

				cur_frm.set_value("total_overall_amount", total_overall_amount)
				cur_frm.set_value("wages_amount", flt(wages_amount))
				cur_frm.set_value("ot_amount", flt(ot_amount))
				cur_frm.refresh_field("total_overall_amount")
				cur_frm.refresh_field("wages_amount")
				cur_frm.refresh_field("ot_amount")
				cur_frm.refresh_field("items");
			}
			else {
				frappe.msgprint("No Overtime and Attendance Record Found")
			}
		}
	})
}


// function update_is_holiday_overtime_entry(frm){
// 	if (frm.doc.employee_type && frm.doc.cost_center){
// 		frappe.call({
// 			method: "erpnext.projects.doctype.process_mr_payment.process_mr_payment.update_is_holiday_overtime_entry",
// 			args: {
// 				"employee_type": frm.doc.employee_type,
// 				"branch": frm.doc.branch,
// 				"fiscal_year": frm.doc.fiscal_year,
// 				"fiscal_month": frm.doc.month
// 			},
// 			callback: function(r){
// 				console.log(r.message);
// 			}
// 		})
// 	}
// }