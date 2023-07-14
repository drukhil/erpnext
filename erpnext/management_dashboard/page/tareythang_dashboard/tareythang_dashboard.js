
	frappe.pages['tareythang-dashboard'].on_page_load = function(wrapper) {
		var page = frappe.ui.make_app_page({
			parent: wrapper,
			title: 'Tareythang Dashboard',
			single_column: true
		});
		$(frappe.render_template('tareythang_dashboard')).appendTo(page.body);
	}
	