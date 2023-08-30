// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.cscript.display_activity_log = function(msg) {
	if(!cur_frm.ss_html)
		cur_frm.ss_html = $a(cur_frm.fields_dict['activity_log'].wrapper,'div');
	if(msg) {
		cur_frm.ss_html.innerHTML =
			'<div class="padding"><h4>'+__("Activity Log:")+'</h4>'+msg+'</div>';
	} else {
		cur_frm.ss_html.innerHTML = "";
	}
}

//Create salary slip
//-----------------------
/*cur_frm.cscript.create_salary_slip = function(doc, cdt, cdn) {
	cur_frm.cscript.display_activity_log("<div style='width: 100%; height: 20px;z-index: 15;'><img src='/assets/erpnext/images/hloading.gif' width='100%' height='100%' /></div>");
	var callback = function(r, rt){
		if (r.message)
			cur_frm.cscript.display_activity_log(r.message);
	}
	return $c('runserverobj', args={'method':'create_sal_slip','docs':doc},callback);
} 

cur_frm.cscript.submit_salary_slip = function(doc, cdt, cdn) {
	frappe.confirm(__("Do you really want to Submit all Salary Slip for month {0} and year {1}", [doc.month, doc.fiscal_year]), function() {
		cur_frm.cscript.display_activity_log("<div style='width: 100%; height: 20px;z-index: 15;'><img src='/assets/erpnext/images/hloading.gif' width='100%' height='100%' /></div>");
		// clear all in locals
		if(locals["Salary Slip"]) {
			$.each(locals["Salary Slip"], function(name, d) {
				frappe.model.remove_from_locals("Salary Slip", name);
			});
		}

		var callback = function(r, rt){
			if (r.message)
				cur_frm.cscript.display_activity_log(r.message);
		}

		return $c('runserverobj', args={'method':'submit_salary_slip','docs':doc},callback);
	});
}

// Ver 20160702.1 by SSK, accounts_posting is added
cur_frm.cscript.accounts_posting = function(doc, cdt, cdn) {
	frappe.confirm(__("Do you really want to Post Payroll to Accounts for month {0} and year {1}?", [doc.month, doc.fiscal_year]), function() {
		cur_frm.cscript.display_activity_log("<div style='width: 100%; height: 20px;z-index: 15;'><img src='/assets/erpnext/images/hloading.gif' width='100%' height='100%' /></div>");
		// clear all in locals
		if(locals["Salary Slip"]) {
			$.each(locals["Salary Slip"], function(name, d) {
				frappe.model.remove_from_locals("Salary Slip", name);
			});
		}

		var callback = function(r, rt){
			if (r.message)
				cur_frm.cscript.display_activity_log(r.message);
		}

		return $c('runserverobj', args={'method':'make_journal_entry1','docs':doc},callback);
	});
} */

cur_frm.cscript.make_bank_entry = function(doc,cdt,cdn){
    if(doc.company && doc.month && doc.fiscal_year){
    	cur_frm.cscript.make_jv(doc, cdt, cdn);
    } else {
  	  msgprint(__("Company, Month and Fiscal Year is mandatory"));
    }
}

cur_frm.cscript.make_jv = function(doc, dt, dn) {
	return $c_obj(doc, 'make_journal_entry', '', function(r) {
		var doc = frappe.model.sync(r.message)[0];
		frappe.set_route("Form", doc.doctype, doc.name);
	});
}

