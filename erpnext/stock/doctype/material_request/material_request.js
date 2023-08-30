// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
/*
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
2.0		          SHIV		     					26/11/2017         * "PR Type/material_request_type" should only be 
																			allowed to change by "Stock User"
																			as recommened by Payma, CDCL
--------------------------------------------------------------------------------------------------------------------------                                                                          
*/

{% include 'erpnext/buying/doctype/purchase_common/purchase_common.js' %};

cur_frm.add_fetch("item_code", "stock_uom", "uom")

frappe.ui.form.on('Material Request', {
	material_request_type: function(frm) {
		if(frm.doc.material_request_type == "Purchase") {
			cur_frm.set_value("purchase_change_date", get_today())
		}
		else {
			cur_frm.set_value("purchase_change_date", "")
		}
	},
	setup: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;	
		frm.get_field('items').grid.editable_fields = [
			{fieldname: 'item_code', columns: 2},
			{fieldname: 'item_name', columns: 2},
			{fieldname: 'uom', columns:2},
			{fieldname: 'qty', columns: 2},
			{fieldname: 'warehouse', columns: 2},
			{fieldname: 'schedule_date', columns: 2},
		];
	},
	/*"items_on_form_rendered": function(frm, grid_row, cdt, cdn) {
		var row = cur_frm.open_grid_row();
		if(!row.grid_form.fields_dict.cost_center_w.value) {
			row.grid_form.fields_dict.cost_center_w.set_value(frm.doc.temp_cc)
                	row.grid_form.fields_dict.cost_center_w.refresh()
		}
		if(!row.grid_form.fields_dict.warehouse.value) {
			row.grid_form.fields_dict.warehouse.set_value(frm.doc.temp_wh)
                	row.grid_form.fields_dict.warehouse.refresh()
		}
	}, */
	title1: function(frm) {
                        if(frm.doc.title1 == 'Stock Request'){
                                frm.set_value("material_request_type", "Purchase");
                        }
                        else if (frm.doc.title1 = 'Material Request') {
                                frm.set_value("material_request_type", "Material Issue");
                        }
                        else
                                {
                                frm.set_value("material_request_type", frm.doc.material_request_type);
                                }

                },


	onload: function(frm) {
		if(!frm.doc.creation_date) {
			frm.set_value("creation_date", get_today())
		}
		// formatter for material request item
		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.qty<=doc.ordered_qty) ? "green" : "orange" })

		frappe.form.link_formatters['Item'] = function(value, doc) {
			console.log('inside link_formatters');
			
			return value + ': ' + doc.item_name;
		}
		
		
		/*
		if(frm.doc.__islocal) {
			cur_frm.set_value("material_request_type", "Material Issue")
			frappe.call({
				method: "erpnext.stock.doctype.material_request.material_request.get_cc_warehouse",
				args: {"user": frappe.session.user},
				callback(r) {
					cur_frm.set_value("temp_cc", r.message[0]);		
					cur_frm.set_value("temp_wh", r.message[1]);		
					cur_frm.set_value("approver", r.message[2]);		
				}
			})
		}
		*/
		
		if(frm.doc.__islocal) {
			frappe.call({
					method: "erpnext.custom_utils.get_user_info",
					args: {"user": frappe.session.user},
					callback(r) {
							cur_frm.set_value("temp_cc", r.message.cost_center);
							cur_frm.set_value("temp_wh", r.message.warehouse);
							cur_frm.set_value("approver", r.message.approver);
							cur_frm.set_value("branch", r.message.branch);
					}
			});
        }
	},
	refresh: function(frm){
		// Ver2.0, Following condition is changed by SHIV on 26/11/2017
		//if(in_list(user_roles, "Stock User") || in_list(user_roles, "Purchase User")) {		
		if(in_list(user_roles, "Stock User")) {
			frm.set_df_property("material_request_type", "read_only", 0)
		}
	}
});

