// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transport Request', {
	refresh: function(frm) {
		custom.apply_default_settings(frm);
		check_if_boulder_t(frm);
		if(frm.doc.docstatus == 1 && !frm.doc.transporter) {
			cur_frm.add_custom_button(__('Change to Draft'), function(){
				return frappe.call({
					method: "change_to_draft",
					doc: cur_frm.doc,
					callback: function(r, rt){
						frm.reload_doc();
					}
				});
			});
		}
	},
	onload: function(frm) {
		cur_frm.set_query("vehicle_capacity",function(){
			return {
				"filters": [
					["is_crm_item", "=", "1"]
				]
			}
		});
	},
	"vehicle_owner": function(frm) {
		if(frm.doc.vehicle_owner == "Self"){
			frappe.model.get_value("User", {"name":frm.doc.user}, "login_id", function(d){
				frm.set_value("owner_cid", d.login_id);
			});
		}
	},
	is_boulder: function(frm){
			check_if_boulder_t(frm);
	}
});

//below method added by Kinley Dorji to check boulder transport request on 2020/12/15
var check_if_boulder_t = function(frm){
	if(cur_frm.doc.is_boulder == 1){
		cur_frm.toggle_reqd("vehicle_capacity",0)
		cur_frm.toggle_reqd("owner_cid",0)
		cur_frm.toggle_reqd("vehicle_owner",0)
	}
	else{
		cur_frm.toggle_reqd("vehicle_capacity",1)
		cur_frm.toggle_reqd("owner_cid",1)
		cur_frm.toggle_reqd("vehicle_owner",1)
	}
}
/*cur_frm.fields_dict['items'].grid.get_field('crm_branch').get_query = function(doc, cdt, cdn) {
        return {
                filters:[
                        ['CRM Branch Setting', 'has_common_pool', '=', 1]
                ]
        }
} */

