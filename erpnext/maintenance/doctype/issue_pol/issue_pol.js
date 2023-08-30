// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Issue POL', {
	onload: function(frm) {
		if(!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today())
		}
	},

	refresh: function(frm) {
		if(frm.doc.docstatus == 1) {
			cur_frm.add_custom_button(__("Stock Ledger"), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company
				};
				frappe.set_route("query-report", "Stock Ledger Report");
			}, __("View"));

			cur_frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
		}
	},

	"items_on_form_rendered": function(frm, grid_row, cdt, cdn) {
		var row = cur_frm.open_grid_row();
		/*if(!row.grid_form.fields_dict.pol_type.value) {
			//row.grid_form.fields_dict.pol_type.set_value(frm.doc.pol_type)
                	row.grid_form.fields_dict.pol_type.refresh()
		}*/
	},

	"branch": function(frm) {
		return frappe.call({
			method: "erpnext.custom_utils.get_cc_warehouse",
			args: {
				"branch": frm.doc.branch
			},
			callback: function(r) {
				cur_frm.set_value("cost_center", r.message.cc)
				cur_frm.set_value("warehouse", r.message.wh)
				cur_frm.refresh_fields()
			}
		})
	}
});

cur_frm.add_fetch("equipment", "equipment_number", "equipment_number")

frappe.ui.form.on("Issue POL", "refresh", function(frm) {
    	cur_frm.set_query("pol_type", function() {
		return {
		    "filters": {
			"disabled": 0,
			"is_pol_item": 1
		    }
		};
	    });
	
	/*cur_frm.set_query("tanker", function() {
		return {
			"query": "erpnext.maintenance.doctype.issue_pol.issue_pol.equipment_query",
			filters: {'branch': frm.doc.branch}
		}
	})
	*/
	cur_frm.set_query("warehouse", function() {
                return {
                        query: "erpnext.controllers.queries.filter_branch_wh",
                        filters: {'branch': frm.doc.branch}
                }
            });

        frm.fields_dict['items'].grid.get_field('equipment_warehouse').get_query = function(doc, cdt, cdn) {
                item = locals[cdt][cdn]
                return {
                        "query": "erpnext.controllers.queries.filter_branch_wh",
                        filters: {'branch': item.equipment_branch}
                }
        }

        frm.fields_dict['items'].grid.get_field('hiring_warehouse').get_query = function(doc, cdt, cdn) {
                item = locals[cdt][cdn]
                return {
                        "query": "erpnext.controllers.queries.filter_branch_wh",
                        filters: {'branch': item.hiring_branch}
                }
        }

	/*frm.fields_dict['items'].grid.get_field('equipment').get_query = function(doc, cdt, cdn) {
		doc = locals[cdt][cdn]
                if(frm.doc.purpose == "Transfer") {
                        return {
				"query": "erpnext.maintenance.doctype.issue_pol.issue_pol.equipment_query",
				filters: {'branch': '%'}
                        }
                }
                else {
                        return {
                                filters: {
                                        "is_disabled": 0,
					"equipment_type": ["not in", ['Skid Tank', 'Barrel']]
                                }
                        }
                }
	}*/
})

frappe.ui.form.on("POL Issue Report Item", "equipment", function(doc, cdt, cdn) {
	doc = locals[cdt][cdn]
	if(doc.equipment_branch) {
		return frappe.call({
			method: "erpnext.custom_utils.get_cc_warehouse",
			args: {
				"branch": doc.equipment_branch
			},
			callback: function(r) {
				frappe.model.set_value(cdt, cdn, "equipment_cost_center", r.message.cc)
				frappe.model.set_value(cdt, cdn, "equipment_warehouse", r.message.wh)
				cur_frm.refresh_fields()
			}
		})
	}
})

