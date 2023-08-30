frappe.pages['design-management'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Design Management',
		single_column: true
	});
	$(frappe.render_template('design_management')).appendTo(page.body);
}
