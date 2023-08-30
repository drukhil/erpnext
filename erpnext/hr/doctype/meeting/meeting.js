// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Meeting', {
	refresh: function(frm) {
	if (frm.doc.docstatus == 0) {
		frm.add_custom_button("Notify Members", function() {
			
				frappe.call({
					method: "notify_members",
					doc: frm.doc,
					callback: function(r, rt) {
					},
					freeze: true,
					freeze_message: "Sending Emails..... Please Wait"
                });
			
		})
	}

	}
});
