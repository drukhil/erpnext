// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("cost_center", "branch", "branch");

frappe.provide("erpnext.stock");
frappe.ui.form.on('Material Return', {
	refresh: function (frm) {
		if (frm.doc.docstatus == 1) {
			cur_frm.add_custom_button(__("Stock Ledger"), function () {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company
				};
				frappe.set_route("query-report", "Stock Ledger Report");
			}, __("View"));

			cur_frm.add_custom_button(__('Accounting Ledger'), function () {
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

	// Added by Karma - Only this one
	// start
	setup: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;	
		frm.get_field('items').grid.editable_fields = [
			{fieldname: 'item_code', columns: 2},
			{fieldname: 'warehouse', columns: 2},
			{fieldname: 'qty', columns: 2},
			{fieldname: 'valuation_rate', columns: 2},
			{fieldname: 'expense_account', columns:2},			
			{fieldname: 'cost_center', columns: 2},
		];
	}
	// end
});

frappe.ui.form.on("Material Return Item", {
	item_code: function (frm, cdt, cdn) {
		get_details(frm, cdt, cdn);
	},
	warehouse: function (frm, cdt, cdn) {
		get_details(frm, cdt, cdn);
	},
	qty: function (frm, cdt, cdn) {
		var i = locals[cdt][cdn];
		if (i.valuation_rate)
			frappe.model.set_value(cdt, cdn, "amount", flt(i.valuation_rate) * flt(i.qty));
	},
	valuation_rate: function (frm, cdt, cdn) {
		var i = locals[cdt][cdn];
		if (i.qty)
			frappe.model.set_value(cdt, cdn, "amount", flt(i.valuation_rate) * flt(i.qty));
	}
});

function get_details(frm, cdt, cdn) {
	var d = frappe.model.get_doc(cdt, cdn);
	if (d.item_code && d.warehouse) {
		frappe.call({
			method: "erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_stock_balance_for",
			args: {
				item_code: d.item_code,
				warehouse: d.warehouse,
				posting_date: frm.doc.posting_date,
				posting_time: frm.doc.posting_time
			},
			callback: function (r) {
				frappe.model.set_value(cdt, cdn, "valuation_rate", r.message.rate);
				frappe.model.set_value(cdt, cdn, "basic_rate", r.message.rate);
			}
		});
	}
}