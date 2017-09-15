from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Accounts"),
			"items": [
				{
					"type": "doctype",
					"name": "Journal Entry",
					"description": _("Accounting journal entries.")
				},
				{
					"type": "doctype",
					"name": "Payment Entry",
					"description": _("Bank/Cash transactions against party or for internal transfer")
				},
				{
					"type": "doctype",
					"name": "Sales Invoice",
					"description": _("Bills raised to Customers.")
				},
				{
					"type": "doctype",
					"name": "Purchase Invoice",
					"description": _("Bills raised by Suppliers.")
				},
				{
					"type": "doctype",
					"name": "Direct Payment",
					"description": _("Direct Payment")
				},
				{
					"type": "doctype",
					"name": "Period Closing Voucher",
					"description": _("Close Balance Sheet and book Profit or Loss.")
				},
			]
		},
		{
			"label": _("Company"),
			"items": [
				{
					"type": "doctype",
					"name": "Company",
					"description": _("Company (not Customer or Supplier) master.")
				},
				{
					"type": "doctype",
					"name": "Account",
					"icon": "icon-sitemap",
					"label": _("Chart of Accounts"),
					"route": "Tree/Account",
					"description": _("Tree of financial accounts."),
				},
				{
					"type": "doctype",
					"name": "Cost Center",
					"icon": "icon-sitemap",
					"label": _("Chart of Cost Centers"),
					"route": "Tree/Cost Center",
					"description": _("Tree of financial Cost Centers."),
				},
				{
					"type": "doctype",
					"name": "Branch",
					"description": _("List of Branches"),
				},                                
			]
		},
		{
			"label": _("Project Accounts"),
			"items": [
                                {
					"type": "doctype",
					"name": "Project Invoice",
					"description": _("Bills raised to Customers.")
				},
                                {
					"type": "doctype",
					"name": "Project Payment",
					"description": _("Payments agains Project Invoices.")
				},
			]
		},
		{
			"label": _("Mechanical Accounts"),
			"items": [
				{
					"type": "doctype",
					"name": "Hire Charge Invoice",
					"description": _("Hire Charge Invoice"),
				},
				{
					"type": "doctype",
					"name": "Job Card",
					"label": "Job Card Invoice",
					"description": _("Create Job Card"),
				},
				{
					"type": "doctype",
					"name": "Mechanical Payment",
					"description": _("Create Payment"),
				},
			]
		},
		{
			"label": _("Asset Management"),
			"items": [
				{
					"type": "doctype",
					"name": "Asset",
				},
				{
					"type": "doctype",
					"name": "Asset Modifier Tool",
					"description": "Asset Addition Tool",
					"label": "Asset Addition Tool",
					"hide_count": True
				},
				{
					"type": "doctype",
					"name": "Asset Category",
				},
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
					"type": "doctype",
					"name": "Asset Movement",
					"description": _("Transfer an asset from one warehouse to another")
				},
				{
					"type": "report",
					"name": "Asset Register",
					"doctype": "Asset",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Property Plant & Equipment",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "doctype",
					"name": "Insurance and Registration",
					"description": _("Insurance and Registration details for equipments")
				},
				{
					"type": "report",
					"name": "Employee Asset Report",
					"doctype": "Asset",
					"is_query_report": True,
				},
			]
		},
		{
			"label": _("Taxes and Registers"),
			"items": [
				{
					"type": "report",
					"name": "Sales Register",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Purchase Register",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Cheque Register",
					"doctype": "Journal Entry",
					"is_query_report": True
				},
				{
					"type": "doctype",
					"name": "Cheque Lot",
					"label": "Create Cheque Lot",
					"description": "Creation of Cheque Lot",
					"hide_count": True
				},
				{
					"type": "report",
					"name": "TDS Certificate",
					"label": "Generate TDS Certificate",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "TDS Challen",
					"label": "Generate TDS Challan",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "doctype",
					"name": "RRCO Receipt Tool",
					"description": "Enter RRCO Receipts in Bulk",
					"hide_count": True
				},
				{
					"type": "report",
					"name": "TDS Deducted By Customer",
					"label": "TDS Deducted By Customer",
					"doctype": "Payment Entry",
					"is_query_report": True
				},
			]
		},
		{
			"label": _("Accounting Statements"),
			"items": [
				{
					"type": "report",
					"name": "Statement of Trial Balance",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Statement of Financial Position",
					"doctype": "GL Entry",
					"is_query_report": True
				},
				#{
				#	"type": "report",
				#	"name": "Statement of Cash Flow",
				#	"doctype": "GL Entry",
				#	"is_query_report": True
				#},
				{
					"type": "report",
					"name": "Statement of Comprehensive Income",
					"doctype": "GL Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Comparative Statement",
					"doctype": "GL Entry",
					"is_query_report": True,
				}
			]
		},
		{
			"label": _("General Reports"),
			"items": [
				{
					"type": "report",
					"name":"General Ledger",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Accounts Receivable",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Accounts Payable",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Party Wise Ledger",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Intra Company Report",
					"doctype": "GL Entry",
					"is_query_report": True,
				}
			]
		},
		{
			"label": _("Bank Accounting"),
			"items": [
                		{
					"type": "doctype",
					"name": "Upload BRS Entries",
                    			"label": _("Upload BRS Data"),
					"description": _("Upload bank payment dates.")
				},
                		{
					"type": "doctype",
					"name": "Bank Reconciliation",
                    			"label": _("Update Bank Transaction Dates"),
					"description": _("Update bank payment dates with journals.")
				},
                		{
					"type": "report",
					"name": "Bank Reconciliation Statement",
                			"is_query_report": True,
					"doctype": "Journal Entry"
				},
                		{
					"type": "report",
					"name": "Bank Clearance Summary",
                    			"is_query_report": True,
					"doctype": "Journal Entry"
				},
                		{
					"type": "doctype",
					"name": "Bank Guarantee",
				},
                		{
					"type": "report",
					"name": "Bank Guarantee Report",
                    			"is_query_report": True,
					"doctype": "Bank Guarantee"
				},
			]
		},
		{
			"label": _("Budget"),
			"items": [
				{
					"type": "doctype",
					"name": "Budget",
					"description": _("Define budget for a financial year.")
				},
				{
					"type": "report",
					"name": "Budget Consumption Report",
					"is_query_report": True,
					"doctype": "GL Entry"
				},
				{
					"type": "doctype",
					"name": "Supplementary Budget Tool",
					"description": "Supplementary Budget",
					"hide_count": True
				},
				{
					"type": "doctype",
					"name": "Budget Reappropriation Tool",
					"description": "Budget Reappropriation",
					"hide_count": True
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Supplementary Budget Report",
					"doctype": "Supplementary Details"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Budget Reappropriation Report",
					"doctype": "Reappropriation Details"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Committed Budget Report",
					"doctype": "Committed Budget"
				}
			]
		},
		{
			"label": _("Setup"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Fiscal Year",
					"description": _("Financial / accounting year.")
				},
				{
					"type": "doctype",
					"name": "Currency",
					"description": _("Enable / disable currencies.")
				},
				{
					"type": "doctype",
					"name": "Currency Exchange",
					"description": _("Currency exchange rate master.")
				},
				{
					"type": "doctype",
					"name":"Mode of Payment",
					"description": _("e.g. Bank, Cash, Credit Card")
				},
				{
					"type": "report",
					"name": "Exchange Report",
					"label": "Exchange Rate History",
					"doctype": "Exchange Rate History",
					"is_query_report": True
				},
			]
		},
		{
			"label": _("Account Settings"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Accounts Settings",
					"description": _("Default settings for accounting transactions.")
				},
				{
					"type": "doctype",
					"name": "HR Accounts Settings",
					"description": _("Account Settings for HR Accounting")
				},
				{
					"type": "doctype",
					"name": "Maintenance Accounts Settings",
					"description": _("Account Settings for Maintenance Accounting")
				},
				{
					"type": "doctype",
					"name": "Projects Accounts Settings",
					"description": _("Account Settings for Projects Accounting")
				},
				{
					"type": "doctype",
					"name": "Sales Accounts Settings",
					"description": _("Account Settings for Sales Accounting")
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
				}
			]
		},
		{
			"label": _("Other Reports"),
			"icon": "icon-table",
			"items": [
				{
					"type": "report",
					"name": "Gross Profit",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Payment Period Based On Invoice Date",
					"is_query_report": True,
					"doctype": "Journal Entry"
				},
				{
					"type": "report",
					"name": "Item-wise Sales Register",
					"is_query_report": True,
					"doctype": "Sales Invoice",
					"label":"Materialwise Sales Register"
				},
				{
					"type": "report",
					"name": "Item-wise Purchase Register",
					"is_query_report": True,
					"doctype": "Purchase Invoice",
					"label":"Materialwise Purchase Register"
				},
				{
					"type": "report",
					"name": "Accounts Receivable Summary",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Accounts Payable Summary",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
			]
		},
	]
