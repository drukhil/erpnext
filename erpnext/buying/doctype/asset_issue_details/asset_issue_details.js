// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("item_code", "item_name", "item_name");
cur_frm.add_fetch("issued_to", "employee_name", "employee_name");
cur_frm.add_fetch("purchase_receipt", "posting_date", "purchase_date");
frappe.ui.form.on('Asset Issue Details', {
        onload: function(frm){
		frm.set_query('item_code', function(doc, cdt, cdn) {
			return {
				filters: {
					"is_fixed_asset": '1'
				}
			}
		});
	},
	refresh: function (frm) {
		frm.set_query('issued_to', function(doc, cdt, cdn) {
			return {
				filters: {
					"branch": frm.doc.branch,
					"status":"Active"
				}
			}
		});
		frm.set_query("purchase_receipt",function(doc) {
			return {
				query: "erpnext.buying.doctype.asset_issue_details.asset_issue_details.check_item_code",
				filters: {
					'item_code': frm.doc.item_code,
					'cost_center': frm.doc.cost_center
				}
			} 
		});
	},
	"purchase_receipt": function(frm){ 
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				parent: "Purchase Receipt",
				doctype: "Purchase Receipt Item",
				fieldname: ["valuation_rate","rate","warehouse","model_name","brand_name"],
				filters: {
					"parent": frm.doc.purchase_receipt,
					"item_code": frm.doc.item_code
				}
			},
			callback: function(r){
				if(r.message.valuation_rate){
					cur_frm.set_value("asset_rate", r.message.valuation_rate)
				}
				else if(r.message.rate){
					cur_frm.set_value("asset_rate", r.message.rate)
				}
				else{
					frappe.throw("Not working")
				}
				cur_frm.set_value("warehouse",r.message.warehouse);
				cur_frm.set_value("brand",r.message.brand_name);
				cur_frm.set_value("model",r.message.model_name);
			}
		});

	},
	"qty": function(frm){
                if(frm.doc.asset_rate){
                        frm.set_value("amount", frm.doc.qty * frm.doc.asset_rate);
                }
        },
	"asset_rate": function(frm){
			if(frm.doc.qty){
					frm.set_value("amount", frm.doc.qty * frm.doc.asset_rate);
			}
	}
});

cur_frm.fields_dict['item_code'].get_query = function(doc) {
        return {
               "filters": {
                       "item_group": "Fixed Asset"
                }
        }
}