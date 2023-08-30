// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee','employee_name','employee_name');
cur_frm.add_fetch('employee','employment_type','employee_type');

var le = 0.00;

frappe.ui.form.on("Leave Allocation", {
	onload: function(frm) {
		if(!frm.doc.from_date) frm.set_value("from_date", get_today());

		frm.set_query("employee", function() {
			return {
				query: "erpnext.controllers.queries.employee_query"
			}
		})
	},

	employee: function(frm) {
		//frm.trigger("calculate_total_leaves_allocated");								// Commented by SHIV on 2018/10/15
		get_leave_balance(frm.doc);														// Added by SHIV on 2018/10/15
	},

	// Following function added by SHIV on 2018/10/15
	from_date: function(frm){
		get_leave_balance(frm.doc);
	},
	
	leave_type: function(frm) {
		//frm.trigger("calculate_total_leaves_allocated");								// Commented by SHIV on 2018/10/15
		get_leave_balance(frm.doc);														// Added by SHIV on 2018/10/15
	},

	carry_forward: function(frm) {
		//frm.trigger("calculate_total_leaves_allocated");								// Commented by SHIV on 2018/10/15
		get_leave_balance(frm.doc);														// Added by SHIV on 2018/10/15
	},

	carry_forwarded_leaves: function(frm) {
		//frm.set_value("total_leaves_allocated",
		//	flt(frm.doc.carry_forwarded_leaves) + flt(frm.doc.new_leaves_allocated));
		//frm.trigger("calculate_total_leaves_allocated");								// Commented by SHIV on 2018/10/15
		get_leave_balance(frm.doc);														// Added by SHIV on 2018/10/15
	},

	new_leaves_allocated: function(frm) {
		//frm.set_value("total_leaves_allocated",
		//	flt(frm.doc.carry_forwarded_leaves) + flt(frm.doc.new_leaves_allocated));
		//frm.trigger("calculate_total_leaves_allocated");								// Commented by SHIV on 2018/10/15
		get_leave_balance(frm.doc);														// Added by SHIV on 2018/10/15
	},

	// Following code commented by SHIV on 2018/10/15
	/*
	calculate_total_leaves_allocated: function(frm) {

		frm.trigger("get_le_settings");
		
		if (cint(frm.doc.carry_forward) == 1 && frm.doc.leave_type && frm.doc.employee) {
			return frappe.call({
				method: "erpnext.hr.doctype.leave_allocation.leave_allocation.get_carry_forwarded_leaves",
				args: {
					"employee": frm.doc.employee,
					"date": frm.doc.from_date,
					"leave_type": frm.doc.leave_type,
					"carry_forward": frm.doc.carry_forward
				},
				callback: function(r) {
					if (!r.exc && r.message) {
						frm.set_value('carry_forwarded_leaves', r.message);
						console.log('le: '+le);
						console.log(flt(r.message) + flt(frm.doc.new_leaves_allocated));
						if (frm.doc.leave_type == 'Earned Leave'){
							if ((flt(r.message) + flt(frm.doc.new_leaves_allocated)) > flt(flt(le) ? flt(le):0.00)){
								frappe.msgprint("Earned Leave Balance "+((flt(r.message) + flt(frm.doc.new_leaves_allocated))-flt(le))+"/"+(flt(r.message) + flt(frm.doc.new_leaves_allocated))+" is lapsed.");
								frm.set_value("total_leaves_allocated",le);
							}
							else{
								frm.set_value("total_leaves_allocated",flt(r.message) + flt(frm.doc.new_leaves_allocated));
							}
						}
						else{
							frm.set_value("total_leaves_allocated",
								flt(r.message) + flt(frm.doc.new_leaves_allocated));							
						}
					}
				}
			})
		} else if (cint(frm.doc.carry_forward) == 0) {
			frm.set_value("carry_forwarded_leaves", 0);
			if (frm.doc.leave_type == 'Earned Leave'){
				if (flt(frm.doc.new_leaves_allocated) > (flt(le) ? flt(le):0.00) > 0.00){
					frappe.msgprint("Earned Leave Balance "+(flt(frm.doc.new_leaves_allocated)-flt(le))+"/"+flt(frm.doc.new_leaves_allocated)+" is lapsed.");
					frm.set_value("total_leaves_allocated", flt(le));
				}
				else{
					frm.set_value("total_leaves_allocated", flt(frm.doc.new_leaves_allocated));
				}
			}
			else{
				frm.set_value("total_leaves_allocated", flt(frm.doc.new_leaves_allocated));
			}
		}
	},
	
	get_le_settings: function(frm){
		return frappe.call({
			method: "erpnext.hr.doctype.leave_encashment.leave_encashment.get_le_settings",
			callback: function(r) {
				if (r.message) {
					le = flt(r.message.encashment_lapse);
				}
			}
		});
	}
	*/
})

// Following function created by SHIV on 2018/10/15
var get_leave_balance = function(doc){
	cur_frm.call({
		method: "set_total_leaves_allocated",
		doc: doc
	});
}
