// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("target_custodian", "user_id", "target_user_id")
cur_frm.add_fetch("target_custodian", "cost_center", "target_custodian_cost_center")

frappe.ui.form.on('Asset Movement', {
	refresh: function(frm) {
		if(frm.doc.docstatus == 1) {
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
	onload: function(frm) {
		frm.add_fetch("asset", "warehouse", "source_warehouse");
		frm.add_fetch("asset", "issued_to", "source_custodian");
		frm.add_fetch("asset", "employee_name", "source_custodian_name");
		frm.add_fetch("asset", "cost_center", "current_cost_center");
		frm.add_fetch("asset", "asset_name", "asset_name");
		
		frm.set_query("target_warehouse", function() {
			return {
				filters: [
                                         ["Warehouse", "company", "in", ["", cstr(frm.doc.company)]],
                                         ["Warehouse", "is_group", "=", 0]
                                        ]				
			}
		})
		frm.set_query("target_cost_center", function() {
			return {
				filters: [
                                         ["Cost Center", "is_disabled", "!=", 1],
                                         ["Cost Center", "is_group", "=", 0]
                                        ]				
			}
		})
	},
	source_custodian: function(frm) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Employee",
				fieldname: "employee_name",
				filters: {name: frm.doc.source_custodian},
			},
			callback: function(r) {
				if(r.message.employee_name) {
					cur_frm.set_value("source_custodian_name", r.message.employee_name)
				}
			}
		})
	}
});
