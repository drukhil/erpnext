// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
/*
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0		          SHIV		   04/09/2017                            * Added "Project Advance" to Reference Type
2.0               SHIV         06/08/2018                            * Filtering bank accounts for "Journal Entry" as per
																		support ticket# 867
--------------------------------------------------------------------------------------------------------------------------                                                                          
*/

frappe.provide("erpnext.accounts");
frappe.provide("erpnext.journal_entry");


frappe.ui.form.on("Journal Entry", {
	setup: function(frm) {
		frm.get_field('accounts').grid.editable_fields = [
			{fieldname: 'account', columns: 3},
			{fieldname: 'party', columns: 1},
			{fieldname: 'cost_center', columns: 2},
			{fieldname: 'debit_in_account_currency', columns: 2},
			{fieldname: 'credit_in_account_currency', columns: 2}
		];
	},
	onload: function(frm) {
		/* ePyment Begins */
		create_custom_buttons(frm);
		/* ePayment Ends */
	},

	refresh: function(frm) {
		//erpnext.toggle_naming_series();
		cur_frm.toggle_display("naming_series", 1)
		frm.cscript.voucher_type(frm.doc);
		
		if(frm.doc.docstatus==1) {
			frm.add_custom_button(__('Ledger'), function() {
				frappe.route_options = {
					"voucher_no": frm.doc.name,
					"from_date": frm.doc.posting_date,
					"to_date": frm.doc.posting_date,
					"company": frm.doc.company,
					group_by_voucher: 0
				};
				frappe.set_route("query-report", "General Ledger");
			}, "icon-table");
		}

		if (frm.doc.__islocal) {
			frm.add_custom_button(__('Quick Entry'), function() {
				return erpnext.journal_entry.quick_entry(frm);
			});
		}

		// hide /unhide fields based on currency
		erpnext.journal_entry.toggle_fields_based_on_currency(frm);
		//Hide cancel button if is bank reconcilled
		if(frm.doc.clearance_date) {
			$(document).ready(function(){
				$(".btn-sm").css("display", "none");
			});
		}
		else {
			$(document).ready(function(){
				$(".btn-sm").css("display", "inline");
			});
		}
		if(cur_frm.fields_dict.naming_series) {
			console.log("Naming Series")
			cur_frm.toggle_display("naming_series", 1)
		}
	},

	multi_currency: function(frm) {
		erpnext.journal_entry.toggle_fields_based_on_currency(frm);
	},

	branch: function(frm){
		// not sure of the use of below code so commented. Kinley Dorji
		// if (frm.doc.branch == undefined || frm.doc.voucher_type != 'Bank Entry'){
		// 	return;
		// } else {
		// 	frm.doc.voucher_type = "Journal Entry"
		// 	frm.doc.accounts.forEach((acc) => {
		// 		acc.account = ""
		// 		frm.refresh_fields();
		// 	});
		// }
	},

	voucher_type: function(frm){
		console.log(frm.doc.voucher_type)
		if (frm.doc.branch == undefined || frm.doc.voucher_type != 'Bank Entry' && (frm.doc.naming_series != 'Bank Payment Voucher' || 
		frm.doc.naming_series != 'Bank Receipt Voucher')){
			// frm.doc.accounts.forEach((acc) => {
			// 	acc.account = ""
			// 	frm.refresh_fields();
			// });
			console.log(frm.doc.voucher_type, "inside", frm.doc.naming_series,frm.doc.branch)
			return;
		}
		console.log(frm.doc.voucher_type, "outside")
		set_accounts(frm);
    },

	naming_series: function(frm){
		if (frm.doc.voucher_type != 'Bank Entry'){
			return;
		}
		set_accounts(frm);
	},
	
	get_series: function(frm) {
		return frappe.call({
			method: "get_series",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.reload_doc();
			}
		});
	}
})

