// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("project", "branch","branch");
cur_frm.add_fetch("project", "cost_center","cost_center");
cur_frm.add_fetch("boq", "boq_type", "boq_type");
		
frappe.ui.form.on('BOQ Adjustment', {
	setup: function(frm){		
		frm.get_field('boq_item').grid.editable_fields = [
			{fieldname: 'boq_code', columns: 1},
			{fieldname: 'item', columns: 2},
			{fieldname: 'is_group', columns: 1},
			{fieldname: 'quantity', columns: 2},
			{fieldname: 'balance_quantity', columns: 2},
			{fieldname: 'adjustment_quantity', columns: 2}
		];
	},
	
	onload: function(frm){
		frm.fields_dict.boq.get_query = function(){
			return {
				filters:{
					'project': frm.doc.project,
					'docstatus': 1
				}
			}
		};
	},
	
	refresh: function(frm) {
		if(!frm.doc.__islocal && frm.doc.project){
			frm.trigger('get_defaults');
		}
	},
	
	project: function(frm){
		frm.trigger("get_defaults");
	},
	
	boq: function(frm){
		frm.add_fetch("boq", "boq_type", "boq_type");
	},
	
	get_defaults: function(frm){
		frm.add_fetch("project", "branch","branch");
		frm.add_fetch("project", "cost_center","cost_center");		
	},
});

frappe.ui.form.on("BOQ Adjustment Item",{	
	adjustment_quantity: function(frm, cdt, cdn){
		calculate_amount(frm, cdt, cdn);
		calculate_total_amount(frm);
	},
	
	adjustment_amount: function(frm, cdt, cdn){
		calculate_amount(frm, cdt, cdn);
		calculate_total_amount(frm);
	},
	
	boq_item_remove: function(frm, cdt, cdn){
		calculate_total_amount(frm);
	}
});

var calculate_amount = function(frm, cdt, cdn){
	child = locals[cdt][cdn];
	amount = 0.0;
	
	if(child.is_group){
		if(parseFloat(child.adjustment_quantity) || parseFloat(child.adjustment_amount)) {
			frappe.msgprint("Adjustments against group items not permitted.");
		}
	}
	else {
		if(frm.doc.boq_type != "Milestone Based"){
			amount = parseFloat(child.adjustment_quantity)*parseFloat(child.rate);
			frappe.model.set_value(cdt, cdn, 'adjustment_amount', parseFloat(amount));
		}
		else {
			if(child.adjustment_quantity){
				frappe.model.set_value(cdt, cdn, 'adjustment_quantity', 0.0);
			}
		}
		
		if ((parseFloat(child.balance_amount || 0.0)+parseFloat(child.adjustment_amount || 0.0)) < 0) {
			frappe.msgprint("Adjustment beyond available balance is not allowed.");
		}
	}
}

var calculate_total_amount = function(frm){
	var bi = frm.doc.boq_item || [];
	var total_amount = 0.0;
	
	for(var i=0; i<bi.length; i++){
		if (bi[i].amount){
			total_amount += parseFloat(bi[i].adjustment_amount);
		}
	}
	
	cur_frm.set_value("total_amount",parseFloat(total_amount));
}
