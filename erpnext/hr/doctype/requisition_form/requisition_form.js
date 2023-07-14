// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


cur_frm.add_fetch('employee', 'designation', 'designation');
cur_frm.add_fetch('employee','department','department');

cur_frm.add_fetch('employee', 'branch', 'branch');

frappe.ui.form.on('Requisition Form', {
	refresh: function(frm) {

	}
});
