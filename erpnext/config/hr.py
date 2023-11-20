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
                                        "name": "Training Records",
                                        "description":_("Training And Development"),
                                        "label": _("Training And Development")
                                },
				 {
                                        "type": "doctype",
                                        "name": "Salary Advance",
                                        "description":_("Salary Advance"),
                                        "label": _("Salary Advance Application")
                                },
				{	
					"type": "doctype",
                                        "name": "SWS Application",
                                        "description":_("SWS Application"),
                                        "label": _("SWS Application")
				},
			]
		},
		{
			"label": _("MR & DES Management"),
			"icon": "icon-facetime-video",
			"items": [
				{
					"type": "doctype",
					"name": "DES Employee",
					"label": "DES Employee",
					"description": _("DES Employee records."),
				},
				{
					"type": "doctype",
					"name": "Muster Roll Employee",
					"description": _("Muster Roll Employee Data"),
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
					"label": "Upload Bulk Attendance",
					"description": _("Attendance Tool for Others"),
				},
				{
					"type": "doctype",
					"name": "Project Overtime Tool",
					"label": "Overtime Tool",
					"description": _("Overtime Tool for MR and GEP"),
				},
				{
					"type": "doctype",
					"name": "Upload Overtime Entries",
					"label": "Upload Overtime Entry",
					"description": _("Overtime Tool for Others"),
				},
				{
					"type": "doctype",
					"name": "Process MR Payment",
					"label": "Process Payment",
					"description": _("Process Payments for Project Muster Roll"),
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
					"name": "Request EL Allocation",
					"label": _("Request EL Allocation"),
				},
				{
                                        "type": "doctype",
                                        "name": "Merge CL To EL",
                                        "label": _("Merge CL Balances To EL"),
                                }
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
				{
					"type": "report",
					"name": "PBVA & Bonus Report",
					"label": "PBVA & Bonus Report",
					"doctype": "Salary Slip",
					"is_query_report": True
				}
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
					"name": "Leave Encashment",
					"description": _("Leave Encashment"),
				},
				{
					"type": "doctype",
					"name": "Leave Travel Concession",
                                        "label": _("Process LTC"),
					"description": _("LTC process"),
				},
				{
					"type": "doctype",
					"name": "PBVA",
                                        "label": _("Process PBVA"),
					"description": _("PBVA process"),
				},
				{
					"type": "doctype",
					"name": "Bonus",
                                        "label": _("Process Bonus"),
					"description": _("Bonus Process"),
				},
				{
					"type": "doctype",
					"name": "Salary Arrear Payment",
                    "label": _("Salary Arrear Payment"),
					"description": _("Salary Arrear Payment"),
				},
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
					"description": _("Other Contribution"),
				},
                                {
					"type": "doctype",
					"name": "Hall Booking",
                                        "label": _("Hall Booking Invoice"),
					"description": _("Hall Booking"),
				},
				
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
					"name": "Employee PMS Report",
					"is_query_report": True,
					"doctype": "Employee"
				},
				{
					"type": "report",
					"name": "Employee Benefits Report",
					"is_query_report": True,
					"doctype": "Employee Benefits"
				},
				{
					"type": "report",
					"name": "DES Employee Report",
					"doctype": "DES Employee"
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
						{
				    "type": "report",
							"is_query_report": True,
				    "name": "Hall Booking Report",
				    "doctype": "Hall Booking"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Over Time Report",
					"doctype": "Overtime Application List"
				},
				{
                    "type": "report",
                    "is_query_report": True,
                    "name": "Salary Advance Report",
                    "doctype": "Salary Advance"
                },
				{
					"type": "report",
					"is_query_report": True,
					"name": "MR Payment",
					"label": "MR Payment",
					"doctype": "Process MR Payment"
				},
        
				{
					"type": "report",
					"is_query_report": True,
					"doctype": "Training Records",
					"name": "Training and Development Report",
				}
			]
		},
	]
