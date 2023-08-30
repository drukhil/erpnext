frappe.pages['rba-project'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'RBA Project',
		single_column: true
	});
	$(frappe.render_template('rba_project')).appendTo(page.body);
}
