// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("branch", "cost_center", "cost_center")
frappe.ui.form.on('TDS Remittance', {
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
	setup: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;		
		
	},
	refresh: function(frm) {
		if(frm.doc.docstatus===1){
                        frm.add_custom_button(__('Accounting Ledger'), function(){
                                frappe.route_options = {
                                        voucher_no: frm.doc.name,
                                        from_date: frm.doc.from_date,
                                        to_date: frm.doc_to_date,
                                        company: frm.doc.company,
                                        group_by_voucher: false
                                };
                                frappe.set_route("query-report", "General Ledger");
                        }, __("View"));
	}
	},
	tds_rate: function(frm){
		switch(frm.doc.tds_rate){
			case "2": 
				frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'tds_2_account',
                        	function(d) {
                            		frm.set_value("tds_account",d.tds_2_account);

                        	});
				break;
			case "3": frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'tds_3_account',
                        		function(d) {
                            			frm.set_value("tds_account",d.tds_3_account);

                        		});


					break;
			case "5": 
					frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'tds_5_account',
					function(d) {
				    		frm.set_value("tds_account",d.tds_5_account);
					});


					break;
			case "10": 
				frappe.model.get_value('Accounts Settings',{'name': 'Accounts Settings'},  'tds_10_account',
                        	function(d) {
                            		frm.set_value("tds_account",d.tds_10_account);

                        	});

				break;
		}
	}
});
