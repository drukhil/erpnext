// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Design Progress Report"] = {
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
                        "label": ("Design"),
                        "fieldtype": "Link",
                        "options": "Design",
                        "get_query": function() {
                                var parent_project = frappe.query_report.filters_by_name.project.get_value();
                                return { 'doctype': "Design",
                                        'filters': [
                                                
                                                ['parent_project', '=', parent_project]
                        ]
                }
        }
                
                },

		// {
                //         "fieldname": "status",
                //         "label": __("Status"),
                //         "fieldtype": "Select",
                //         "options": ['', 'Planning', 'Ongoing', 'Completed', 'Cancelled']
                // }
]}
