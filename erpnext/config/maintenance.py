from frappe import _
def get_data():
	return [
		{
			"label": _("Master Data"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Equipment",
					"description": _("Equipment Details"),
				},
				{
					"type": "doctype",
					"name": "Equipment Category",
					"description": _("Equipment Category Details"),
				},
				{
					"type": "doctype",
					"name": "Equipment Type",
					"description": _("Equipment Type Details"),
				},
				{
					"type": "doctype",
					"name": "Equipment Model",
					"description": _("Equipment Model Details"),
				},
				{
					"type": "doctype",
					"name": "Fuelbook",
					"description": _("Fuelbook Types"),
				},
				# {
				# 	"type": "doctype",
				# 	"name": "Service",
				# 	"label": "Services List",
				# 	"description": _("Services"),
				# },
			]
		},
		{
			"label": _("Settings and Tools"),
			"icon": "icon-star",
			"items": [
				# {
				# 	"type": "doctype",
				# 	"name": "Mechanical Settings",
				# },
				{
					"type": "doctype",
					"name": "Hire Charge Parameter",
					"description": _("Hire Charge Parameter"),
				},
				# {
				# 	"type": "doctype",
				# 	"name": "Branch Fleet Manager",
				# 	"label": "Mechanical Notification Settings",
				# },
				 {
				 	"type": "doctype",
				 	"name": "Tender Hire Rate",
				 },
				{
					"type": "doctype",
					"name": "HSD Adjustment",
					"description": _("Create Payment"),
				},
			]
		},
		{
			"label": _("Maintenance Transaction"),
			"icon": "icon-star",
			"items": [
				 #{
				 #	"type": "doctype",
				 #	"name": "Break Down Report",
				 #	"description": _("Break Down Reports"),
				 #},
				 #{
				 #	"type": "doctype",
				 #	"name": "Job Card",
				 #	"description": _("Create Job Card"),
				 #},
				 #{
				 #	"type": "doctype",
				 #	"name": "Mechanical Payment",
				 #	"description": _("Create Payment"),
				 #},
			]
		},
		{
			"label": _("Fleet Transaction"),
			"icon": "icon-star",
			"items": [
				 #{
				 #	"type": "doctype",
				 #	"name": "Equipment Request",
				 #},
				#{
				#	"type": "doctype",
				#	"name": "Equipment Hiring Form",
				#	"description": _("Equipment Hiring Form"),
				#},
				{
					"type": "doctype",
					"name": "Vehicle Logbook",
					"description": _("Vehicle Logbook"),
				},
				#{
				#	"type": "doctype",
				#	"name": "Hire Charge Invoice",
				#	"description": _("Hire Charge Invoice"),
				#},
				# {
				# 	"type": "doctype",
				# 	"name": "Mechanical Payment",
				# 	"description": _("Create Payment"),
				# },
				#{
				#	"type": "doctype",
				#	"name": "Equipment Hiring Extension",
				#	"description": _("Equipment Hiring Extension"),
				#},
			]
		},
		{
			"label": _("POL Transaction"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "POL",
					"label": "Receive POL",
					"description": _("Receive POL"),
				},
				{
					"type": "doctype",
					"name": "Issue POL",
					"label": "Issue POL",
					"description": _("Issue POL"),
				},
				{
					"type": "doctype",
					"name": "Equipment POL Transfer",
				},
				{
					"type": "doctype",
					"name": "HSD Payment",
					"description": _("Create Payment"),
				},
			]
		},
		{
			"label": _("Maintenance Reports"),
			"icon": "icon-star",
			"items": [
				# {
				# 	"type": "report",
				# 	"is_query_report": True,
				# 	"name": "Job Card Imprest Report",
				# 	"doctype": "Job Card"
				# },
				# {
				# 	"type": "report",
				# 	"is_query_report": True,
				# 	"name": "Workshop Progress Report",
				# 	"doctype": "Job Card"
				# },
			]
		},
		{
			"label": _("Fleet Reports"),
			"icon": "icon-star",
			"items": [
				# {
				# 	"type": "report",
				# 	"is_query_report": True,
				# 	"name": "Equipment Hire Report",
				# 	"doctype": "Hire Charge Invoice"
				# },
				# {
				# 	"type": "report",
				# 	"is_query_report": True,
				# 	"name": "Party Wise Billing",
				# 	"doctype": "Hire Charge Invoice"
				# },
				{
					"type": "report",
					"is_query_report": True,
					"name": "HSD Consumption Report",
					"doctype": "Vehicle Logbook"
				},
				 {
				 	"type": "report",
				 	"is_query_report": True,
				 	"name": "Equipment Expense Report",
				 	"doctype": "Equipment"
				 },
				# {
				# 	"type": "report",
				# 	"is_query_report": True,
				# 	"name": "Equipment Performance Report",
				# 	"doctype": "Equipment"
				# },
				 {
				 	"type": "report",
				 	"is_query_report": True,
				 	"name": "Equipment Status",
				 	"label": "Equipment Status Report",
				 	"doctype": "Equipment"
				 },
				# {
				# 	"type": "report",
				# 	"is_query_report": True,
				# 	"name": "Equipment Status Report",
				# 	"label": "Equipment Status (Details)",
				# 	"doctype": "Equipment"
				# },
			]
		},
		{
			"label": _("POL Reports"),
			"icon": "icon-star",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "POL Ledger",
					"doctype": "POL Entry"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "POL Issue Report",
					"doctype": "Consumed POL"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "POL Balance Report",
					"doctype": "POL"
				},
				{
                                        "type": "report",
                                        "is_query_report": True,
                                        "name": "POL Receive Report",
                                        "doctype": "POL"
                                },

			]
		},
	]
