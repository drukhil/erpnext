frappe.pages['mechanical-services'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Fleet Management',
		single_column: true
	});
	$(frappe.render_template('mechanical_services')).appendTo(page.body);
}
