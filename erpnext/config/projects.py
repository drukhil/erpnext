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
					"name": "Project",
					"description": _("Project master."),
				},
				{
					"type": "doctype",
					"name": "Design",
					"description": _("Design master."),
				},
				{
					"type": "doctype",
					"name": "DFG Housing",
					"description": _("DFG Housing."),
				},
				{
					"type": "doctype",
					"name": "Home Security Skilling",
					"description": _("HSS"),
				},
				{
					"type": "doctype",
					"name": "RBA Project",
					"description": _("RBA Project."),
				},
				{
                                        "type": "doctype",
                                        "name": "Project Category",
                                        "description": _("Project Category."),
                                },
				{
                                        "type": "doctype",
                                        "name": "Project Sub Category",
                                        "description": _("Project Sub Category."),
                                },
				{
                                        "type": "doctype",
                                        "name": "Task Category",
                                        "description": _("Task Category."),
                                },
				{
                                        "type": "doctype",
                                        "name": "Task Sub Category",
                                        "description": _("Task Sub Category."),
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
			"label": _("Manpower Management"),
			"icon": "icon-facetime-video",
			"items": [
				{
					"type": "doctype",
					"name": "Muster Roll Employee",
					"description": _("Muster Roll Employee Data"),
				},
				{
					"type": "doctype",
					"name": "Attendance Tool Others",
					"label": "Attendance Tool for Muster Roll",
					"description": _("Attendance Tool for Others"),
				},
				#{
				#	"type": "doctype",
				#	"name": "Attendance Tool Others",
				#	"label": "Attendance Tool for GEP & MR",
				#	"description": _("Attendance Tool for Others"),
				#},
				{
					"type": "doctype",
					"name": "Upload Attendance Others",
					"label": "Upload Bulk Attendance for MR",
					"description": _("Attendance Tool for Others"),
				},
				{
					"type": "doctype",
					"name": "Project Overtime Tool",
					"label": "Overtime Tool for MR",
					"description": _("Overtime Tool"),
				},
				{
					"type": "doctype",
					"name": "Upload Overtime Entries",
					"label": "Upload Overtime Entry for MR",
					"description": _("Overtime Tool for Others"),
				},
				{
					"type": "doctype",
					"name": "Process MR Payment",
					"label": "Process Payment for MR",
					"description": _("Process Payments for Project Muster Roll"),
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Attendance Register",
					"label": "Attendance Register for Muster Roll",
					"description": _("Attendance Sheet"),
					"doctype": "Attendance Others"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Overtime Register",
					"label": "Overtime Register for Muster Roll",
					"description": _("Overtime Register"),
					"doctype": "Overtime Entry"
				},
			]
		},
		{
			"label": _("Project Tools"),
			"icon": "icon-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Attendance Register",
					"label": "Attendance Register for MR",
					"description": _("Attendance Sheet"),
					"doctype": "Attendance Others"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Overtime Register",
					"label": "Overtime Register for MR",
					"description": _("Overtime Register"),
					"doctype": "Overtime Entry"
				},
				{
					"type": "doctype",
					"name": "Project Muster Roll Tool",
					"label": "Assign Muster Roll To Projects",
					"description": _("Project Muster Roll Tool"),
				},
				{
					"type": "doctype",
					"name": "MusterRoll Application",
					"label": "Muster Roll Application",
				},
			]
		},
		{
			"label": _("Reports"),
			"icon": "icon-list",
			"items": [
                                {
					"type": "report",
					"is_query_report": True,
					"name": "Project Progress Report",
					"doctype": "Project"
				},
				{       
                                        "type": "report",
                                        "is_query_report": True,
                                        "name": "Project Progress Graph",
                                        "doctype": "Project"
                                }, 

				{       
                                       "type": "report",
                                       "is_query_report": True,
                                       "name": "Design Progress Report",
                                       "doctype": "Design"
                                }, 
			]
		},
	]
