frappe.pages['asset-management'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Khotokha Dashboard',
		single_column: true
	});
	$(frappe.render_template('asset_management')).appendTo(page.body);
}