function set_accounts(frm){
	frappe.call({
		method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_parent_cost_center",
		args: { branch : frm.doc.branch},
		callback: function(r) {
			if(r.message) {
				if (r.message == 'Corporate Head Office - NRDCL'){
					return;
				}
				frm.doc.accounts.forEach((acc) => {
					if (frm.doc.naming_series == 'Bank Payment Voucher'){
						frappe.model.get_value('Branch', {'name': frm.doc.branch}, 'expense_bank_account',
							function(d) {
								acc.account = d.expense_bank_account
								frm.refresh_fields();
						});
					}else if (frm.doc.naming_series == 'Bank Receipt Voucher'){
						frappe.model.get_value('Branch', {'name': frm.doc.branch}, 'revenue_bank_account',
						function(d) {
							acc.account = d.revenue_bank_account					
							frm.refresh_fields();
						});
					} else {
						acc.account = ""					
						frm.refresh_fields();
					}
				});
				frm.refresh_fields();
			}
		}
	});
}

erpnext.accounts.JournalEntry = frappe.ui.form.Controller.extend({
	onload: function() {
		this.load_defaults();
		this.setup_queries();
		this.setup_balance_formatter();
	},

	onload_post_render: function() {
		cur_frm.get_field("accounts").grid.set_multiple_add("account");
	},

	load_defaults: function() {
		//this.frm.show_print_first = true;
		if(this.frm.doc.__islocal && this.frm.doc.company) {
			frappe.model.set_default_values(this.frm.doc);
			$.each(this.frm.doc.accounts || [], function(i, jvd) {
					frappe.model.set_default_values(jvd);
				}
			);

			if(!this.frm.doc.amended_from) this.frm.doc.posting_date = this.frm.posting_date || get_today();
		}
	},

	setup_queries: function() {
		var me = this;

		me.frm.set_query("account", "accounts", function(doc, cdt, cdn) {
			return erpnext.journal_entry.account_query(me.frm);
		});

		me.frm.set_query("cost_center", "accounts", function(doc, cdt, cdn) {
			return {
				filters: {
					company: me.frm.doc.company,
					is_group: 0,
					is_disabled: 0,
				}
			};
		});

		me.frm.set_query("party_type", "accounts", function(doc, cdt, cdn) {
			return {
				filters: {"name": ["in", ["Customer", "Supplier","Employee","Equipment"]]}
			}
		});

		me.frm.set_query("reference_name", "accounts", function(doc, cdt, cdn) {
			var jvd = frappe.get_doc(cdt, cdn);

			// ++++++++++++++++++++ Ver 1.0 BEGINS ++++++++++++++++++++
			// Project Advance
			// Following code added by SHIV on 04/09/2017
			if(jvd.reference_type==="Project Advance"){
				return {};
			}
			// +++++++++++++++++++++ Ver 1.0 ENDS +++++++++++++++++++++
			
			// expense claim
			if(jvd.reference_type==="Expense Claim") {
				return {};
			}

			// expense claim
			if(jvd.reference_type==="Hall Booking") {
				return {};
			}

			// journal entry
			if(jvd.reference_type==="Journal Entry") {
				frappe.model.validate_missing(jvd, "account");
				return {
					query: "erpnext.accounts.doctype.journal_entry.journal_entry.get_against_jv",
					filters: {
						account: jvd.account,
						party: jvd.party
					}
				};
			}
			if(jvd.reference_type != "Equipment"){
				var out = {
					filters: [
						[jvd.reference_type, "docstatus", "=", 1]
					]
				};
			}
			else{
				var out = {
					filters: [
						[jvd.reference_type, "is_disabled", "=", 0]
					]
				};
			}
			if(jvd.reference_type!="Equipment"){
				if(in_list(["Sales Invoice", "Purchase Invoice"], jvd.reference_type)) {
					out.filters.push([jvd.reference_type, "outstanding_amount", "!=", 0]);

					// account filter
					frappe.model.validate_missing(jvd, "account");

					party_account_field = jvd.reference_type==="Sales Invoice" ? "debit_to": "credit_to";
					out.filters.push([jvd.reference_type, party_account_field, "=", jvd.account]);
				} else {
					// party_type and party mandatory
					frappe.model.validate_missing(jvd, "party_type");
					frappe.model.validate_missing(jvd, "party");

					//out.filters.push([jvd.reference_type, "per_billed", "<", 100]);
				}

			if(jvd.party_type && jvd.party)	 {
				if(jvd.reference_type != "Hire Charge Invoice"){
					out.filters.push([jvd.reference_type,
					(jvd.reference_type.indexOf("Sales")===0 ? "customer" : "supplier"), "=", jvd.party]);
				}
				else{
					out.filters.push([jvd.reference_type,
						"customer", "=", jvd.party]);
				}
			}
		}
			return out;
		});


	},

	setup_balance_formatter: function() {
		var me = this;
		$.each(["balance", "party_balance"], function(i, field) {
			var df = frappe.meta.get_docfield("Journal Entry Account", field, me.frm.doc.name);
			df.formatter = function(value, df, options, doc) {
				var currency = frappe.meta.get_field_currency(df, doc);
				var dr_or_cr = value ? ('<label>' + (value > 0.0 ? __("Dr") : __("Cr")) + '</label>') : "";
				return "<div style='text-align: right'>"
					+ ((value==null || value==="") ? "" : format_currency(Math.abs(value), currency))
					+ " " + dr_or_cr
					+ "</div>";
			}
		})
	},

	reference_name: function(doc, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		if(d.reference_name) {
			if (d.reference_type==="Purchase Invoice" && !flt(d.debit)) {
				this.get_outstanding('Purchase Invoice', d.reference_name, doc.company, d);
			}
			if (d.reference_type==="Sales Invoice" && !flt(d.credit)) {
				this.get_outstanding('Sales Invoice', d.reference_name, doc.company, d);
			}
			if (d.reference_type==="Journal Entry" && !flt(d.credit) && !flt(d.debit)) {
				this.get_outstanding('Journal Entry', d.reference_name, doc.company, d);
			}
		}
		else {
			msgprint("NONE SELECTED")
		}
	},

	get_outstanding: function(doctype, docname, company, child) {
		var me = this;
		var args = {
			"doctype": doctype,
			"docname": docname,
			"party": child.party,
			"account": child.account,
			"account_currency": child.account_currency,
			"company": company
		}

		return frappe.call({
			method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_outstanding",
			args: { args: args},
			callback: function(r) {
				if(r.message) {
					$.each(r.message, function(field, value) {
						frappe.model.set_value(child.doctype, child.name, field, value);
					})
				}
			}
		});
	},

	accounts_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		$.each(doc.accounts, function(i, d) {
			if(d.account && d.party && d.party_type) {
				row.account = d.account;
				row.party = d.party;
				row.party_type = d.party_type;
			}
		});

		// set difference
		if(doc.difference) {
			if(doc.difference > 0) {
				row.credit_in_account_currency = doc.difference;
				row.credit = doc.difference;
			} else {
				row.debit_in_account_currency = -doc.difference;
				row.debit = -doc.difference;
			}
		}
		cur_frm.cscript.update_totals(doc);
	},

});

