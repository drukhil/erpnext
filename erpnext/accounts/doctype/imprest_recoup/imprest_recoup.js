// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("branch","expense_bank_account","revenue_bank_account");
cur_frm.add_fetch("settlement_account","account_type","settlement_account_type");
cur_frm.add_fetch("cost_center", "warehouse", "warehouse"); 
frappe.ui.form.on('Imprest Recoup', {
	setup: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;		
		frm.get_field('items').grid.editable_fields = [
			{fieldname: 'transaction_date', columns: 1},
			{fieldname: 'particulars', columns: 2},
			{fieldname: 'quantity', columns: 1},
			{fieldname: 'rate', columns: 1},
			{fieldname: 'amount', columns: 2},
			{fieldname: 'budget_account', columns: 2},
			{fieldname: 'remarks', columns: 1}
		];
	},
	refresh: function(frm) {
		enable_disable(frm);
		
		if(frm.doc.docstatus===1){
			cur_frm.add_custom_button(__("Stock Ledger"), function() {
                                frappe.route_options = {
                                        voucher_no: frm.doc.name,
                                        from_date: frm.doc.posting_date,
                                        to_date: frm.doc.posting_date,
                                        company: frm.doc.company
                                };
                                frappe.set_route("query-report", "Stock Ledger Report");
                        }, __("View"));

			frm.add_custom_button(__('Accounting Ledger'), function(){
				frappe.route_options = {
					voucher_no: frm.doc.name,
					company: frm.doc.company,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
		}
	},
	onload: function(frm) {
		// Updating default information based on loggedin user
		if(frm.doc.__islocal) {
			if(!frm.doc.branch){
				frappe.call({
						method: "erpnext.custom_utils.get_user_info",
						args: {
							"user": frappe.session.user
						},
						callback(r) {
							if(r.message){
								cur_frm.set_value("cost_center", r.message.cost_center);
								cur_frm.set_value("branch", r.message.branch);
							}
						}
				});
			}
        }
		
		/*
		if (frm.doc.docstatus === 0 && frm.doc.workflow_state === "Recouped"){
			frm.set_value("workflow_state", "Waiting Recoupment");
			cur_frm.save();
		}
		*/
		
		/*
		if(!frm.doc.posting_date){
			cur_frm.set_value("posting_date", frappe.datetime.now_datetime());
		}
		*/
		
		frm.fields_dict['items'].grid.get_field('budget_account').get_query = function(){
			return{
				filters: {
					'is_group': 0
				}
			}
		};
	
		frm.fields_dict['items'].grid.get_field('cost_center').get_query = function(){
                        return{
                                filters: {
                                        // 'parent_cost_center': frm.doc.cost_center,
										'is_group' : 0
                                }
                        }
                };
	
		cur_frm.set_query("select_cheque_lot", function(){
			return {
				"filters": [
					["status", "!=", "Used"],
					["docstatus", "=", "1"],
					["branch", "=", frm.doc.branch]
				]
			}
		});
		
		cur_frm.set_query("party_type", function(){
			return {
				filters: {"name": ["in", ["Customer", "Supplier","Employee"]]}
			}
		});
	},
	branch: function(frm){
		// Update totals
		update_totals(frm);
		
		// Update Cost Center
		if(frm.doc.branch){
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Cost Center',
					filters: {
						'branch': frm.doc.branch,
						'is_group': 0
					},
					fieldname: ['name']
				},
				callback: function(r){
					if(r.message){
						cur_frm.set_value("cost_center", r.message.name);
						refresh_field('cost_center');
					}
				}
			});
			
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Branch Imprest Item',
					filters: {
						'parent': frm.doc.branch,
						'default': 1
					},
					fieldname: ['imprest_type']
				},
				callback: function(r){
					if(r.message){
						cur_frm.set_value("imprest_type", r.message.imprest_type);
					}
				}
			});
		}
	},
	imprest_type: function(frm){
		update_totals(frm);
	},
	select_cheque_lot: function(frm){
		if(frm.doc.select_cheque_lot){
			frappe.call({
				method: "erpnext.accounts.doctype.cheque_lot.cheque_lot.get_cheque_no_and_date",
				args: {
				'name': frm.doc.select_cheque_lot
				},
				callback: function(r){
				   if (r.message) {
					   cur_frm.set_value("cheque_no", r.message[0].reference_no);
					   cur_frm.set_value("cheque_date", r.message[1].reference_date);
				   }
				   }
			});
		}
	},
	final_settlement: function(frm){
		enable_disable(frm);
	},
	settlement_account: function(frm){
		enable_disable(frm);
	},
	settlement_account_type: function(frm){
		enable_disable(frm);
	},
	party_type: function(frm){
		enable_disable(frm);
	},
	party: function(frm){
		enable_disable(frm);
	}
});

