// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('MB Entry', {
	setup: function(frm){
		frm.get_field('mb_entry_boq').grid.editable_fields = [
			{fieldname: 'item', columns: 3},
			{fieldname: 'is_selected', columns: 1},
			{fieldname: 'uom', columns: 1},
			{fieldname: 'entry_quantity', columns: 1},
			{fieldname: 'entry_rate', columns: 2},
			{fieldname: 'entry_amount', columns: 2}
		];		
	},

	onload: function(frm){
		calculate_totals(frm);
	},
	
	onload_post_render: function(frm){
		cur_frm.refresh();
	},
	
	refresh: function(frm, cdt, cdn) {
		//if(!frm.doc.__islocal){
				
			
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
			if(frappe.model.can_read("Project Invoice") && parseFloat(frm.doc.total_balance_amount) > 0){
				frm.add_custom_button(__("Invoice"), function(){
					frm.trigger("make_mb_invoice")},
					__("Make"), "icon-file-alt");
			}
		}		
		
		/*
		if(frm.doc.boq_type=="Item Based"){
			frm.fields_dict.mb_entry_boq.grid.toggle_enable("entry_quantity", true);
			frm.fields_dict.mb_entry_boq.grid.toggle_enable("entry_amount", false);
			//frm.fields_dict.mb_entry_boq.grid.set_column_disp("entry_quantity", true);			
		} 
		else if(frm.doc.boq_type=="Milestone Based"){
			frm.fields_dict.mb_entry_boq.grid.toggle_enable("entry_quantity", false);
			frm.fields_dict.mb_entry_boq.grid.toggle_enable("entry_amount", true);
		}
		else if(frm.doc.boq_type=="Piece Rate Work Based(PRW)"){
			frm.fields_dict.mb_entry_boq.grid.toggle_enable("entry_quantity", true);
			frm.fields_dict.mb_entry_boq.grid.toggle_enable("entry_amount", false);
		}		
		*/
	},

	make_mb_invoice: function(frm){
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.mb_entry.mb_entry.make_mb_invoice",
			frm: frm
		});
	},	
	
	check_all: function(frm){
		check_uncheck_all(frm);
	}
});

frappe.ui.form.on("MB Entry BOQ",{
	entry_quantity: function(frm, cdt, cdn){
		child = locals[cdt][cdn];
		
		if(child.entry_quantity > child.act_quantity){
			msgprint(__("Invoice Quantity cannot be greater than balance quantity.").format(child.entry_quantity))
		}
		
		//if(child.entry_quantity && child.entry_rate){
		frappe.model.set_value(cdt, cdn, 'entry_amount', (parseFloat(child.entry_quantity)*parseFloat(child.entry_rate)).toFixed(2));
		//}
	},
	entry_amount: function(frm, cdt, cdn){
		child = locals[cdt][cdn];
		
		if(child.entry_amount > child.act_amount){
			msgprint(__("Invoice Amount cannot be greater than balance amount."));
		}
		calculate_totals(frm);
	},
	is_selected: function(frm, cdt, cdn){
		calculate_totals(frm);
	},
});

var calculate_totals = function(frm){
	var me = frm.doc.mb_entry_boq || [];
	var total_entry_amount = 0.0, net_entry_amount =0.0;
	
	if(frm.doc.docstatus != 1)
	{
		for(var i=0; i<me.length; i++){
			if(me[i].entry_amount && me[i].is_selected==1){
				total_entry_amount += parseFloat(me[i].entry_amount);
			}
		}
		
		cur_frm.set_value("total_entry_amount",(total_entry_amount));
		cur_frm.set_value("total_balance_amount",(parseFloat(total_entry_amount || 0)-parseFloat(frm.doc.total_received_amount || 0)));
	}
}

var check_uncheck_all = function(frm){
	var meb =frm.doc.mb_entry_boq || [];

	for(var id in meb){
		frappe.model.set_value("MB Entry BOQ", meb[id].name, "is_selected", frm.doc.check_all);
	}
}
