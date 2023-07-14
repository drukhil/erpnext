from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Projects"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Design",
					"description": _("Design master."),
				},
				{
					"type": "doctype",
					"name": "Project",
					"description": _("Project master."),
				}
			]
		},
                {
                        "label": _("Transactions"),
                        "icon": "icon-pencil",
                        "items": [
                                # {
                                #         "type": "doctype",
                                #         "name": "Project Advance",
                                #         "description": _("Project Advances."),
                                # },
                                # {
                                #         "type": "doctype",
                                #         "name": "Project Invoice",
                                #         "description": _("Project Invoices."),
                                # },
                                # {
                                #         "type": "doctype",
                                #         "name": "Project Payment",
                                #         "description": _("Project Payments."),
                                # },
                        ]
                },
		
		
		{
			"label": _("Reports"),
			"icon": "icon-list",
			"items": [
                        {       
                                       "type": "report",
                                       "is_query_report": True,
                                       "name": "Design Progress Report",
                                       "doctype": "Design"
                                },
							    {
					"type": "report",
					"is_query_report": True,
					"name": "Project Progress Report",
					"doctype": "Project"
				},
				{       
                                        "type": "report",
                                        "is_query_report": True,
                                        "name": "Project Progress Graphs",
                                        "doctype": "Project"
                                }, 

			]
		},

		{
			"label": _("Dashboard"),
			"icon": "icon-list",
			"items": [
                         {
                                        "type": "page",
                                        "name": "design-management",
                                        "label": "Design Management"
                                },
				{
                                        "type": "page",
                                        "name": "project-management",
                                        "label": "Project Management"
                                },
				{
                                        "type": "page",
                                        "name": "bmt-focused-project",
                                        "label": "BMT Focused Activity"
                                },
				# {
                #                         "type": "page",
                #                         "name": "design-management",
                #                         "label": "Design Management"
                #                 },
								{
                                        "type": "page",
                                        "name": "dessung-project",
                                        "label": "Priority Activity"
                                },
                                	{
                                        "type": "page",
                                        "name": "rba-project",
                                        "label": "RBA Project"
                                },

			]
		},
	]