frappe.ui.form.on("Material Request Item", {
	"items_add": function(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "cost_center_w", frm.doc.temp_cc)
		frappe.model.set_value(cdt, cdn, "warehouse", frm.doc.temp_wh)
		frappe.model.set_value(cdt, cdn, "schedule_date", frappe.datetime.add_days(frm.doc.creation_date, 30))
	}, 
	"qty": function(frm, doctype, name) {
			var d = locals[doctype][name];
			if (flt(d.qty) < flt(d.min_order_qty)) {
				alert(__("Warning: Material Requested Qty is less than Minimum Order Qty"));
			}
		},
	"issued_quantity": function(frm, doctype, name) {
		var d = locals[doctype][name];
		if(d.qty < d.issued_quantity) {
			frappe.model.set_value(doctype, name, "issued_quantity", "")
			frappe.model.set_value(doctype, name, "ordered_qty", "")
			msgprint("Issued Quantity cannot be greater than actual quantity")
		}
		else {	
			frappe.model.set_value(doctype, name, "ordered_qty", d.issued_quantity)
		}
	}
},);

erpnext.buying.MaterialRequestController = erpnext.buying.BuyingController.extend({
	onload: function(doc) {
		this._super();
		this.frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query"
			}
		});
		
		/* Shiv, 25/12/2017 tried here not working
		frappe.form.link_formatters['Item'] = function(value, doc) {
			console.log('inside link_formatters');
			
			return value + ': ' + doc.item_name;
		}
		*/
	},

	refresh: function(doc) {
		var me = this;
		this._super();
		/*
		if(doc.docstatus==0) {
			cur_frm.add_custom_button(__("Get Items from BOM"),
				cur_frm.cscript.get_items_from_bom, "icon-sitemap", "btn-default");
		}
		*/
		if(doc.docstatus == 1 && doc.status != 'Stopped') {
			if(flt(doc.per_ordered, 2) < 100) {
				// make
				if(doc.material_request_type === "Material Transfer" && doc.status === "Submitted")
					cur_frm.add_custom_button(__("Transfer Material"),
					this.make_stock_entry, __("Make"));

				if(doc.material_request_type === "Material Issue" && doc.status === "Submitted")
					cur_frm.add_custom_button(__("Issue Material"),
					this.make_stock_entry, __("Make"));

				if(doc.material_request_type === "Purchase")
					cur_frm.add_custom_button(__('Purchase Order'),
						this.make_purchase_order, __("Make"));

				if(doc.material_request_type === "Purchase")
					cur_frm.add_custom_button(__("Request for Quotation"),
						this.make_request_for_quotation, __("Make"));

				if(doc.material_request_type === "Purchase")
					cur_frm.add_custom_button(__("Supplier Quotation"),
					this.make_supplier_quotation, __("Make"));

				if(doc.material_request_type === "Manufacture" && doc.status === "Submitted")
					cur_frm.add_custom_button(__("Production Order"),
					this.raise_production_orders, __("Make"));

				cur_frm.page.set_inner_btn_group_as_primary(__("Make"));

				// stop
				cur_frm.add_custom_button(__('Stop'),
					cur_frm.cscript['Stop Material Request']);

			}
		}
		/*
		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(__('Sales Order'),
				function() {
					erpnext.utils.map_current_doc({
						method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
						source_doctype: "Sales Order",
						get_query_filters: {
							docstatus: 1,
							status: ["!=", "Closed"],
							per_delivered: ["<", 99.99],
							company: cur_frm.doc.company
						}
					})
				}, __("Get items from"));
		}
		*/
		if(doc.docstatus == 1 && doc.status == 'Stopped')
			cur_frm.add_custom_button(__('Re-open'),
				cur_frm.cscript['Unstop Material Request']);

	},

	schedule_date: function(doc, cdt, cdn) {
		var val = locals[cdt][cdn].schedule_date;
		if(val) {
			$.each((doc.items || []), function(i, d) {
				if(!d.schedule_date) {
					d.schedule_date = val;
				}
			});
			refresh_field("items");
		}
	},

	get_items_from_bom: function() {
		var d = new frappe.ui.Dialog({
			title: __("Get Items from BOM"),
			fields: [
				{"fieldname":"bom", "fieldtype":"Link", "label":__("BOM"),
					options:"BOM", reqd: 1, get_query: function(){
						return {filters: { docstatus:1 }}
					}},
				{"fieldname":"warehouse", "fieldtype":"Link", "label":__("Warehouse"),
					options:"Warehouse", reqd: 1, label:"For Warehouse"},
				{"fieldname":"fetch_exploded", "fieldtype":"Check",
					"label":__("Fetch exploded BOM (including sub-assemblies)"), "default":1},
				{fieldname:"fetch", "label":__("Get Items from BOM"), "fieldtype":"Button"}
			]
		});
		d.get_input("fetch").on("click", function() {
			var values = d.get_values();
			if(!values) return;
			values["company"] = cur_frm.doc.company;
			frappe.call({
				method: "erpnext.manufacturing.doctype.bom.bom.get_bom_items",
				args: values,
				callback: function(r) {
					if(!r.message) {
						frappe.throw(__("BOM does not contain any stock item"))
					} else {
						$.each(r.message, function(i, item) {
							var d = frappe.model.add_child(cur_frm.doc, "Material Request Item", "items");
							d.item_code = item.item_code;
							d.description = item.description;
							d.warehouse = values.warehouse;
							d.uom = item.stock_uom;
							d.qty = item.qty;
						});
					}
					d.hide();
					refresh_field("items");
				}
			});
		});
		d.show();
	},

	tc_name: function() {
		this.get_terms();
	},

	validate_company_and_party: function(party_field) {
		return true;
	},

	calculate_taxes_and_totals: function() {
		return;
	},

	make_purchase_order: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order",
			frm: cur_frm,
			run_link_triggers: true
		});
	},

	make_request_for_quotation: function(){
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_request_for_quotation",
			frm: cur_frm,
			run_link_triggers: true
		});
	},

	make_supplier_quotation: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_supplier_quotation",
			frm: cur_frm
		});
	},

	make_stock_entry: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_stock_entry",
			frm: cur_frm
		});
	},

	raise_production_orders: function() {
		frappe.call({
			method:"erpnext.stock.doctype.material_request.material_request.raise_production_orders",
			args: {
				"material_request": cur_frm.doc.name
			}
		});
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.MaterialRequestController({frm: cur_frm}));

