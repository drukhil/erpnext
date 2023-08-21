// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Asset Depreciation', {
	refresh: function(frm) {
		create_custom_buttons(frm);
	},
	get_asset: function(frm) {
		return frappe.call({
			method: "get_asset",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("item");
				frm.refresh_fields();
			},
			freeze: true,
			freeze_message: "Fetching Utility Outstanding Amount..... Please Wait"
		});
	},
});

var create_custom_buttons = function(frm){
	if(!frm.is_new() && !frm.is_dirty()){
		if(frm.doc.docstatus == 1 && frm.doc.completed != 1){
			frm.page.set_primary_action(__('Book Depreciation'), () => {
				make_asset_depreciation(frm);
			});
		}
	}
}

var make_asset_depreciation = function(frm){
	frappe.call({
		method: "make_asset_depreciation",
		doc: frm.doc,
		callback: function(r){
			cur_frm.reload_doc();
		},
		freeze: true,
        freeze_message: "Booking Depreciation.... Please Wait",
	})
	cur_frm.reload_doc();
}
