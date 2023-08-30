frappe.pages['pemathang-dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Pemathang Dashboard',
		single_column: true
	});
	$(frappe.render_template('pemathang_dashboard')).appendTo(page.body);
}