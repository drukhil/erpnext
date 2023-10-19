// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Direct Payment', {
	refresh: function(frm) {
		if(!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today())
		}
		if(frm.doc.party_type == "Customer"){
			cur_frm.set_query("party", function() {
				return {
					"filters": {
						"inter_company": 1
					}
				}
			});
		}

		if(frm.doc.docstatus===1){
			frm.add_custom_button(__('Accounting Ledger'), function(){
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
		}
	},

	"party_type": function(frm){
		cur_frm.set_value("party","");
	},
	"payment_type": function(frm){
		cur_frm.set_value("party_type", (frm.doc.payment_type == "Receive")? "Customer":"Supplier");
		if(frm.doc.party_type == "Customer"){
			cur_frm.set_query("party", function() {
				return {
					"filters": {
						"inter_company": 1
					}
				}
			});
		}
		if(frm.doc.payment_type == "Receive"){
			frappe.model.get_value('Branch', {'name': frm.doc.branch}, 'revenue_bank_account',
			function(d) {
			    cur_frm.set_value("debit_account",d.revenue_bank_account);
		    	cur_frm.set_value("credit_account","");
			});
		}
		if(frm.doc.payment_type == "Payment"){
			frappe.model.get_value('Branch', {'name': frm.doc.branch}, 'expense_bank_account',
			  function(d) {
			    cur_frm.set_value("credit_account",d.expense_bank_account);
			    cur_frm.set_value("debit_account","");
			});
		}
		calculate_tds(frm);
	},
	"amount": function(frm) {
		frm.set_value("taxable_amount", parseFloat(frm.doc.amount))
		calculate_tds(frm);
	},
	"tds_percent": function(frm) {
		calculate_tds(frm);
		cur_frm.set_df_property("tds_account", "reqd", (frm.doc.tds_percent > 1)? 1:0);
	},
	"taxable_amount": function(frm) {
		calculate_tds(frm);
	},
	"deduction_amount": function(frm){
		frm.set_value("net_amount",  parseFloat(frm.doc.amount) - parseFloat(frm.doc.tds_amount) - parseFloat(frm.doc.deduction_amount)	)	}
			,
	"tds_amount": function(frm){
		frm.set_value("net_amount", parseFloat(frm.doc.amount) - parseFloat(frm.doc.tds_amount) - parseFloat(frm.doc.deduction_amount))
	},
	"branch": function(frm) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Cost Center", 
				fieldname:"name",
				filters: {
					branch: frm.doc.branch
				}
			},
			callback: function(r) {
				if(r.message.name) {
					cur_frm.set_value("cost_center", r.message.name)
				}				
			}
		});
		if(frm.doc.payment_type == "Receive"){
			frappe.model.get_value('Branch', {'name': frm.doc.branch}, 'revenue_bank_account',
			  function(d) {
			    cur_frm.set_value("debit_account",d.revenue_bank_account);
			});
		}
		if(frm.doc.payment_type == "Payment"){
			frappe.model.get_value('Branch', {'name': frm.doc.branch}, 'expense_bank_account',
			  function(d) {
			    cur_frm.set_value("credit_account",d.expense_bank_account);
			});
		}
	},
	"party": function(frm) {
		frm.set_value("pay_to_recd_from", frm.doc.party);
	}
/*
	"customer": function(frm) {
		frm.set_value("pay_to_recd_from", frm.doc.customer);
	} */
});
function roundOff(num) {    
    return +(Math.round(num + "e+2")  + "e-2");
}

function calculate_tds(frm) {
	var tds = Math.round(parseFloat(frm.doc.tds_percent) * parseFloat(frm.doc.taxable_amount) / 100 );
	frm.set_value("tds_amount", tds);
	if(tds > 0){
		if(frm.doc.deduction_amount)
			frm.set_value("net_amount", frm.doc.amount - frm.doc.deduction_amount - tds);
		else
			frm.set_value("net_amount", frm.doc.amount - tds);
	}else{
		if(frm.doc.deduction_amount)
			frm.set_value("net_amount", frm.doc.amount - frm.doc.deduction_amount);
		else
			frm.set_value("net_amount", frm.doc.amount);
	}

	frappe.call({
		method: "erpnext.accounts.doctype.direct_payment.direct_payment.get_tds_account",
		args: {
			percent: frm.doc.tds_percent,
			payment_type: frm.doc.payment_type
		},
		callback: function(r) {
			if(r.message) {
				frm.set_value("tds_account", r.message);
				cur_frm.refresh_field("tds_account");
			}
		}
	});
}


frappe.ui.form.on("Direct Payment", "onload", function(frm){
	cur_frm.set_query("select_cheque_lot", function(){
		return {
			"filters": [
				["branch", "=", frm.doc.branch],
				["status", "!=", "Used"],
				["docstatus", "=", "1"]	
			]	
		}
	});
});

frappe.ui.form.on("Direct Payment", "select_cheque_lot", function(frm){
	if(frm.doc.select_cheque_lot){
		frappe.call({
			method:"erpnext.accounts.doctype.cheque_lot.cheque_lot.get_cheque_no_and_date",
			args:{
				'name':frm.doc.select_cheque_lot
			},
			callback: function(r){
				if(r.message){
					cur_frm.set_value("cheque_no", r.message[0].reference_no);
					cur_frm.set_value("cheque_date", r.message[0].reference_date);	
				}
			}			
		});
	}
})

frappe.ui.form.on("Direct Payment Deduction", { 
	"amount": function(frm, cdt, cdn) {
		calculate_total(frm,cdt,cdn)
	}
});

function calculate_total(frm, cdt, cdn) {
	var deducts = locals[cdt][cdn]
		var total = 0;
		
		frm.doc.deduct.forEach(function(d) {
			total     += parseFloat(d.amount);
			cur_frm.set_value("deduction_amount", total);
			if(frm.doc.tds_amount)
				cur_frm.set_value("net_amount", (frm.doc.amount - frm.doc.tds_amount - frm.doc.deduction_amount));
			else
				cur_frm.set_value("net_amount", (frm.doc.amount - frm.doc.deduction_amount));

		})
	}
