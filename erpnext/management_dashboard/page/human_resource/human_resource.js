frappe.pages['human-resource'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'HRM',
		single_column: true
	});
	$(frappe.render_template('human_resource')).appendTo(page.body);
}
