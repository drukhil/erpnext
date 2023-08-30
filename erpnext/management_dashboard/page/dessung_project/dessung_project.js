frappe.pages['dessung-project'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Piority Activities Progress',
		single_column: true
	});
	$(frappe.render_template('dessung_project')).appendTo(page.body);
}
