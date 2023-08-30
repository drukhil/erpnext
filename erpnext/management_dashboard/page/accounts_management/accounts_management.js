frappe.pages['accounts-management'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Accounts & Finance',
		single_column: true
	});
	$(frappe.render_template('accounts_management')).appendTo(page.body);
}
