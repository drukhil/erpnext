// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("branch", "cost_center", "cost_center")
cur_frm.add_fetch("marking_list", "cable_line", "cable_line")

frappe.ui.form.on('Royalty Payment', {
	onload: function(frm) {
                if (!frm.doc.posting_date) {
                        frm.set_value("posting_date", get_today());
                }
	},

	refresh: function(frm) {

	},
    production_type: function(frm){
        cur_frm.set_df_property("range_name",cur_frm.doc.production_type == "Planned");
    },	
	get_royalty_details: function(frm) {
		return frappe.call({
			method: "get_royalty_details",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("planned_items");
				frm.refresh_field("adhoc_temp_items");
				frm.refresh_field("adhoc_items");
				frm.refresh_fields();
			},
			freeze: true,
			freeze_message: "Loading Royalty Details..... Please Wait"
		});
    },
    "discount_amount": function(frm) {
        if(frm.doc.discount_amount > frm.doc.total_royalty){
					frappe.throw("Discount amount cannot be greater than the total royalty.");
        }
        else{
            cur_frm.set_value("net_royalty",frm.doc.total_royalty-frm.doc.discount_amount);
        }

    },
    "add_amount": function(frm) {
       
        cur_frm.set_value("net_royalty",frm.doc.total_royalty+frm.doc.add_amount);
        

    },
    // "less_cft": function(frm) {
    //     if(frm.doc.less_cft > frm.doc.total_cft){
	// 				frappe.throw("Volume to be subtracted cannot be greater than the total volume.")
    //     }
    //     else{
    //         cur_frm.set_value("net_cft",frm.doc.total_cft-frm.doc.less_cft);
    //     }

    // }
    "less_qty": function(frm) {
        if(frm.doc.less_qty > frm.doc.total_qty){
					frappe.throw("Quantity to be subtracted cannot be greater than the total quantity.")
        }
        else{
            cur_frm.set_value("net_qty",frm.doc.total_qty-frm.doc.less_qty);
        }

    }
});

frappe.ui.form.on("Royalty Payment", "refresh", function(frm) {
    cur_frm.set_query("marking_list", function() {
        return {
            "filters": {
                "branch": frm.doc.branch,
                "fmu": frm.doc.location,
		"docstatus": 1
            }
        };
	
    });

    cur_frm.set_query("location", function() {
        return {
            "filters": {
                "branch": frm.doc.branch,
		"is_disabled": 0
            }
        };
    });

    cur_frm.set_query("range_name", function () {
        return {
		    "query": "erpnext.controllers.queries.filter_branch_rng",
            "filters": {
                "branch": frm.doc.branch,
                "is_disabled": 0
            }
        };
    });
    cur_frm.set_query("adhoc_production", function() {
        return {
            "filters": {
                "branch": frm.doc.branch,
                // "location": frm.doc.location,
		// "range_name": frm.doc.range_name,
		"is_disabled": 0
            }
        };
    });
})