frappe.ui.form.on('Imprest Recoup Item',{
	quantity: function(frm, cdt, cdn){
		calculate_amount(frm, cdt, cdn);
	},
	
	rate: function(frm, cdt, cdn){
		calculate_amount(frm, cdt, cdn);
	},
	
	amount: function(frm){
		update_totals(frm);
	},

	item: function(frm, cdt, cdn){
                var child = locals[cdt][cdn]
                //frm.doc.items.forEach(function(d) {
                        frm.add_fetch("item", "expense_account", "budget_account");
                        frm.add_fetch("item", "item_name", "particulars");
                //})
        },

	items_remove: function(frm){
		update_totals(frm);
	},
	maintain_stock_asset: function(frm, cdt, cdn){
		var df1 = frappe.meta.get_docfield("Imprest Recoup Item","budget_account", cur_frm.doc.name);
		var df2 = frappe.meta.get_docfield("Imprest Recoup Item", "cost_center", cur_frm.doc.name); 
		var child = locals[cdt][cdn]
		frm.doc.items.forEach(function(d) {
			if(d.maintain_stock_asset){
				df1.read_only = 0;
				df2.reqd = 0;
			}
			else {
				df1.read_only = 0;
				df2.reqd = 0;
			}
		})
	},
});

var calculate_amount = function(frm, cdt, cdn){
	var child  = locals[cdt][cdn];
	var amount = 0.0;
	
	amount = parseFloat(child.quantity || 0.0)*parseFloat(child.rate || 0.0);
	frappe.model.set_value(cdt, cdn, "amount", parseFloat(amount || 0.0));
}

var update_totals = function(frm){
	var det = frm.doc.items || [];
	var tot_opening_balance = 0.0, 
		tot_receipt_amount  = 0.0, 
		tot_purchase_amount = 0.0, 
		tot_closing_balance = 0.0;
		
	for(var i=0; i<det.length; i++){
			tot_purchase_amount += parseFloat(det[i].amount || 0.0);
	}
	
	cur_frm.set_value("opening_balance",tot_opening_balance);
	cur_frm.set_value("receipt_amount",tot_receipt_amount);
	cur_frm.set_value("purchase_amount",tot_purchase_amount);
	cur_frm.set_value("closing_balance",parseFloat(tot_opening_balance || 0.0)+parseFloat(tot_receipt_amount)-parseFloat(tot_purchase_amount));
	
	if(frm.doc.branch){
		frappe.call({
			method: "erpnext.accounts.doctype.imprest_receipt.imprest_receipt.get_opening_balance",
			args: {
				"branch": frm.doc.branch,
				"imprest_type": frm.doc.imprest_type,
				"docname": frm.doc.name
			},
			callback: function(r){
				if(r.message){
					cur_frm.set_value("opening_balance",parseFloat(r.message || 0.0));
					cur_frm.set_value("receipt_amount", parseFloat(tot_receipt_amount));
					cur_frm.set_value("closing_balance", parseFloat(r.message || 0.0)+parseFloat(tot_receipt_amount)-parseFloat(tot_purchase_amount));
				}
			}
		});
	}
}

