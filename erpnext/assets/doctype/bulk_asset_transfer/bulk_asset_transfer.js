// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("project", "cost_center", "cost_center")
cur_frm.add_fetch("custodian", "employee_name", "custodian_name")
cur_frm.add_fetch("asset_code", "asset_name", "asset_name")
cur_frm.add_fetch("asset_code", "gross_purchase_amount", "gross_amount")

cur_frm.add_fetch("current_custodian", "employee_name", "c_custodian_name")

frappe.ui.form.on('Bulk Asset Transfer', {
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
	setup: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;
	},
	get_assets: function(frm) {
		return frappe.call({
			method: "get_assets",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("items");
				frm.refresh_fields();
			},
			freeze: true,
                        freeze_message: "Loading Asset Details..... Please Wait"
		});
	}
});

cur_frm.fields_dict['items'].grid.get_field('asset_code').get_query = function(frm, cdt, cdn) {
        if(frm.purpose == "Cost Center") {
                return {
                        filters: [
                        ['Asset', 'cost_center', '=', frm.cost_center],
                        ]
                }
        }
        else if(frm.purpose == "Custodian") {
                return {
                        filters: [
                        ['Asset', 'issued_to', '=', frm.current_custodian],
                        ]
                }
        }
	else {
		return {
			filters: [
				["Asset", 'cost_center', '=', "NOTFOUND"]
			]
		}
	}
}
