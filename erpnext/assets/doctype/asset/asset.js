// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.asset");

frappe.ui.form.on('Asset', {
	onload: function(frm) {
		frm.set_query("item_code", function() {
			return {
				"filters": {
					"disabled": 0,
					"is_fixed_asset": 1,
					"is_stock_item": 0
				}
			};
		});

		frm.set_query("warehouse", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"is_group": 0
				}
			};
		});

		frm.set_query("asset_sub_category", function() {
			return {
				"filters": {
					"item_group": "Fixed Asset",
				}
			};
		});
	},

	refresh: function(frm) {
		frappe.ui.form.trigger("Asset", "is_existing_asset");
		frm.toggle_display("next_depreciation_date", frm.doc.docstatus < 1);

		if (frm.doc.docstatus==1) {
			if (frm.doc.status=='Submitted' && !frm.doc.is_existing_asset && !frm.doc.purchase_invoice) {
				frm.add_custom_button("Make Purchase Invoice", function() {
					erpnext.asset.make_purchase_invoice(frm);
				});
			}
			if(in_list(user_roles, "Asset User") || in_list(user_roles, "Asset Manager")) {
				if (in_list(["Submitted", "Partially Depreciated", "Fully Depreciated"], frm.doc.status)) {
					/*frm.add_custom_button("Transfer Asset", function() {
						erpnext.asset.transfer_asset(frm);
					}); */

					frm.add_custom_button("Scrap Asset", function() {
						erpnext.asset.scrap_asset(frm);
					});

					frm.add_custom_button("Sale Asset", function() {
						erpnext.asset.make_sales_invoice(frm);
					});

				} else if (frm.doc.status=='Scrapped') {
					/*
					frm.add_custom_button("Restore Asset", function() {
						erpnext.asset.restore_asset(frm);
					});
					*/
				}
			}
			frm.trigger("show_graph");
		}
		if(frm.doc.docstatus===1){
			frm.add_custom_button(__('Journal Entry'), function(){
				frappe.route_options = {
					"Journal Entry Account.reference_type": me.frm.doc.doctype,
					"Journal Entry Account.reference_name": me.frm.doc.name,
				};
				frappe.set_route("List", "Journal Entry");
			}, __("View"));
		}
	},

	show_graph: function(frm) {
		var x_intervals = ["x", frm.doc.purchase_date];
		var asset_values = ["Asset Value", frm.doc.gross_purchase_amount];
		var last_depreciation_date = frm.doc.purchase_date;

		if(frm.doc.opening_accumulated_depreciation) {
			last_depreciation_date = frappe.datetime.add_months(frm.doc.next_depreciation_date,
				-1*frm.doc.frequency_of_depreciation);

			x_intervals.push(last_depreciation_date);
			asset_values.push(flt(frm.doc.gross_purchase_amount) -
				flt(frm.doc.opening_accumulated_depreciation));
		}

		$.each(frm.doc.schedules || [], function(i, v) {
			x_intervals.push(v.schedule_date);
			asset_value = flt(frm.doc.gross_purchase_amount) - flt(v.accumulated_depreciation_amount);
			if(v.journal_entry) {
				last_depreciation_date = v.schedule_date;
				asset_values.push(asset_value)
			} else {
				if (in_list(["Scrapped", "Sold"], frm.doc.status)) {
	 				asset_values.push(null)
				} else {
					asset_values.push(asset_value)
				}
			}
		})

		if(in_list(["Scrapped", "Sold"], frm.doc.status)) {
			x_intervals.push(frm.doc.disposal_date);
			asset_values.push(0);
			last_depreciation_date = frm.doc.disposal_date;
		}

		frm.dashboard.setup_chart({
			data: {
				x: 'x',
				columns: [x_intervals, asset_values],
				regions: {
					'Asset Value': [{'start': last_depreciation_date, 'style':'dashed'}]
				}
			},
			legend: {
				show: false
			},
			axis: {
				x: {
					type: 'timeseries',
					tick: {
						format: "%d-%m-%Y"
					}
				},
				y: {
					min: 0,
					padding: {bottom: 10}
				}
			}
		});
	},

	item_code: function(frm) {
		if(frm.doc.item_code) {
			frappe.call({
				method: "erpnext.assets.doctype.asset.asset.get_item_details",
				args: {
					item_code: frm.doc.item_code
				},
				callback: function(r, rt) {
					if(r.message) {
						$.each(r.message, function(field, value) {
							frm.set_value(field, value);
						})
					}
				}
			})
		}
	},

	is_existing_asset: function(frm) {
		frm.toggle_enable("supplier", frm.doc.is_existing_asset);
		frm.toggle_reqd("next_depreciation_date", !frm.doc.is_existing_asset);
	},
	
	asset_status: function(frm) {
		if(frm.doc.asset_status == "Marked for Auction") {
			cur_frm.set_value("marked_on", get_today())
		}
		else {
			cur_frm.set_value("marked_on", "")
		}
	}
});

frappe.ui.form.on('Depreciation Schedule', {
	make_depreciation_entry: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (!row.journal_entry) {
			frappe.call({
				method: "erpnext.assets.doctype.asset.depreciation.make_depreciation_entry",
				args: {
					"asset_name": frm.doc.name,
					"date": row.schedule_date
				},
				callback: function(r) {
					frappe.model.sync(r.message);
					frm.refresh();
				}
			})
		}
	}
})