/*
cur_frm.cscript.custom_before_submit = function(frm){
	console.log('before submit');
}
*/

function enable_disable(frm){
	var toggle_fields = ["final_settlement","settlement_account","party_type","party","revenue_bank_account","pay_to_recd_from", "use_cheque_lot","select_cheque_lot","cheque_no", "cheque_date"];
	var other_fields  = ["company","title","branch","imprest_type","remarks","notes"];
	
	toggle_fields.forEach(function(field_name){
		frm.set_df_property(field_name,"read_only",1);
	});
	
	if(frm.doc.workflow_state == 'Waiting Approval'){
		if(!in_list(user_roles, "Imprest Manager") && !in_list(user_roles, "Accounts User")){
			other_fields.forEach(function(field_name){
				frm.set_df_property(field_name,"read_only",1);
			});

			frm.set_df_property("items", "read_only", 1);			
			frm.disable_save();
		}
	}
	else if(frm.doc.workflow_state == 'Waiting Recoupment'){
		if(!in_list(user_roles, "Accounts User")){
			other_fields.forEach(function(field_name){
				frm.set_df_property(field_name,"read_only",1);
			});
			
			frm.set_df_property("items", "read_only", 1);
			frm.disable_save();
		}
		else {
			toggle_fields.forEach(function(field_name){
				frm.set_df_property(field_name,"read_only",0);
			});
			
			if(frm.doc.final_settlement){
				frm.toggle_reqd(["settlement_account"], 1);
				frm.toggle_display(["settlement_account","party_type", "party"], 1);
				frm.toggle_reqd(["revenue_bank_account","pay_to_recd_from", "cheque_no", "cheque_date"], 0);
			} else {
				frm.toggle_reqd(["settlement_account","party_type", "party"], 0);
				frm.toggle_display(["settlement_account","party_type", "party"], 0);
				frm.toggle_reqd(["revenue_bank_account","pay_to_recd_from", "cheque_no", "cheque_date"], 1);
			}
			
			frm.toggle_reqd(["party_type", "party"], 0);
			if(frm.doc.settlement_account_type && (frm.doc.settlement_account_type === "Payable" || frm.doc.settlement_account_type === "Receivable")){
				frm.toggle_reqd(["party_type", "party"], 1);
			}
		}
	}
	else {
		frm.enable_save();
	}
}

frappe.ui.form.on("Imprest Recoup","items_on_form_rendered", function(frm, grid_row, cdt, cdn){
	var grid_row = cur_frm.open_grid_row();
	if(frm.doc.workflow_state == 'Waiting Approval'){
		if(!in_list(user_roles, "Imprest Manager") && !in_list(user_roles, "Accounts User")){
			//Following works only when row is opened
			grid_row.grid_form.fields_dict.quantity.df.read_only = true;
			grid_row.grid_form.fields_dict.rate.df.read_only = true;
			grid_row.grid_form.fields_dict.quantity.refresh();
			grid_row.grid_form.fields_dict.rate.refresh();
		}
	}
	else if(frm.doc.workflow_state == 'Waiting Recoupment'){
		if(!in_list(user_roles, "Accounts User")){
			//Following works only when row is opened
			grid_row.grid_form.fields_dict.quantity.df.read_only = true;
			grid_row.grid_form.fields_dict.rate.df.read_only = true;
			//grid_row.grid_form.fields_dict.budget_account.df.read_only = true;
			grid_row.grid_form.fields_dict.quantity.refresh();
			grid_row.grid_form.fields_dict.rate.refresh();
			grid_row.grid_form.fields_dict.budget_account.refresh();
		}
	}
	
})
cur_frm.fields_dict['items'].grid.get_field('item').get_query = function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	
		return {
			filters: [
			['Item', 'is_stock_item', '=', 1],
			['Item', 'disabled', '=', 0],
			
			]
		}
	}