cur_frm.cscript['Stop Material Request'] = function() {
	var doc = cur_frm.doc;
	$c('runserverobj', args={'method':'update_status', 'arg': 'Stopped', 'docs': doc}, function(r,rt) {
		cur_frm.refresh();
	});
};

cur_frm.cscript['Unstop Material Request'] = function(){
	var doc = cur_frm.doc;
	$c('runserverobj', args={'method':'update_status', 'arg': 'Submitted','docs': doc}, function(r,rt) {
		cur_frm.refresh();
	});
};


//custom Scripts
frappe.ui.form.on("Material Request Item", "item_code", function(frm, cdt, cdn) {
   var item = frappe.get_doc(cdt, cdn);
   frappe.call({
        method: "erpnext.buying.doctype.purchase_order.purchase_order.get_budget_account",
        args: {
            "item_code": item.item_code
        },
        callback: function(r)  {
             if(r.message) {
                   frappe.model.set_value(cdt, cdn, "budget_account", r.message)
             }
        }
   })
})

//cost Center
cur_frm.fields_dict.items.grid.get_field("cost_center").get_query = function(doc) {
	return {
		filters: {
			'company': doc.company,
			"is_group": 0,
			"is_disabled": 0,
		}
	}
} 

/*
// Shiv, 25/12/2017 test not working
cur_frm.cscript.onload = function(frm){
	console.log('test from cscript');

	frappe.form.link_formatters['Item'] = function(value, doc) {
		console.log('inside link_formatters');
		
		return value + ': ' + doc.items.item_name;
	}
}
*/
