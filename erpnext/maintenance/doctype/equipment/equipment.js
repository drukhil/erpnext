// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("asset_code", "branch", "branch")

frappe.ui.form.on('Equipment', {
//	onload: function(frm) {
	//	cur_frm.set_df_property("asset_code", "reqd", frm.doc.not_cdcl ? 0 : 1) 
	//	cur_frm.set_df_property("asset_code", "reqd", frm.doc.equipment_type == "NA" ? 0 : 1) 
//	},
	refresh: function(frm) {
		cur_frm.set_df_property("engine_number", "read_only", frm.doc.engine_number ? 1 : 0)
		cur_frm.set_df_property("asset_code", "read_only", frm.doc.asset_code ? 1 : 0)
		cur_frm.set_df_property("chassis_number", "read_only", frm.doc.chassis_number ? 1 : 0)
		cur_frm.set_df_property("hsd_type", "read_only", frm.doc.hsd_type ? 1 : 0)
		cur_frm.set_df_property("equipment_category", "read_only", frm.doc.equipment_category ? 1 : 0)
		cur_frm.set_df_property("branch", "read_only", frm.doc.asset_code ? 1 : 0)
		if(!frm.doc.__islocal && in_list(user_roles, "Asset User")) {
            		cur_frm.set_df_property("asset_code", "read_only", 0)
           		cur_frm.set_df_property("fuelbook", "read_only", 1)
			frm.set_df_property("branch", "read_only", frm.doc.not_cdcl ? 0 : 1)
			frm.set_df_property("is_disabled", "read_only", 1)	
			var df = frappe.meta.get_docfield("Equipment Operator", "operator", cur_frm.doc.name);
			df.read_only = 1;
			frappe.meta.get_docfield("Equipment Operator", "start_date", cur_frm.doc.name).read_only = 1;
                        frappe.meta.get_docfield("Equipment Operator", "end_date", cur_frm.doc.name).read_only = 1;
                }
		if(!frm.doc.__islocal && in_list(user_roles, "Mechanical Master")) {
		    	frm.set_df_property("operator", "read_only", 1)
			frm.set_df_property("branch", "read_only", 1)
			frm.set_df_property("is_disabled", "read_only", 1)
		    	cur_frm.set_df_property("fuelbook", "read_only", 0)
		    	cur_frm.set_df_property("hsd_type", "read_only", 0)
			frappe.meta.get_docfield("Equipment Operator", "operator", cur_frm.doc.name).read_only = 0;
                	frappe.meta.get_docfield("Equipment Operator", "start_date", cur_frm.doc.name).read_only = 1;
   			frappe.meta.get_docfield("Equipment Operator", "end_date", cur_frm.doc.name).read_only = 1;
                }
		if(!frm.doc.__islocal && in_list(user_roles, "Fleet User")) {
			frm.set_df_property("branch", "read_only", 1)
			frm.set_df_property("is_disabled", "read_only", 1)
                        frm.set_df_property("fuelbook", "read_only", 1)
                        frm.set_df_property("is_disabled", "read_only", 1)
                }
		if(!frm.doc.__islocal && in_list(user_roles, "Asset Manager")) {
			cur_frm.set_df_property("asset_code", "read_only", 0)
                        cur_frm.set_df_property("fuelbook", "read_only", 0)
			frm.set_df_property("branch", "read_only", frm.doc.not_cdcl ? 0 : 1)
                        frm.set_df_property("is_disabled", "read_only", 0)
                        var df = frappe.meta.get_docfield("Equipment Operator", "operator", cur_frm.doc.name);
                        df.read_only = 1;
                }
		if(!frm.doc.__islocal && in_list(user_roles, "Administrator")) {
			frappe.meta.get_docfield("Equipment Operator", "operator", cur_frm.doc.name).read_only = 0;
                	frappe.meta.get_docfield("Equipment Operator", "start_date", cur_frm.doc.name).read_only = 0;
   			frappe.meta.get_docfield("Equipment Operator", "end_date", cur_frm.doc.name).read_only = 0;
			frm.set_df_property("branch", "read_only", frm.doc.not_cdcl ? 0 : 1)
			
		}
	},
	validate: function(frm) {
		if (frm.doc.operators) {
			frm.doc.operators.forEach(function(d) { 
				frm.set_value("current_operator", d.operator)
			})
			frm.refresh_field("current_operator")
		}
	},
	not_cdcl: function(frm) {
		cur_frm.toggle_reqd("asset_code", frm.doc.not_cdcl == 0)
		cur_frm.toggle_reqd("owned_by", frm.doc.not_cdcl == 1) 
	},

	/*branch: function(frm){
                if(!this.frm.doc.__islocal){
                        cur_frm.set_value("date_of_transfer",frappe.datetime.nowdate());
                        refresh_many(["date_of_transfer"]);
                        validate_prev_doc(this.frm,__("Please select date of transfer to new cost center"));
                }
        },
	*/
	//equipment_type: function(frm) {
	//	cur_frm.toggle_reqd("asset_code", frm.doc.equipment_type != "Fabrication Product")
//	}
});

frappe.ui.form.on("Equipment", "refresh", function(frm) {
    cur_frm.set_query("equipment_model", function() {
        return {
            "filters": {
		"equipment_type": frm.doc.equipment_type
            }
        };
    });
    cur_frm.set_query("equipment_type", function() {
        return {
            "filters": {
		"equipment_category": frm.doc.equipment_category
            }
        };
    });
    cur_frm.set_query("branch", function() {
	return {
		"filters": {
			"is_disabled": 0
		}
	}
    });
    cur_frm.set_query("fuelbook", function() {
	return {
		"filters": {
			"is_disabled": 0,
			"branch": frm.doc.branch
		}
	}
    });
    cur_frm.set_query("hsd_type", function() {
        return {
                "filters": {
                        "is_hsd_item": 1
                }
        }
    });
})

cur_frm.fields_dict['operators'].grid.get_field('operator').get_query = function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.employee_type == "Employee") {
		return {
			filters: [
			['Employee', 'branch', '=', frm.branch],
			['Employee', 'status', '=', 'Active']
			]
		}
	}
	else if(d.employee_type == 'Muster Roll Employee') {
		return {
			filters: [
				['Muster Roll Employee', 'branch', '=', frm.branch],
				['Muster Roll Employee', 'status', '=', 'Active']
			]
		}
	}
	else if(d.employee_type == 'Operator') {
		return {
			filters: [
				['Operator', 'branch', '=', frm.branch],
				['Operator', 'status', '=', 'Active']
			]
		}
	}	
}

frappe.ui.form.on('Equipment History', {
        before_equipment_history_remove: function(frm, cdt, cdn) {
                doc = locals[cdt][cdn]
                if(!doc.__islocal) {
                        frappe.throw("Cannot delete saved Items")
                }
        }

});



function validate_prev_doc(frm, title){
        return frappe.call({
                                method: "erpnext.custom_utils.get_prev_doc_eq",
                                args: {doctype: frm.doctype, docname: frm.docname, col_list: "cost_center,branch"},
                                callback: function(r) {
                                        if(frm.doc.cost_center && (frm.doc.cost_center !== r.message.cost_center)){
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
