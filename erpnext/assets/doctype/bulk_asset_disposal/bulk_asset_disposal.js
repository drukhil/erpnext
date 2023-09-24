// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("asset", "item_code", "item_code");
cur_frm.add_fetch("asset", "branch", "branch");
// cur_frm.add_fetch("item_code", "item_name", "item_name");

frappe.ui.form.on('Bulk Asset Disposal', {
	setup: function(frm) {
		frm.get_docfield("item").allow_bulk_edit = 1;			
		
	},

	onload: function (frm) {
		frm.set_query("asset", "item", (doc) => {
			return {
				filters: {
					asset_category:doc.asset_category,
					status: ["not in", ["Draft","Sold","Scrapped","Submitted","Cancelled"]],
				}
			}
		})
	},
	refresh: function(frm) {
		if ((frm.doc.docstatus == 1 && frm.doc.scrap == "Sale Asset") && frm.doc.sales_invoice == null) {
			cur_frm.add_custom_button(__("Make Sales Invoice"),
				function () {
					frm.events.make_sales_invoice(frm);
				}
			).addClass("btn-primary custom-create custom-create-css")
		}
	},

	scrap: function (frm) {
		// frm.doc.scrap_date = Date.now();
		// frm.refresh_fields()
		frm.set_df_property('customer', 'reqd', frm.doc.scrap=='Sale Asset'? 1:0)
	},

	make_sales_invoice: function (frm) {
		frappe.call({
			method: "erpnext.assets.doctype.bulk_asset_disposal.bulk_asset_disposal.sale_asset",
			args: {
				branch: frm.doc.branch,
				name: frm.doc.name,
				scrap_date: frm.doc.scrap_date,
				customer: frm.doc.customer
			},
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	on_submit: function(frm) {
		if(frm.doc.scrap == 'Scrap Asset'){
			frappe.set_route("List", "Journal Entry");
		}
	}
});

frappe.ui.form.on("Bulk Asset Disposal Item", {
	item_code: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(!row.item_code) return
		// console.log(row.item_code)
		frappe.call({
			method: 'frappe.client.get_value',
			args: {
				doctype: 'Item',
				filters: {
					'name': row.item_code
				},
				fieldname: ['item_name']
			},
			callback: function(r){
				if(r.message){
					// console.log(r.message);
					frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
					frm.refresh_fields();
				}
			}
		});
	}
});

frappe.form.link_formatters['Item'] = function(value, doc) {
	return value
}