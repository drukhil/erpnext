// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Advance', {
	refresh: function(frm) {
		if(frm.doc.customer && frm.doc.docstatus == 0){
			fetch_customer_details(frm);
		}
		
		if(frappe.model.can_read("Project")) {
			frm.add_custom_button(__("Project"), function() {
				frappe.route_options = {"name": frm.doc.project}
				frappe.set_route("Form", "Project", frm.doc.project);
			}, __("View"), true);
			
			if (frm.doc.docstatus == 0){
				set_mandatory(frm);
			}
		}
	},
	
	project: function(frm){
		set_mandatory(frm);
	}
	
	/*
	customer: function(frm){
		if(frm.doc.__islocal){
			fetch_customer_details(frm);
		}
	}
	*/
});

var set_mandatory = function(frm){
	if (frm.doc.project) {
		frm.add_fetch("project","branch","branch");
		frm.add_fetch("project","cost_center","cost_center");
	}
}

var fetch_customer_details = function(frm){
	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "Customer",
			filters: {
				name: frm.doc.customer
			},
			fieldname:["customer_details","default_currency"]
		},
		callback: function(r){
			cur_frm.set_value("customer_details", r.message.customer_details);
			cur_frm.set_value("customer_currency", r.message.default_currency);
		}
	});
}