cur_frm.script_manager.make(erpnext.accounts.JournalEntry);

cur_frm.cscript.update_totals = function(doc) {
	var td=0.0; var tc =0.0;
	var accounts = doc.accounts || [];
	for(var i in accounts) {
		td += flt(accounts[i].debit, precision("debit", accounts[i]));
		tc += flt(accounts[i].credit, precision("credit", accounts[i]));
	}
	var doc = locals[doc.doctype][doc.name];
	doc.total_debit = td;
	doc.total_credit = tc;
	doc.difference = flt((td - tc), precision("difference"));
	refresh_many(['total_debit','total_credit','difference']);
}

cur_frm.cscript.get_balance = function(doc,dt,dn) {
	cur_frm.cscript.update_totals(doc);
	return $c_obj(cur_frm.doc, 'get_balance', '', function(r, rt){
	cur_frm.refresh();
	});
}

cur_frm.cscript.validate = function(doc,cdt,cdn) {
	cur_frm.cscript.update_totals(doc);
}

cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
	if(doc.select_print_heading){
		// print heading
		cur_frm.pformat.print_heading = doc.select_print_heading;
	}
	else
		cur_frm.pformat.print_heading = __("Journal Entry");
}

cur_frm.cscript.voucher_type = function(doc, cdt, cdn) {

	// Ver 20160617.1 by SSK on 17/06/2016, following two lines commented and the subsequent if condition added
	//cur_frm.set_df_property("cheque_no", "reqd", doc.voucher_type=="Bank Entry");
	//cur_frm.set_df_property("cheque_date", "reqd", doc.voucher_type=="Bank Entry");

	// Ver 20160617.1 by SSK on 17/06/2016, following if condition is added
	if(doc.docstatus == 1){
		if(doc.cheque_no){
			frappe.meta.get_docfield(doc.doctype, "cheque_no", this.frm.doc.name).read_only=1;
		}
		else {
			cur_frm.set_df_property("cheque_no", "reqd", doc.voucher_type=="Bank Entry");
		}

		if(doc.cheque_date){
			frappe.meta.get_docfield(doc.doctype, "cheque_date", this.frm.doc.name).read_only=1;
		}
		else {
			cur_frm.set_df_property("cheque_date", "reqd", doc.voucher_type=="Bank Entry");
		}

		// Ver 20160713.1 by SSK, field "Payee Name" is introducted
		if(doc.pay_to_recd_from){
			frappe.meta.get_docfield(doc.doctype, "pay_to_recd_from", this.frm.doc.name).read_only=0;
		}
		else {
			cur_frm.set_df_property("pay_to_recd_from", "reqd", doc.voucher_type=="Bank Entry");
		}
	}

	if(!doc.company) return;

	var update_jv_details = function(doc, r) {
		var jvdetail = frappe.model.add_child(doc, "Journal Entry Account", "accounts");
		$.each(r, function(i, d) {
			var row = frappe.model.add_child(doc, "Journal Entry Account", "accounts");
			row.account = d.account;
			row.balance = d.balance;
		});
		refresh_field("accounts");
	}

	if(!(doc.accounts || []).length) {
		if(in_list(["Bank Entry", "Cash Entry"], doc.voucher_type)) {
			return frappe.call({
				type: "GET",
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_default_bank_cash_account",
				args: {
					"account_type": (doc.voucher_type=="Bank Entry" ?
						"Bank" : (doc.voucher_type=="Cash" ? "Cash" : null)),
					"company": doc.company
				},
				callback: function(r) {
					if(r.message) {
						update_jv_details(doc, [r.message]);
					}
				}
			})
		} else if(doc.voucher_type=="Opening Entry") {
			return frappe.call({
				type:"GET",
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_opening_accounts",
				args: {
					"company": doc.company
				},
				callback: function(r) {
					frappe.model.clear_table(doc, "accounts");
					if(r.message) {
						update_jv_details(doc, r.message);
					}
					cur_frm.set_value("is_opening", "Yes")
				}
			})
		}
	}
}

