// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

//var temp = document.querySelectorAll('[data-fieldname="invoice_quantity"]');
//var temp = $('[data-fieldname="invoice_quantity"]')
//console.log(temp);

frappe.ui.form.on('Project Invoice', {
	setup: function(frm){
		frm.get_field('project_invoice_boq').grid.editable_fields = [
			{fieldname: 'item', columns: 3},
			{fieldname: 'is_selected', columns: 1},
			{fieldname: 'uom', columns: 1},
			{fieldname: 'invoice_quantity', columns: 1},
			{fieldname: 'invoice_rate', columns: 2},
			{fieldname: 'invoice_amount', columns: 2}
		];			
		frm.get_field('project_invoice_mb').grid.editable_fields = [
			{fieldname: 'entry_name', columns: 2},
			{fieldname: 'entry_date', columns: 2},
			{fieldname: 'price_adjustment_amount', columns: 2},
			{fieldname: 'entry_amount', columns: 2},
			{fieldname: 'is_selected', columns: 1},
		];
	},

	onload: function(frm, cdt, cdn){
		toggle_child_tables(frm);
		if(frm.doc.project && frm.doc.__islocal){
			if(frm.doc.docstatus != 1){
				if(frm.doc.invoice_type == "Direct Invoice"){
					frm.trigger("boq_type");
				}
				else {
					get_mb_list(frm);
				}
				calculate_totals(frm);
			}
		}
	},
	
	onload_post_render: function(frm){

	},
	
	refresh: function(frm, cdt, cdn) {
		frm.trigger("boq_type");
		frm.trigger("invoice_type");
		if(frm.doc.__islocal){
			calculate_totals(frm);
		}
							
		if(frm.doc.project){
			if(frappe.model.can_read("Project")) {
				frm.add_custom_button(__("Project"), function() {
					frappe.route_options = {"name": frm.doc.project}
					frappe.set_route("Form", "Project", frm.doc.project);
				}, __("View"), true);
			}						
		}

		if(frm.doc.boq){
			if(frappe.model.can_read("BOQ")) {
				frm.add_custom_button(__("BOQ"), function() {
					frappe.route_options = {"name": frm.doc.boq}
					frappe.set_route("Form", "BOQ", frm.doc.boq);
				}, __("View"), true);
			}					
		}
		
		if(frm.doc.docstatus===1){
			frm.add_custom_button(__('Accounting Ledger'), function(){
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.invoice_date,
					to_date: frm.doc_invoice_date,
					company: frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
			
			if(frappe.model.can_read("Project Payment") && parseFloat(frm.doc.total_balance_amount) > 0){
				frm.add_custom_button(__("Payment"), function(){
					frm.trigger("make_project_payment")},
					__("Make"), "icon-file-alt");
			}
		}
	},

	project: function(frm){
		cur_frm.add_fetch("project","branch","branch");
		cur_frm.add_fetch("project","cost_center","cost_center");
		cur_frm.add_fetch("project","customer","customer");
			
		if(frm.doc.invoice_type == "Direct Invoice"){
			frm.trigger("boq_type");
		}
		else {
			get_mb_list(frm);
		}
		calculate_totals(frm);
	},
	
	make_project_payment: function(frm){
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.project_payment.project_payment.make_project_payment",
			frm: frm
		});
	},
	
	price_adjustment_amount: function(frm){
		calculate_totals(frm);
	},
	
	advance_recovery: function(frm){
		calculate_totals(frm);
	},
	
	tds_amount: function(frm){
		calculate_totals(frm);
	},
	
	check_all: function(frm){
		check_uncheck_all(frm);
	},

	check_all_mb: function(frm){
		check_uncheck_all(frm);
	},
	
	boq_type: function(frm){
		toggle_items_based_on_boq_type(frm);
	},
	
	invoice_type: function(frm){
		frm.set_df_property("price_adjustment_amount","read_only",(frm.doc.invoice_type === 'MB Based Invoice' ? 1 : 0));
	},
	
	get_mb_entries: function(frm, cdt, cdn){
		get_mb_list(frm);
	}
});

// Project Invoice BOQ
frappe.ui.form.on("Project Invoice BOQ",{
	invoice_quantity: function(frm, cdt, cdn){
		child = locals[cdt][cdn];
		
		if(child.invoice_quantity > child.act_quantity){
			msgprint(__("Invoice Quantity cannot be greater than balance quantity.").format(child.invoice_quantity))
		}
		
		//if(child.invoice_quantity && child.invoice_rate){
		frappe.model.set_value(cdt, cdn, 'invoice_amount', (parseFloat(child.invoice_quantity)*parseFloat(child.invoice_rate)).toFixed(2));
		//}
	},
	
	invoice_amount: function(frm, cdt, cdn){
		child = locals[cdt][cdn];
		
		if(child.invoice_amount > child.act_amount){
			msgprint(__("Invoice Amount cannot be greater than balance amount."));
		}
		calculate_totals(frm);
	},
	
	is_selected: function(frm, cdt, cdn){
		calculate_totals(frm);
	},
	
	project_invoice_boq_remove: function(frm, cdt, cdn){
		calculate_totals(frm);
	},
});

// Project Invoice MB
frappe.ui.form.on("Project Invoice MB",{
	is_selected: function(frm, cdt, cdn){
		calculate_totals(frm);
	},
	
	project_invoice_mb_remove: function(frm, cdt, cdn){
		calculate_totals(frm);
	},
	
	price_adjustment_amount: function(frm,cdt,cdn){
		calculate_totals(frm);
	}
});

