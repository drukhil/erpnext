// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Project Update Report"] = {
	"filters": [
		{
			"fieldname": "project",
			"label": ("Gyalsung Academy"),
			"fieldtype": "Link",
			"options": "Project",
			"get_query": function() {
							return {
											'doctype': "Project",
											'filters': [
															['is_group', '=', '1']
											]
							}
			},
	},
	{
			"fieldname": "activity",
			"label": ("Activity"),
			"fieldtype": "Link",
			"options": "Project",
			"get_query": function() {
							var parent_project = frappe.query_report.filters_by_name.project.get_value();
							return { 'doctype': "Project",
									'filters': [
											['is_group', '=', '0'],
											['parent_project', '=', parent_project]
					]
			}
	}
}
               

	]
}

