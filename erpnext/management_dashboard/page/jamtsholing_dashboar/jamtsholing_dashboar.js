frappe.pages['jamtsholing-dashboar'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Jamtsholing Dashboard',
		single_column: true
	});
	$(frappe.render_template('jamtsholing_dashboar')).appendTo(page.body);
}