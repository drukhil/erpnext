frappe.pages['project-management'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Project Management',
		single_column: true
	});
	$(frappe.render_template('project_management')).appendTo(page.body);
}
