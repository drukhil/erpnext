frappe.pages['bongdeyma-dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Bongdeyma Dashboard',
		single_column: true
	});
	$(frappe.render_template('bongdeyma_dashboard')).appendTo(page.body);
}