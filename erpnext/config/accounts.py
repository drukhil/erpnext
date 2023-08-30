from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
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
					"name": "Employee Benefit Type",
                                        "description": _("Employee Benefit Types e.g., Transfer and Retirement")
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
				}
			]
		},
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
					"name": "Direct Payment",
					"description": _("Direct Payment")
				},
				{
					"type": "doctype",
					"name": "Period Closing Voucher",
					"description": _("Close Balance Sheet and book Profit or Loss.")
				},
                                {
					"type": "report",
					"name": "Voucher Summary",
					"doctype": "Journal Entry",
					"is_query_report": True,
                                        "style": {"color":"red"}
				},
			]
		},
		{
			"label": _("Purchase Accounts"),
			"items": [
				{
					"type": "doctype",
					"name": "Payment Entry",
					"description": _("Bank/Cash transactions against party or for internal transfer")
				},
				{
					"type": "doctype",
					"name": "Purchase Invoice",
					"description": _("Bills raised by Suppliers.")
				},
                                {
					"type": "report",
					"name": "Payment Entry Summary",
					"doctype": "Payment Entry",
					"is_query_report": True,
				},                                
			]
		},                
		#{
		#	"label": _("Project Accounts"),
		#	"items": [
        #                        {
		#			"type": "doctype",
		#			"name": "Project Invoice",
		#			"description": _("Bills raised to Customers.")
		#		},
        #                       {
		#			"type": "doctype",
		#			"name": "Project Payment",
		#			"description": _("Payments agains Project Invoices.")
		#		},
        #                       {
		#			"type": "doctype",
		#			"name": "Deposit Work",
		#		},
		#		{	
		#			"type": "report",
		#			"name": "Deposit Work Report",
		#			"doctype": "Deposit Work",
		#			"is_query_report": True,
		#		},
		#	]
		#},
		{
			"label": _("Mechanical Accounts"),
			"items": [
				#{
				#	"type": "doctype",
				#	"name": "Hire Charge Invoice",
				#	"description": _("Hire Charge Invoice"),
				#},
				#{
				#	"type": "doctype",
				#	"name": "Mechanical Payment",
				#	"description": _("Create Payment"),
				#},
				{
					"type": "doctype",
					"name": "HSD Payment",
					"description": _("Create Payment"),
				},
			]
		},
                {
			"label": _("Imprest Management"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Imprest Type",
					"description": _("Imprest Types.")
				},
				{
					"type": "doctype",
					"name": "Imprest Receipt",
					"label": "Receipt Entry",
					"description": _("Imprest Receipt Entry.")
				},
				{
					"type": "doctype",
					"name": "Imprest Recoup",
					"label": "Recoup Entry",
					"description": _("Imprest Recoup Entry.")
				},
                                {
					"type": "report",
                                        "label": _("Report"),
					"is_query_report": True,
					"name": "Register Imprest",
					"doctype": "Imprest Receipt"
				},
			]
		},
                {
			"label": _("Tools"),
			"items": [
				{
					"type": "doctype",
					"name": "Cheque Lot",
					"label": "Create Cheque Lot",
					"description": "Creation of Cheque Lot",
					"hide_count": True
				},
				{
					"type": "doctype",
					"name": "RRCO Receipt Tool",
					"description": "Enter RRCO Receipts in Bulk",
					"hide_count": True
				},
				{
                                        "type": "doctype",
                                        "name": "RRCO Receipt Modifier",
                                        "description": "Enter RRCO Receipts Modification",
                                        "hide_count": True
                                },

                                {
					"type": "doctype",
					"name": "Salary Remittance",
					"description": "Bulk document generator for Salary Remittance",
					"hide_count": True
				},
				{
                                        "type": "doctype",
                                        "name": "TDS Remittance",
                                        "description": "TDS Remittance Tool",
                                        "hide_count": True
                                },
				{
					"type": "doctype",
					"name": "Fund Requisition",
					"description": "Fund Requisition",
					"hide_count": True
				},
			
				{
                                        "type": "doctype",
                                        "name": "Process Overtime Payment",
                                        "description": "Process Overtime Payment",
                                        "hide_count": False
                                },
								{
					"type": "doctype",
					"name": "Expense Allocation",
					"description": "Expense Allocation",
					"hide_count": True
				},
				{
					"type": "doctype",
					"name": "Cost Appropriation",
					"description": "Cost Appropriation",
					"hide_count": True
				},
			]
		},
		{
			"label": _("Taxes and Registers"),
			"items": [
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
                                        "name": "TDS Remittance",
                                        "description": "TDS Remittance Tool",
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
					"type": "report",
					"name": "TDS Deducted By Customer",
					"label": "TDS Deducted By Customer",
					"doctype": "Payment Entry",
					"is_query_report": True
				},
				 {
                                        "type": "report",
                                        "name": "Money Receipt Issued",
                                        "label": "Money Receipt Register",
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
				{
					"type": "report",
					"name": "Fund Flow Statement",
					"doctype": "GL Entry",
					"is_query_report": True
				},
				 {
				 	"type": "report",
				 	"name": "R & P Report",
				 	"label": "R & P Report",
				 	"doctype": "GL Entry",
				 	"is_query_report": True
				 },
				{
					"type": "report",
					"name": "Expenditure Statement",
					"label": "Expenditure Statement",
					"doctype": "GL Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Comparative Statement",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
                                {
					"type": "report",
					"name": "Profitability Analysis",
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
				#{
				#	"type": "report",
				#	"name": "Accounts Receivable",
				#	"doctype": "Sales Invoice",
				#	"is_query_report": True
				#},
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
				},
				{
                    "type": "report",
                    "name": "Inter Company Transaction Report",
                    "doctype": "Account",
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
				{
                                        "type": "doctype",
                                        "name": "Fixed Deposit",
                                },
                                {
                                        "type": "report",
                                        "name": "Fixed Deposit Report",
                                        "is_query_report": True,
                                        "doctype": "Fixed Deposit"
                                },
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
			"label": _("Other Reports"),
			"icon": "icon-table",
			"items": [
				#{
				#	"type": "report",
				#	"name": "Gross Profit",
				#	"doctype": "Sales Invoice",
				#	"is_query_report": True
				#},
				{
					"type": "report",
					"name": "Payment Period Based On Invoice Date",
					"is_query_report": True,
					"doctype": "Journal Entry"
				},
				#{
				#	"type": "report",
				#	"name": "Item-wise Sales Register",
				#	"is_query_report": True,
				#	"doctype": "Sales Invoice",
				#	"label":"Materialwise Sales Register"
				#},
				{
					"type": "report",
					"name": "Item-wise Purchase Register",
					"is_query_report": True,
					"doctype": "Purchase Invoice",
					"label":"Materialwise Purchase Register"
				},
				#{
				#	"type": "report",
				#	"name": "Accounts Receivable Summary",
				#	"doctype": "Sales Invoice",
				#	"is_query_report": True
				#},
				{
					"type": "report",
					"name": "Accounts Payable Summary",
					"doctype": "Purchase Invoice",
					"is_query_report": True
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
                                        "name": "Alimony Report",
                                        "label": _("AlimonyReport"),
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
					"name": "New GIS Report",
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
                                        "name": "Summarized Salary Report",
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
                                        "name": "Salary Payable Report",
                                        "label": _("Salary Payable Report"),
                                        "doctype": "Salary Slip"
                                },
				#{
                                #        "type" : "report",
                                #        "is_query_report": True,
                                #        "name": "Other Recoveries",
                                #        "label": _("Other Recoveries"),
                                #        "doctype": "Salary Slip"
                                #},
				 {
                                        "type": "report",
                                        "is_query_report": True,
                                        "name": "LTC Process Report",
                                        "label": _("LTC, PBVA and Bonus Report"),
                                        "doctype": "Leave Travel Concession"
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
				 #{
                                 #       "type" : "report",
                                 #       "is_query_report": True,
                                 #       "name": "Adhoc Recoveries",
                                 #       "label": _("Adhoc Recoveries"),
                                 #       "doctype": "Salary Slip"
                                #},
				{
                                        "type": "report",
                                        "is_query_report": True,
                                        "name": "Travel Report",
                                        "doctype": "Travel Claim"
                                },
				{
                                        "type": "report",
                                        "is_query_report": True,
                                        "name": "OT Detail Report",
                              		"doctype": "Process Overtime Payment"
                                },
				{
                                        "type": "report",
                                        "is_query_report": True,
                                        "name": "Payment Report",
					"label": "Muster Roll Employee/Operator/Open Air Prisoner Payment Report",
                                        "doctype": "Process MR Payment"
                                },


			]
		},
	]
