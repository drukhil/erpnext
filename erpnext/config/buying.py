from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Transactions"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Material Request",
					"description": _("Request for purchase."),
				},
				{
					"type": "doctype",
					"name": "Request for Quotation",
					"description": _("Request for quotation."),
				},
				{
					"type": "doctype",
					"name": "Supplier Quotation",
					"label": "Vendor Quotation",
					"description": _("Quotations received from Suppliers."),
				},
				{
					"type": "doctype",
					"name": "Purchase Order",
					"description": _("Purchase Orders given to Suppliers."),
				},
				{
					"type": "doctype",
					"name": "Purchase Receipt",
					"description": _("Goods received from Suppliers."),
				},
				{
					"type": "doctype",
					"name": "Quality Inspection",
					"description": _("Quality Inspection"),
				},
				{
					"type": "doctype",
					"name": "Purchase Invoice",
					"description": _("Bills raised by Suppliers.")
				},
				{
					"type": "doctype",
					"name": "Supplier Monitoring",
					"label": "Suppliers Monitoring Tool",
					"description": _("Bills raised by Suppliers.")
				}
			]
		},
		{
			"label": _("Master Data"),
			"items": [
				{
					"type": "doctype",
					"name": "Supplier",
					"label": "Vendor",
					"description": _("Supplier database."),
				},
				{
					"type": "doctype",
					"name": "Supplier Type",
					"label": "Vendor Type",
					"description": _("Supplier Type master.")
				},
				{
					"type": "doctype",
					"name":"Terms and Conditions",
					"label": _("Purchase Terms and Conditions Template"),
					"description": _("Template of terms or contract.")
				},
				{
					"type": "doctype",
					"name": "Annual Tender",
					"label": "Annual Tender",
					"description": _("Supplier Type master.")
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
					"name": "Material Request Pending for Purchase Order",
					"doctype": "Material Request"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Material Request Pending for Supplier Quotation",
					"doctype": "Material Request"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Material Purchase History",
					"doctype": "Item"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase History Report",
					"doctype": "Purchase Order"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Order Trends",
					"doctype": "Purchase Order"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Order Materials To Be Received",
					"doctype": "Purchase Receipt"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Receipt Trends",
					"doctype": "Purchase Receipt"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Asset Issue Report",
					"doctype": "Asset Issue Details"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Asset Balance Report",
					"doctype": "Asset Received Entries"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Registered Vendors",
					"doctype": "Supplier"
				},
				{
					"type": "page",
					"name": "purchase-analytics",
					"label": "Purchase Analytics"
				},
				{
                                        "type": "report",
                                        "is_query_report": True,
                                        "name": "MR Status Report",
                                        "doctype": "Material Request"
                },
				{
					"type": "report",
					"name": "Tax Exemption Report",
					"doctype": "Purchase Invoice",
					"is_query_report": True,
				},	


			]
		},
		{
			"label": _("Materials and Pricing"),
			"items": [
				{
					"type": "doctype",
					"name": "Item",
					"label": "Materials",
					"description": _("All Products or Services."),
				},
				{
					"type": "doctype",
					"name": "Item Group",
					"icon": "icon-sitemap",
					"label": _("Material Group"),
					"link": "Tree/Item Group",
					"description": _("Tree of Item Groups."),
				},
				{
					"type": "doctype",
					"name": "Item Sub Group",
					"label": _("Material Sub Group"),
					"description": _("Item Sub Groups."),
				},
				{
					"type": "doctype",
					"name": "Item Price",
					"label": "Material Price",
					"description": _("Multiple Item prices."),
					"route": "Report/Item Price"
				},
				{
					"type": "doctype",
					"name": "Asset Issue Details",
					"description": _("Record to whom the assets are issued"),
				}
			]
		}
	]
