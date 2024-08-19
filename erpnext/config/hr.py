from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Employee Records"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee",
					"description": _("Employee records."),
				},
				{
					"type": "doctype",
					"name": "DFG",
					"description": _("DFG records."),
				},
				{
					"type": "doctype",
					"name": "Attendance",
					"description": _("Attendance record."),
				},                                
				{
					"type": "doctype",
					"name": "Upload Attendance",
					"description":_("Upload attendance from a .csv file"),
					"hide_count": True
				},
                                {
					"type": "doctype",
					"name": "Employee Attendance Tool",
					"label": _("Employee Attendance Tool"),
					"description":_("Mark Attendance for multiple employees"),
					"hide_count": True
				},
				{
					"type": "doctype",
					"name": "Training And Development",
					"label": _("Training & Development Records"),
					"description": _("Traning & Development Master."),
				}, 
				{
					"type": "doctype",
					"name": "Meeting",
					"label": _("Meeting Management"),
					"description": _("Meeting Management."),
				},   
				{
					"type": "doctype",
					"name": "Requisition Form",
					"label": _("Employee Requisition Form"),
					"description": _("Employee Requisition Form."),
				},
				{
					"type": "doctype",
					"name": "Unfreeze OAP",
					"label": _("Unfreeze OAP"),
					"description": _("Unfreeze OAP."),
				},                
			]
		},
				
		{
                        "label": _("Muster Roll Employee/Operator/Open Air Prisoner/DFG"),
                        "icon": "icon-facetime-video",
                        "items": [
                                {
                                        "type": "doctype",
                                        "name": "Muster Roll Employee",
                                        "description": _("Muster Roll Employee Data"),
                                },
                                {
                                        "type": "doctype",
                                        "name": "Operator",
                                        "label": "Operator List",
                                        "description": _("Master Data of Operators"),
                                },
                                {
                                        "type": "doctype",
                                        "name": "Open Air Prisoner",
                                        "label": "OAP List",
                                        "description": _("Open Air Prisoner"),
                                },
											{
                                        "type": "doctype",
                                        "name": "Foreign Labourer",
                                        "label": "Foreign Labourer",
                                        "description": _("Foreign Labourer"),
                                },

				{
					"type": "doctype",
					"name": "MusterRoll Application",
					"label": "Muster Roll Application",
				},
				{
					"type": "doctype",
					"name": "Attendance Tool Others",
					"label": "Attendance Tool",
					"description": _("Attendance Tool for Others"),
				},
				{
					"type": "doctype",
					"name": "Upload Attendance Others",
					"label": "Upload Bulk Attendance for Muster Roll",
					"description": _("Attendance Tool for Others"),
				},
				{
					"type": "doctype",
					"name": "Project Overtime Tool",
					"label": "Overtime Tool",
					"description": _("Overtime Tool"),
				},
				{
					"type": "doctype",
					"name": "Upload Overtime Entries",
					"label": "Upload Overtime Entry for Muster Roll",
					"description": _("Overtime Tool for Others"),
				},
				{
					"type": "doctype",
					"name": "Process MR Payment",
					"label": "Process Payment",
					"description": _("Process Payments"),
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Attendance Register",
					"label": "Attendance Register",
					"description": _("Attendance Sheet"),
					"doctype": "Attendance Others"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Overtime Register",
					"label": "Overtime Register",
					"description": _("Overtime Register"),
					"doctype": "Overtime Entry"
				},
				{
                                        "type": "doctype",
                                        "name": "Project Muster Roll Tool",
                                        "label": "Project Muster Roll Tool",
                                        "description": _("MR Transfer tool"),
                                },
			]
		},
		{
			"label": _("Leaves and Holiday"),
			"items": [
				{
					"type": "doctype",
					"name": "Leave Application",
					"description": _("Applications for leave."),
				},
				{
					"type": "doctype",
					"name": "Leave Block List",
					"description": _("Block leave applications by department.")
				},                                
				{
					"type": "doctype",
					"name":"Leave Type",
					"description": _("Type of leaves like casual, sick etc."),
				},                                
				{
					"type": "doctype",
					"name": "Holiday List",
					"description": _("Holiday master.")
				},                                
				{
					"type": "doctype",
					"name": "Leave Allocation",
					"description": _("Allocate leaves for a period.")
				},
                                {
					"type": "doctype",
					"name": "Leave Control Panel",
					"label": _("Leave Allocation Tool"),
					"description":_("Allocate leaves for the year."),
					"hide_count": True
				},
                                {
					"type": "doctype",
					"name": "Leave Adjustment",
					"label": _("Leave Adjustment Tool"),
				},
				{
					"type": "doctype",
					"name": "Carry Forward Entry",
					"label": _("CL TO EL Converter"),
                },
				{
					"type": "doctype",
					"name": "GCE Leave Cancellation",
					"label": _("GCE Leave Cancellation"),
                },
			]
		},
		{
			"label": _("Payroll"),
			"items": [
				{
					"type": "doctype",
					"name": "Salary Structure",
					"description": _("Salary template master.")
				},                                
				{
					"type": "doctype",
					"name": "Salary Slip",
					"description": _("Monthly salary statement."),
				},
                                {
					"type": "doctype",
					"name": "Salary Increment",
					"description": _("Annual Salary Increments"),
				},
				{
					"type": "doctype",
					"name": "Process Payroll",
					"label": _("Process Payroll"),
					"description":_("Generate Salary Slips"),
					"hide_count": True
				},
                                {
					"type": "doctype",
					"name": "Process Increment",
					"label": _("Process Increments"),
					"description":_("Generate Salary Increments"),
					"hide_count": True
				},
				{
					"type": "doctype",
					"name": "Salary Component",
					"label": _("Salary Components"),
					"description": _("Earnings, Deductions and other Salary components")
				},
				{
					"type": "report",
					"name": "Employee TDS Certificate",
					"label": "Generate TDS Certificate",
					"doctype": "Salary Slip",
					"is_query_report": True
				},
			]
		},
		{
			"label": _("Expense Claims"),
			"items": [
				{
					"type": "doctype",
					"name": "Travel Authorization",
                                        "label": _("Travel Authorization"),
					"description": _("Get Travel Authorization"),
				},
				{
					"type": "doctype",
					"name": "Travel Claim",
                                        "label": _("Travel Claim"),
					"description": _("Claims for travels"),
				},
				{
					"type": "doctype",
					"name": "Vehicle Requisition",
					"description": _("Vehicle Requisition"),
				},
				{
					"type": "doctype",
					"name": "Leave Encashment",
					"description": _("Leave Encashment"),
				},
				{
					"type": "doctype",
					"name": "Leave Travel Concession",
                                        "label": _("Process LTC"),
					"description": _("LTC process"),
				},
				#{
				#	"type": "doctype",
				#	"name": "PBVA",
                                #       "label": _("Process PBVA"),
				#	"description": _("PBVA process"),
				#},
				#{
				#	"type": "doctype",
				#	"name": "Bonus",
                                #       "label": _("Process Bonus"),
				#	"description": _("Bonus Process"),
				#},
				{
					"type": "doctype",
					"name": "Overtime Application",
                                        "label": _("Overtime Application"),
					"description": _("Overtime Application"),
				},
				{
					"type": "doctype",
					"name": "Employee Benefits",
                                        "label": _("Process Employee Benefits"),
				},
				{
					"type": "doctype",
					"name": "Other Contribution",
                                        "label": _("Other Contribution"),
				}
			]
		},
		{
			"label": _("Settings"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "HR Settings",
					"description": _("Settings for HR Module")
				},
				#{
				#	"type": "doctype",
				#	"name": "Leave Encashment Settings",
				#	"description": _("Leave Encashment Settings"),
				#},                                
				#{
				#	"type": "doctype",
				#	"name": "Department Director",
				#	"label": "Department\'s Director",
				#	"description": _("Assign Directors to Departments")
				#},
				{
					"type": "doctype",
					"name": "Assign Branch",
					"label": "Branch Access Control",
					"description": _("Assign Multiple Branches to Users")
				},
				{
					"type": "doctype",
					"name": "Officiating Employee",
					"label": "Nominate Officiating",
					"description": _("Nominate officiating employees")
				},
				{
					"type": "doctype",
					"name": "Employee Grade",
					"description": _("List of Employee Grades"),
				},                                
				{
					"type": "doctype",
					"name": "Financial Institution",
					"description": _("List of Financial Institution"),
				},                                
				{
					"type": "doctype",
					"name": "Financial Schemes",
					"description": _("List of Financial Schemes"),
				},                                
			]
		},
		{
			"label": _("Salary Reports"),
			"icon": "icon-list",
			"items": [
                                {
					"type": "report",
					"is_query_report": True,
					"name": "Monthly Salary Register",
					"doctype": "Salary Slip"
				},
                                {
					"type": "report",
					"is_query_report": True,
					"name": "Loan Report",
                                        "label": _("Loan Report"),
					"doctype": "Salary Slip"
				},
                                {
					"type": "report",
					"is_query_report": True,
					"name": "SSS Report",
                                        "label": _("Salary Saving Scheme Report"),
					"doctype": "Salary Slip"
				},
                                {
					"type": "report",
					"is_query_report": True,
					"name": "PF Report",
                                        "label": _("PF Report"),
					"doctype": "Salary Slip"
				},
                                {
					"type": "report",
					"is_query_report": True,
					"name": "GIS Report",
                                        "label": _("GIS Report"),
					"doctype": "Salary Slip"
				},
                                {
					"type": "report",
					"is_query_report": True,
					"name": "Tax and Health Report",
                                        "label": _("Salary Tax & Health Contribution Report"),
					"doctype": "Salary Slip"
				},
                                {
					"type": "report",
					"is_query_report": True,
					"name": "Earning Report",
					"doctype": "Salary Slip"
				},

				{
					"type" : "report",
					"is_query_report": True,
					"name": "Salary Increment",
					"label": _("Salary Increment Report"),
					"doctype": "Salary Increment"
				},

				{
                                        "type" : "report",
                                        "is_query_report": True,
                                        "name": "Salary Payable Report",
                                        "label": _("Salary Payable Report"),
                                        "doctype": "Salary Slip"
                                },
				{
                                        "type" : "report",
                                        "is_query_report": True,
                                        "name": "Other Recoveries",
                                        "label": _("Other Recoveries"),
                                        "doctype": "Salary Slip"
                                },
				{
                                        "type" : "report",
                                        "is_query_report": True,
                                        "name": "Summarized Salary Report",
                                        "label": _("Summarized Salary Report"),
                                        "doctype": "Salary Slip",
                                },
				{
					"type" : "report",
					"is_query_report": True,
					"name": "Alimony Report",
					"label":_("Alimony Report"),
					"doctype" : "Salary Slip"
				},
                                {
                                        "type" : "report",
                                        "is_query_report": True,
                                        "name": "House Rent Report",
                                        "label": _("House Rent Report"),
                                        "doctype": "Salary Slip",
                                },
                                 {
                                        "type" : "report",
                                        "is_query_report": True,
                                        "name": "Staff Welfare Scheme",
                                        "label": _("Staff Welfare Scheme"),
                                        "doctype": "Salary Slip"
                                },
				 {
                                        "type" : "report",
                                        "is_query_report": True,
                                        "name": "Adhoc Recoveries",
                                        "label": _("Adhoc Recoveries"),
                                        "doctype": "Salary Slip"
                                },
				 {
                                        "type" : "report",
                                        "is_query_report": True,
                                        "name": "Payment Report",
                                        "label": _("Muster Roll Employee/Operator/Open Air Prisoner Payment Report"),
                                        "doctype": "Process MR Payment"
                                }


			]
		},
		{
			"label": _("Other Reports"),
			"icon": "icon-list",
			"items": [
                                {
					"type": "report",
					"is_query_report": True,
					"name": "Employee Salary Structure",
					"doctype": "Salary Structure"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employee Leave Balance",
					"doctype": "Leave Application"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Overtime Register For Normal Employees",
					"doctype": "Overtime Application"
				},
                                {
					"type": "report",
					"is_query_report": True,
					"name": "Leave Encashment Report",
                                        "label": _("Leave Encashment Report"),
					"doctype": "Leave Encashment"
				},
				{
					"type": "report",
					"name": "Employee Information",
					"doctype": "Employee"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Monthly Attendance Sheet",
					"doctype": "Attendance"
				},
                                {
					"type": "report",
					"is_query_report": True,
					"name": "Salary Tax Report",
                                        "label": "RRCO Tax Slab Details",
					"doctype": "Salary Tax"
				},
                                {
					"type": "report",
					"is_query_report": True,
					"name": "Employee Due Date Report",
					"doctype": "Employee"
				},
				{
                                        "type": "report",
                                        "name": "LTC Details",
                                        "doctype": "Leave Travel Concession"
                                },
				{
                                        "type": "report",
                                        "is_query_report": True,
                                        "name": "Travel Report",
                                        "doctype": "Travel Claim"
                                },

			]
		},
	]
