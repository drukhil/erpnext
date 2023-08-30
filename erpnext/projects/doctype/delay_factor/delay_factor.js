// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delay Factor', {
	setup: function(frm) {
		frm.get_field('items').grid.editable_fields = [
                        {fieldname: 'task_name', columns: 2},
			{fieldname: 'actual_from_date', columns: 2},
                        {fieldname: 'new_from_date', columns: 2},
                        {fieldname: 'actual_to_date', columns: 2},
			{fieldname: 'new_to_date', columns: 2},
                ];

	},

	from_date: function(frm) {
		if(frm.doc.to_date){
			calculate_duration(frm, frm.doc.from_date, frm.doc.to_date);
		}
	},
	to_date: function(frm) {
		if(frm.doc.from_date){
		calculate_duration(frm, frm.doc.from_date, frm.doc.to_date);
		}
	},
	get_tasks: function(frm) {
                return frappe.call({
                        method: "update_tasks",
                        doc: frm.doc,
                        callback: function(r, rt) {
                                frm.refresh_field("items");
                                frm.refresh_fields();
                        }
                });
        },
});


function calculate_duration(cur_frm, from_date, to_date) {
        frappe.call({
                method: "erpnext.projects.doctype.delay_factor.delay_factor.calculate_durations",
                 args: {
                        "from_date": from_date,
                        "to_date": to_date
                   },
                callback: function(r) {
                        if(r.message) {
                                cur_frm.set_value('no_of_days', r.message);
                        }
                }
        })
}
