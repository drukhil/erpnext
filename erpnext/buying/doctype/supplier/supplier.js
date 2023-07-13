// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Supplier", {
	before_load: function(frm) {
		frappe.setup_language_field(frm);
	},
	refresh: function(frm) {
		if(frappe.defaults.get_default("supp_master_name")!="Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		if(frm.doc.__islocal){
	    	hide_field(['address_html','contact_html']);
			erpnext.utils.clear_address_and_contact(frm);
		}
		else {
		  	unhide_field(['address_html','contact_html']);
			erpnext.utils.render_address_and_contact(frm);
		}
		/* ePayment Beings, added by SHIV on 2021/06/11 */
		enable_disable(frm);
		/* ePayment Ends*/
	},
	/* ePayment Beings, added by SHIV on 2021/06/11 */
	bank_name_new: function(frm){
		enable_disable(frm);
		cur_frm.set_value('bank_branch', null);
	},
	/* ePayment Ends*/
	// for consolidation purpose
	inter_company: (frm)=>{
		frm.toggle_reqd('company_code',frm.doc.inter_company);
		if (!frm.doc.inter_company){
			frm.set_value('company_code','')
			frm.set_value('company_name','')
		}
	},
});

cur_frm.fields_dict['default_price_list'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{'buying': 1}
	}
}

cur_frm.fields_dict['accounts'].grid.get_field('account').get_query = function(doc, cdt, cdn) {
	var d  = locals[cdt][cdn];
	return {
		filters: {
			'account_type': 'Payable',
			'company': d.company,
			"is_group": 0
		}
	}
}

/* ePayment Begins */
// cur_frm.fields_dict['bank_branch'].get_query = function(doc, dt, dn) {
// 	return {
// 		filters:{
// 		 	"financial_institution": doc.bank_name_new
// 	 	}
// 	}
// }

var enable_disable = function(frm){
	if(frm.doc.bank_name_new){
		cur_frm.toggle_display(["bank_branch", "bank_account_type"], frm.doc.bank_name_new != "INR");
		cur_frm.toggle_reqd(["bank_branch", "bank_account_type"], frm.doc.bank_name_new != "INR");

		cur_frm.toggle_display(["inr_bank_code", "inr_purpose_code"], frm.doc.bank_name_new == "INR");
		cur_frm.toggle_reqd(["inr_bank_code", "inr_purpose_code"], frm.doc.bank_name_new == "INR");
	}
}
/* ePayment Ends */

