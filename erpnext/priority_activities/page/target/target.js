frappe.pages['target'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Target',
		single_column: true
	});
	$(frappe.render_template('target')).appendTo(page.body);
}