frappe.ui.form.on("Journal Entry Account", {
	party: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		if(!d.account && d.party_type && d.party) {
			if(!frm.doc.company) frappe.throw(__("Please select Company"));
			return frm.call({
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_party_account_and_balance",
				child: d,
				args: {
					company: frm.doc.company,
					party_type: d.party_type,
					party: d.party
				}
			});
		}
	},

	account: function(frm, dt, dn) {
		var d = locals[dt][dn];
		if(d.account) {
			if(!frm.doc.company) frappe.throw(__("Please select Company first"));
			if(!frm.doc.posting_date) frappe.throw(__("Please select Posting Date first"));

			return frappe.call({
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_account_balance_and_party_type",
				args: {
					account: d.account,
					date: frm.doc.posting_date,
					company: frm.doc.company,
					debit: flt(d.debit_in_account_currency),
					credit: flt(d.credit_in_account_currency),
					exchange_rate: d.exchange_rate
				},
				callback: function(r) {
					if(r.message) {
						$.extend(d, r.message);
						erpnext.journal_entry.set_debit_credit_in_company_currency(frm, dt, dn);
						refresh_field('accounts');
					}
				}
			});
		}
	},

	debit_in_account_currency: function(frm, cdt, cdn) {
		erpnext.journal_entry.set_exchange_rate(frm, cdt, cdn);
	},

	credit_in_account_currency: function(frm, cdt, cdn) {
		erpnext.journal_entry.set_exchange_rate(frm, cdt, cdn);
	},

	debit: function(frm, dt, dn) {
		cur_frm.cscript.update_totals(frm.doc);
	},

	credit: function(frm, dt, dn) {
		cur_frm.cscript.update_totals(frm.doc);
	},

	exchange_rate: function(frm, cdt, cdn) {
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		var row = locals[cdt][cdn];

		if(row.account_currency == company_currency || !frm.doc.multi_currency) {
			frappe.model.set_value(cdt, cdn, "exchange_rate", 1);
		}

		erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
	},

	/*"account_currency": function(frm, cdt, cdn) {
		if(frm.doc.multi_currency) {
			item = locals[cdt][cdn]
			frappe.call({
				method: "erpnext.hr.doctype.travel_authorization.travel_authorization.get_exchange_rate",
				args: {
					from_currency: item.account_currency,
					to_currency: "BTN"
				},
				callback: function(r) {
					frappe.model.set_value(cdt, cdn, "exchange_rate", r.message)
				}
			})
		}		
	} */
})