frappe.ui.form.on("Process Payroll", {
	refresh: function(frm) {
		frm.disable_save();
	},

	create_salary_slip: function(frm){
		process_salary(frm, "create");
	},
	
	remove_salary_slip: function(frm) {
        process_salary(frm, "remove");
    },

	submit_salary_slip: function(frm){
		process_salary(frm, "submit");
	},
	// Commented by SHIV on 2018/10/15
	/*
	"create_salary_slip": function(frm) {
                return frappe.call({
                        method: "create_sal_slip",
                        doc: frm.doc,
                        callback: function(r, rt) {
                                frm.refresh_fields();
                                if (r.message)
                                        cur_frm.cscript.display_activity_log(r.message);
                        },
                        freeze: true,
                        freeze_message: "Processing Salary.... Please Wait",
                });
    },
	"remove_salary_slip": function(frm) {
                return frappe.call({
                        method: "remove_sal_slip",
                        doc: frm.doc,
                        callback: function(r, rt) {
                                frm.refresh_fields();
                                if (r.message)
                                        cur_frm.cscript.display_activity_log(r.message);
                        },
                        freeze: true,
                        freeze_message: "Removing Salary.... Please Wait!!!",
                });
    },
	
	submit_salary_slip: function(frm) {
		frappe.confirm(__("Do you really want to Submit all Salary Slip for month {0} and year {1}", [frm.doc.month, frm.doc.fiscal_year]), function() {
				if(locals["Salary Slip"]) {
						$.each(locals["Salary Slip"], function(name, d) {
								frappe.model.remove_from_locals("Salary Slip", name);
						});
				}

				return frappe.call({
						method: "submit_salary_slip",
						doc: frm.doc,
						callback: function(r, rt) {
								frm.refresh_fields();
								if (r.message)
										cur_frm.cscript.display_activity_log(r.message);
						},
						freeze: true,
						freeze_message: "Submitting Salary.... Please Wait!!!",
				});
		})
    },
	*/
	
	accounts_posting: function(frm) {
		frappe.confirm(__("Do you really want to Submit all Salary Slip for month {0} and year {1}", [frm.doc.month, frm.doc.fiscal_year]), function() {
				if(locals["Salary Slip"]) {
						$.each(locals["Salary Slip"], function(name, d) {
								frappe.model.remove_from_locals("Salary Slip", name);
						});
				}

				return frappe.call({
						method: "make_journal_entry1",
						doc: frm.doc,
						callback: function(r, rt) {
								frm.refresh_fields();
								if (r.message)
										cur_frm.cscript.display_activity_log(r.message);
						},
						freeze: true,
						freeze_message: "Posting Journal.... Please Wait!!!",
				});
		})
	}
});


//custom Scripts
//Ver20160705.1 Original version Added by SSK

/*
cur_frm.fields_dict['division'].get_query = function(doc, dt, dn) {
       return {
               filters:{"dpt_name": doc.department, "branch": doc.branch}
       }
}
*/

//Added by SHIV on 2018/10/15
var process_salary = function(frm, process_type){
	var head_log="", body_log="", msg="", msg_other="";
	cur_frm.cscript.display_activity_log('');
	head_log = '<div class="container"><h4>'+__("Activity Log:")+'</h4><table class="table">';
	frm.set_value("progress", "");
	frm.refresh_field("progress");
	
	if(process_type == "create"){
		msg = "Creating Salary Slip(s).... Please Wait!!!";
		msg_other = "created";
	} else if(process_type == "remove"){
		msg = "Removing Salary Slip(s).... Please Wait!!!";
		msg_other = "removed";
	} else{
		msg = "Submitting Salary Slip(s).... Please Wait!!!";
		msg_other = "submitted";
	}
	
	return frappe.call({
		method: "get_emp_list",
		doc: frm.doc,
		args: {"process_type": process_type},
		callback: function(r, rt){
			if(r.message){
				var counter=0;
				r.message.forEach(function(rec) {
					counter += 1;
					frm.set_value("progress", "Processing "+counter+"/"+r.message.length+" salary slip(s) ["+Math.round((counter/r.message.length)*100)+"% completed]");
					frm.refresh_field("progress");
					frm.refresh_field("activity_log");
					cur_frm.call({
						method: "process_salary",
						doc: frm.doc,
						args: {"process_type": process_type, "name": rec.name},
						callback: function(r2, rt2){
							body_log = r2.message+body_log
							cur_frm.ss_html.innerHTML = head_log+body_log
						},
						freeze: true,
					});
				});
			} else {
				body_log = '<div style="color:#fa3635;">No employee for the above selected criteria OR salary slip(s) already '+msg_other+'</div>';
				msgprint(body_log);
				cur_frm.ss_html.innerHTML = head_log+body_log;
			}
		},
		freeze: true,
		freeze_message: msg,
	});
	cur_frm.ss_html.innerHTML += '</table></div>';
}
