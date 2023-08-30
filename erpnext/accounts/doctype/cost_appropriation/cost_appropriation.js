// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


cur_frm.add_fetch("branch", "cost_center", "cost_center")
cur_frm.add_fetch("cost_center", "branch", "branch")
frappe.ui.form.on('Cost Appropriation', {
	get_details: function(frm) {
		return frappe.call({
			method: "get_details",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("items");
				frm.refresh_fields();
			}
		});
	},
	refresh: function(frm) {
		if(frm.doc.docstatus===1){
                        frm.add_custom_button(__('Accounting Ledger'), function(){
                                frappe.route_options = {
                                        voucher_no: frm.doc.name,
                                        from_date: frm.doc.from_date,
                                        to_date: frm.doc.to_date,
                                        company: frm.doc.company,
                                        group_by_voucher: false
                                };
                                frappe.set_route("query-report", "General Ledger");
                        }, __("View"));
	}
	},
	branch: function(frm){
		// Update Cost Center
		if(frm.doc.branch){
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Cost Center',
					filters: {
						'branch': frm.doc.branch
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

	cost_type: function(frm){
		switch(frm.doc.cost_type){
			case "Hire Charge": 
				frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'hire_charge',
                        	function(d) {
                            		frm.set_value("account",d.hire_charge);

                        	});
				break;
			case "HSD": frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'hsd',
                        		function(d) {
                            			frm.set_value("account",d.hsd);

                        		});


					break;
			case "Lubricant": 
					frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'lubricant',
					function(d) {
				    		frm.set_value("account",d.lubricant);
					});


					break;
			case "Operator Allowance": 
				frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'operator_allowance',
                        	function(d) {
                            		frm.set_value("account",d.operator_allowance);

                        	});

				break;
			case "OAP Salary": 
				frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'oap_salary',
                        	function(d) {
                            		frm.set_value("account",d.oap_salary);

                        	});

				break;
				case "GCE": 
				frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'gce',
				function(d) {
						frm.set_value("account",d.gce);
				});


				break;
		case "Overtime Payment": 
			frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'overtime_payment',
						function(d) {
								frm.set_value("account",d.overtime_payment);

						});

			break;
		case "Muster Roll Employee": 
			frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'muster_roll_employee',
						function(d) {
								frm.set_value("account",d.muster_roll_employee);

						});

			break;
			
		}
	}
});
// frappe.ui.form.on('Cost Appropriation Item',{
// 	quantity: function(frm, cdt, cdn){
// 		calculate_amount(frm, cdt, cdn);
// 	},
	
// 	rate: function(frm, cdt, cdn){
// 		calculate_amount(frm, cdt, cdn);
// 	},
	
// 	amount: function(frm){
// 		update_totals(frm);
// 	},
// });

// var calculate_amount = function(frm, cdt, cdn){
// 	var child  = locals[cdt][cdn];
// 	var amount = 0.0;
	
// 	amount = parseFloat(child.quantity || 0.0)*parseFloat(child.rate || 0.0);
// 	frappe.model.set_value(cdt, cdn, "amount", parseFloat(amount || 0.0));
// }

// var update_totals = function(frm){
// 	var det = frm.doc.items || [];
// 	var tot_amount= 0.0;
		
		
// 	for(var i=0; i<det.length; i++){
// 			tot_amount += parseFloat(det[i].amount || 0.0);
// 	}
// 	cur_frm.set_value("total_amount",tot_amount);
	
// }

// cur_frm.fields_dict['items'].grid.get_field('cost_center').get_query = function(frm, cdt, cdn) {
// 	return {
//             "filters": {
//                 "is_disabled": 0,
//                 "is_group": 0
//             }
//         };
// }