frappe.ui.form.on("Journal Entry Account", "accounts_remove", function(frm) {
	cur_frm.cscript.update_totals(frm.doc);
});

$.extend(erpnext.journal_entry, {
	toggle_fields_based_on_currency: function(frm) {
		var fields = ["currency_section", "account_currency", "exchange_rate", "debit", "credit"];

		var grid = frm.get_field("accounts").grid;
		if(grid) grid.set_column_disp(fields, frm.doc.multi_currency);

		// dynamic label
		var field_label_map = {
			"debit_in_account_currency": "Debit",
			"credit_in_account_currency": "Credit"
		};

		$.each(field_label_map, function (fieldname, label) {
			var df = frappe.meta.get_docfield("Journal Entry Account", fieldname, frm.doc.name);
			df.label = frm.doc.multi_currency ? (label + " in Account Currency") : label;
		})
	},

	set_debit_credit_in_company_currency: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];

		frappe.model.set_value(cdt, cdn, "debit",
			flt(flt(row.debit_in_account_currency)*row.exchange_rate, precision("debit", row)));

		frappe.model.set_value(cdt, cdn, "credit",
			flt(flt(row.credit_in_account_currency)*row.exchange_rate, precision("credit", row)));

		cur_frm.cscript.update_totals(frm.doc);
	},

	set_exchange_rate: function(frm, cdt, cdn) {
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		var row = locals[cdt][cdn];

		if(row.account_currency == company_currency || !frm.doc.multi_currency) {
			row.exchange_rate = 1;
			erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
		} else if (!row.exchange_rate || row.exchange_rate == 1 || row.account_type == "Bank") {
			frappe.call({
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_exchange_rate",
				args: {
					account: row.account,
					account_currency: row.account_currency,
					company: frm.doc.company,
					reference_type: cstr(row.reference_type),
					reference_name: cstr(row.reference_name),
					debit: flt(row.debit_in_account_currency),
					credit: flt(row.credit_in_account_currency),
					exchange_rate: row.exchange_rate
				},
				callback: function(r) {
					if(r.message) {
						row.exchange_rate = r.message;
						erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
					}
				}
			})
		} else {
			erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
		}
		refresh_field("exchange_rate", cdn, "accounts");
	},

	quick_entry: function(frm) {
		var naming_series_options = frm.fields_dict.naming_series.df.options;
		var naming_series_default = frm.fields_dict.naming_series.df.default || naming_series_options.split("\n")[0];

		var dialog = new frappe.ui.Dialog({
			title: __("Quick Journal Entry"),
			fields: [
				{fieldtype: "Currency", fieldname: "debit", label: __("Amount"), reqd: 1},
				{fieldtype: "Link", fieldname: "debit_account", label: __("Debit Account"), reqd: 1,
					options: "Account",
					get_query: function() {
						return erpnext.journal_entry.account_query(frm);
					}
				},
				{fieldtype: "Link", fieldname: "credit_account", label: __("Credit Account"), reqd: 1,
					options: "Account",
					get_query: function() {
						return erpnext.journal_entry.account_query(frm);
					}
				},
				{fieldtype: "Date", fieldname: "posting_date", label: __("Date"), reqd: 1,
					default: frm.doc.posting_date},
				{fieldtype: "Small Text", fieldname: "user_remark", label: __("User Remark"), reqd: 1},
				{fieldtype: "Select", fieldname: "naming_series", label: __("Series"), reqd: 1,
					options: naming_series_options, default: naming_series_default},
			]
		});

		dialog.set_primary_action(__("Save"), function() {
			var btn = this;
			var values = dialog.get_values();

			frm.set_value("posting_date", values.posting_date);
			frm.set_value("user_remark", values.user_remark);
			frm.set_value("naming_series", values.naming_series);

			// clear table is used because there might've been an error while adding child
			// and cleanup didn't happen
			frm.clear_table("accounts");

			// using grid.add_new_row() to add a row in UI as well as locals
			// this is required because triggers try to refresh the grid

			var debit_row = frm.fields_dict.accounts.grid.add_new_row();
			frappe.model.set_value(debit_row.doctype, debit_row.name, "account", values.debit_account);
			frappe.model.set_value(debit_row.doctype, debit_row.name, "debit_in_account_currency", values.debit);

			var credit_row = frm.fields_dict.accounts.grid.add_new_row();
			frappe.model.set_value(credit_row.doctype, credit_row.name, "account", values.credit_account);
			frappe.model.set_value(credit_row.doctype, credit_row.name, "credit_in_account_currency", values.debit);

			frm.save();

			dialog.hide();
		});

		dialog.show();
	},

	account_query: function(frm) {
		var filters = {
			company: frm.doc.company,
			is_group: 0
		};
		if(!frm.doc.multi_currency) {
			$.extend(filters, {
				account_currency: frappe.get_doc(":Company", frm.doc.company).default_currency
			});
		}
		// ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++
		// Following code added by SHIV on 06/08/2018
		if(frm.doc.voucher_type === 'Journal Entry'){
			$.extend(filters, {
				account_type: ["!=", "Bank"]
			});
		}
		// +++++++++++++++++++++ Ver 2.0 ENDS +++++++++++++++++++++
		return { filters: filters };
	}
});


//custom Scripts
frappe.ui.form.on("Journal Entry", "onload", function(frm){
    cur_frm.set_query("select_cheque_lot", function(){
        return {
            "filters": [
                ["status", "!=", "Used"],
                ["docstatus", "=", "1"],
		["branch", "=", frm.doc.branch]
            ]
        }
    });
});

frappe.ui.form.on("Journal Entry", "select_cheque_lot", function(frm) {
     if(frm.doc.select_cheque_lot) {
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
})

/* ePayment Begins */
var create_custom_buttons = function(frm){
	if(frm.doc.docstatus == 1 && (frm.doc.voucher_type == "Bank Entry" || frm.doc.voucher_type == "Contra Entry")){
		if(!frm.doc.bank_payment || frm.doc.payment_status == 'Failed' || frm.doc.payment_status == 'Payment Failed'){
			frm.page.set_primary_action(__('Process Payment'), () => {
				frappe.model.open_mapped_doc({
					method: "erpnext.accounts.doctype.journal_entry.journal_entry.make_bank_payment",
					frm: cur_frm
				});
			});
		}
	}
}
