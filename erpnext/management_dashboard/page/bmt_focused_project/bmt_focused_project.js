frappe.pages['bmt-focused-project'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'BMT Focused Project',
		single_column: true
	});
	$(frappe.render_template('bmt_focused_project')).appendTo(page.body);
}