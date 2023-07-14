frappe.pages['dfg-housing'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'DFG Housing Progress',
		single_column: true
	});
	$(frappe.render_template('dfg_housing')).appendTo(page.body);
}