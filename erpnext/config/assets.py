from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Assets"),
			"items": [
				{
					"type": "doctype",
					"name": "Asset",
					"label": "Own Assets",
				},
                                {
					"type": "doctype",
					"name": "Asset Category",
				},
				{
					"type": "doctype",
					"name": "Asset Others",
					"label": "Assets From Other Org.",
				}
			]
		},
                {
			"label": _("Tools"),
			"items": [
				{
					"type": "doctype",
					"name": "Asset Movement",
					"description": _("Transfer an asset from one warehouse to another")
				},
				{
					"type": "doctype",
					"name": "Asset Modifier",
					"description": "Asset Addition Tool",
					"label": "Asset Addition Tool",
					"hide_count": True
				},
                                				{
					"type": "doctype",
					"name": "Bulk Asset Transfer",
				},
				{
					"type": "doctype",
					"name": "Insurance and Registration",
					"description": _("Insurance and Registration details for equipments")
				},
			]
		},
                {
			"label": _("Reports"),
			"items": [
				{
					"type": "report",
					"name": "Asset Depreciation Ledger",
					"doctype": "Asset",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Asset Depreciations and Balances",
					"doctype": "Asset",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Asset Register",
					"doctype": "Asset",
					"is_query_report": True,
				},
				{
					"type" :"report",
					"name" : "Equipment Register",
					"doctype" : "Asset",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Property Plant and Equipment",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Employee Asset Report",
					"doctype": "Asset",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Others' Asset Report",
					"doctype": "Asset Others",
					"is_query_report": True,
					"label": "Assets' From Other Org.",
				},
				{
                    "type": "report",
                    "name": "Asset Movement Register",
                    "doctype": "Asset",
                    "is_query_report": True,
                },
								{
                    "type": "report",
                    "name": "Asset Insurance Report",
                    "doctype": "Asset",
                    "is_query_report": True,
                },
			]
		},
	]