erpnext.asset.make_purchase_invoice = function(frm) {
	frappe.call({
		args: {
			"asset": frm.doc.name,
			"item_code": frm.doc.item_code,
			"gross_purchase_amount": frm.doc.gross_purchase_amount,
			"company": frm.doc.company,
			"posting_date": frm.doc.purchase_date,
			"branch": frm.doc.branch
		},
		method: "erpnext.assets.doctype.asset.asset.make_purchase_invoice",
		callback: function(r) {
			var doclist = frappe.model.sync(r.message);
			frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	})
}

erpnext.asset.make_sales_invoice = function(frm) {
	frappe.call({
		args: {
			"asset": frm.doc.name,
			"item_code": frm.doc.item_code,
			"company": frm.doc.company,
			"branch": frm.doc.branch
		},
		method: "erpnext.assets.doctype.asset.asset.make_sales_invoice",
		callback: function(r) {
			var doclist = frappe.model.sync(r.message);
			frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	})
}

erpnext.asset.restore_asset = function(frm) {
	frappe.confirm(__("Do you really want to restore this scrapped asset?"), function () {
		frappe.call({
			args: {
				"asset_name": frm.doc.name
			},
			method: "erpnext.assets.doctype.asset.depreciation.restore_asset",
			callback: function(r) {
				cur_frm.reload_doc();
			}
		})
	})
}

erpnext.asset.transfer_asset = function(frm) {
	var dialog = new frappe.ui.Dialog({
		title: __("Transfer Asset"),
		fields: [
			/*{
				"label": __("Target Warehouse"),
				"fieldname": "target_warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"get_query": function () {
					return {
						filters: [
                                                	["Warehouse", "company", "in", ["", cstr(frm.doc.company)]],
                                                	["Warehouse", "is_group", "=", 0]
                                        	]
					}
				},
			}, */
			{
				"label": __("Target Custodian"),
				"fieldname": "target_custodian",
				"fieldtype": "Link",
				"options": "Employee",
			},
			{
				"label": __("Date"),
				"fieldname": "transfer_date",
				"fieldtype": "Datetime",
				"reqd": 1,
				"default": frappe.datetime.now_datetime()
			}
		]
	});

	dialog.set_primary_action(__("Transfer"), function() {
		args = dialog.get_values();
		if(!args) return;
		dialog.hide();
		return frappe.call({
			type: "GET",
			method: "erpnext.assets.doctype.asset.asset.transfer_asset",
			args: {
				args: {
					"asset": frm.doc.name,
					"transaction_date": args.transfer_date,
					"source_warehouse": frm.doc.warehouse,
					"target_warehouse": args.target_warehouse,
		       			"source_custodian": frm.doc.issued_to,
		       			"target_custodian": args.target_custodian,
					"company": frm.doc.company
				}
			},
			freeze: true,
			callback: function(r) {
				cur_frm.reload_doc();
			}
		})
	});
	dialog.show();
}

erpnext.asset.scrap_asset = function(frm) {
	var dialog = new frappe.ui.Dialog({
		title: __("Scrap Asset"),
		fields: [
			{
				"label": __("Scrap Date"),
				"fieldname": "scrap_date",
				"fieldtype": "Date",
				"reqd": 1,
				"default": frappe.datetime.nowdate()
			}
		]
	});

	dialog.set_primary_action(__("Scrap"), function() {
		args = dialog.get_values();
		if(!args) return;
		dialog.hide();
		return frappe.call({
			method: "erpnext.assets.doctype.asset.depreciation.scrap_asset",
			args: {
				"asset_name": frm.doc.name,
		       		"scrap_date": args.scrap_date
			},
			callback: function(r) {
				cur_frm.reload_doc();
			}
		})
	});
	dialog.show();
}

//custom Scripts
//Set Asset Name from Item Code
cur_frm.add_fetch("item_code", "item_name", "asset_name");
cur_frm.add_fetch("issued_to", "cost_center", "cost_center");
cur_frm.add_fetch("issued_to", "branch", "branch");

//Set next depreciation date as the last day of the month
cur_frm.cscript.onload = function(doc) {

frappe.call({
    'method': 'erpnext.assets.doctype.asset.asset.get_next_depreciation_date',
    'args': {
        },
       callback: function(r){
           if (r.message) {
                 if(doc.next_depreciation_date) {}
                 else {
                      cur_frm.set_value("next_depreciation_date", r.message);
                      //cur_frm.set_df_property("next_depreciation_date", "hidden", true);
                 }
           }
       }
});

}

//Set Depreciation rate based on asset category
cur_frm.cscript.asset_category = function(doc) {

frappe.call({
    'method': 'frappe.client.get',
    'args': {
        'doctype': 'Asset Category',
        'filters': {
            'asset_category_name': doc.asset_category
          },
        'fields':['depreciation_percent']
        },
       callback: function(r){
           if (r.message) {
               cur_frm.set_value("asset_depreciation_percent", r.message.depreciation_percent);
frappe.call({
    'method': 'frappe.client.get',
    'args': {
        'doctype': 'Asset Category Account',
        'filters': {
            'parent': doc.asset_category
          },
        'fields':['fixed_asset_account', 'credit_account']
        },
       callback: function(r){
           if (r.message) {
               cur_frm.set_value("asset_account", r.message.fixed_asset_account);
               cur_frm.set_value("credit_account", r.message.credit_account);
           }
       }
});

           }
       }
});

};


// gross amount calculation
frappe.ui.form.on("Asset", "asset_rate", function(frm) {
    if (frm.doc.asset_quantity_) {
        cur_frm.set_value("gross_purchase_amount", ((frm.doc.asset_quantity_ * frm.doc.asset_rate) + frm.doc.additional_value))
    }
})

frappe.ui.form.on("Asset", "asset_quantity_", function(frm) {
    if (frm.doc.asset_rate) {
        cur_frm.set_value("gross_purchase_amount", frm.doc.asset_quantity_ * frm.doc.asset_rate)
    }
})
