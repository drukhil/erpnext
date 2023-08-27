// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("equipment", "equipment_number", "equipment_number")

frappe.ui.form.on('Expense Allocation', {
	setup: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;			
			
	},
	refresh: function(frm) {

	},
	branch: function(frm){
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
		}
	},
});
frappe.ui.form.on('Expense Allocation Item',{
	quantity: function(frm, cdt, cdn){
		calculate_amount(frm, cdt, cdn);
	},
	
	rate: function(frm, cdt, cdn){
		calculate_amount(frm, cdt, cdn);
	},
	
	amount: function(frm){
		update_totals(frm);
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
	var tot_amount= 0.0;
		
		
	for(var i=0; i<det.length; i++){
			tot_amount += parseFloat(det[i].amount || 0.0);
	}
	cur_frm.set_value("total_amount",tot_amount);
	
}

cur_frm.fields_dict['items'].grid.get_field('cost_center').get_query = function(frm, cdt, cdn) {
	return {
            "filters": {
                "is_disabled": 0,
                "is_group": 0
            }
        };
}