// Custom Functions
var toggle_child_tables = function(frm){
	//var boq = frappe.meta.get_docfield("Project Invoice BOQ", "item", cur_frm.doc.name);
	//boq.hidden = 1;
	
	if(frm.doc.invoice_type == "Direct Invoice"){
		frm.toggle_enable("project_invoice_boq", true);
		frm.toggle_enable("project_invoice_mb", false);
	} else {
		frm.toggle_enable("project_invoice_boq", false);
		frm.toggle_enable("project_invoice_mb", true);
	}	
}

var get_mb_list = function(frm){
	frappe.call({
		method: "erpnext.projects.doctype.project_invoice.project_invoice.get_mb_list",
		args: {
			"project": frm.doc.project,
			"boq_name": frm.doc.boq ||  "dummy",
			"entry_name": frm.doc.reference_name || "dummy"
		},
		callback: function(r){
			if(r.message){
				cur_frm.clear_table("project_invoice_mb");
				r.message.forEach(function(mb){
					var row = frappe.model.add_child(frm.doc, "Project Invoice MB", "project_invoice_mb");
					row.entry_name 			= mb['name'];
					row.entry_date 			= mb['entry_date'];
					row.entry_amount 		= parseFloat(mb['total_balance_amount']);
					row.act_entry_amount 	= parseFloat(mb['total_entry_amount']);
					row.act_invoice_amount 	= parseFloat(mb['total_invoice_amount']);
					row.act_received_amount = parseFloat(mb['total_received_amount']);
					row.act_balance_amount 	= parseFloat(mb['total_balance_amount']);
					row.boq 				= mb['boq'];
					row.boq_type 			= mb['boq_type'];
				});
				cur_frm.refresh();
			}
			else {
				cur_frm.clear_table("project_invoice_mb");
				cur_frm.refresh();
			}
		}
	});	
}

var toggle_items_based_on_boq_type = function(frm){
		var invoice_amount_editable = frm.doc.boq_type==="Milestone Based" ? true : false;

		var invoice_quantity_editable = in_list(["Item Based", 
			"Piece Rate Work Based(PRW)"], frm.doc.boq_type) ? true : false;
			
		// Had to disable the following code as it is not working when boq_type changes, 
		// 	works only on reload which is cumbersome for users
		/*
		frm.fields_dict["project_invoice_boq"].grid.toggle_enable("invoice_quantity",
			invoice_quantity_editable);
		
		frm.fields_dict["project_invoice_boq"].grid.toggle_enable("invoice_amount",
			invoice_amount_editable);
		*/
}

var calculate_totals = function(frm){
	var pi = frm.doc.project_invoice_boq || [];
	var mb = frm.doc.project_invoice_mb || [];
	var gross_invoice_amount = 0.0, price_adjustment_amount = 0.0, net_invoice_amount =0.0;
	
	//frm.enable_save();
	
	if(frm.doc.docstatus != 1)
	{
		if(frm.doc.invoice_type == "Direct Invoice"){
			// Direct Invoice
			for(var i=0; i<pi.length; i++){
				if(pi[i].invoice_amount && pi[i].is_selected==1){
					gross_invoice_amount += parseFloat(pi[i].invoice_amount);
				}
			}
		}
		else {
			// MB Based Invoice
			for(var i=0; i<mb.length; i++){
				if(mb[i].entry_amount && mb[i].is_selected==1){
					gross_invoice_amount += parseFloat(mb[i].entry_amount);
					price_adjustment_amount += parseFloat(mb[i].price_adjustment_amount || 0.0);

					/*
					if((parseFloat(mb[i].price_adjustment_amount || 0.0)+parseFloat(mb[i].entry_amount)) < 0.0){
						msgprint(__("Row#{0} : Price Adjustment Amount cannot exceed entry amount.",[mb[i].idx]));
						validated = false;
						frm.disable_save();
					}
					*/
				}
			}
			
			if(parseFloat(frm.doc.price_adjustment_amount || 0.0) != parseFloat(price_adjustment_amount || 0.0)){
				cur_frm.set_value("price_adjustment_amount",parseFloat(price_adjustment_amount));
			}

		}
				
		net_invoice_amount = (parseFloat(gross_invoice_amount)+parseFloat(frm.doc.price_adjustment_amount || 0.0)-parseFloat(frm.doc.advance_recovery || 0.0)-parseFloat(frm.doc.tds_amount || 0.0));
		cur_frm.set_value("gross_invoice_amount",(gross_invoice_amount));
		cur_frm.set_value("net_invoice_amount",(net_invoice_amount));
		cur_frm.set_value("total_balance_amount",(parseFloat(frm.doc.net_invoice_amount || 0)-parseFloat(frm.doc.total_received_amount || 0)));
	}
}

var check_uncheck_all = function(frm){
	if(frm.doc.invoice_type == "Direct Invoice"){
		var pib =frm.doc.project_invoice_boq || [];

		for(var id in pib){
			frappe.model.set_value("Project Invoice BOQ", pib[id].name, "is_selected", frm.doc.check_all);
		}
	}
	else {
		var mb = frm.doc.project_invoice_mb || [];
		
		for(var id in mb){
			frappe.model.set_value("Project Invoice MB", mb[id].name, "is_selected", frm.doc.check_all_mb);
		}
	}
}
