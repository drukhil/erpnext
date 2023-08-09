// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("cost_center", "branch", "branch")
cur_frm.add_fetch("project", "cost_center", "cost_center")
cur_frm.add_fetch("project", "branch", "branch")

frappe.ui.form.on('Muster Roll Employee', {
	refresh: function(frm) {
	},

	rate_per_day: function(frm) {
		if(frm.doc.rate_per_day) {
			frm.set_value("rate_per_hour", (frm.doc.rate_per_day * 1.5) / 8)
			frm.refresh_field("rate_per_hour")
		}
	},

	"status": function(frm) {
		cur_frm.toggle_reqd("separation_date", frm.doc.status == "Left")
	},
	
	cost_center: function(frm){
		if(!frm.doc.__islocal){
			cur_frm.set_value("date_of_transfer",frappe.datetime.nowdate());
			refresh_many(["date_of_transfer"]);
			validate_prev_doc(frm,__("Please select date of transfer to new cost center"));		
		}
	},

});

frappe.ui.form.on("Muster Roll Employee", "refresh", function(frm) {
    cur_frm.set_query("cost_center", function() {
        return {
            "filters": {
		"is_group": 0,
		"is_disabled": 0
            }
        };
    });
})

function validate_prev_doc(frm, title){
	return frappe.call({
				method: "erpnext.custom_utils.get_prev_doc",
				args: {doctype: frm.doctype, docname: frm.docname, col_list: "cost_center,branch"},
				callback: function(r) {
					if(frm.doc.cost_center && (frm.doc.cost_center !== r.message.cost_center)){
						console.log(frm);
						console.log(r);
						var d = frappe.prompt({
							fieldtype: "Date",
							fieldname: "date_of_transfer",
							reqd: 1,
							description: __("*This information shall be recorded in employee internal work history.")},
							function(data) {
								cur_frm.set_value("date_of_transfer",data.date_of_transfer);
								refresh_many(["date_of_transfer"]);
							},
							title, 
							__("Update")
						);
					}
				}
		});
}

frappe.ui.form.on('Musterroll', {
	"rate_per_day": function(frm, cdt ,cdn) {
	var wages =locals[cdt][cdn];
	if(wages.rate_per_day) {
		frappe.model.set_value(wages.doctype, wages.name, "rate_per_hour", flt((flt(wages.rate_per_day) * 1.5)/8));
		frm.refresh_field("rate_per_hour")

		frappe.model.set_value(wages.doctype, wages.name, "rate_per_hour_normal", flt(flt(wages.rate_per_day)/8));
		frm.refresh_field("rate_per_hour_normal")
		}
	},
	})
