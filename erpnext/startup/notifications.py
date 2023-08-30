# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

def get_notification_config():
	return { "for_doctype":
		{
			"Issue": {"status": "Open"},
			"Warranty Claim": {"status": "Open"},
			"Task": {"status": "Overdue", "is_group": 0},
			"Project": {
                                "status": "Ongoing"
                        },
			#"Item": {"total_projected_qty": ("<", 0)},
			
			"Contact": {"status": "Open"},
			"Opportunity": {"status": "Open"},
			"Quotation": {"docstatus": 0},
			"Sales Order": {
				"status": ("not in", ("Completed", "Closed")),
				"docstatus": ("<", 2)
			},
			"Journal Entry": {"docstatus": 0},
			"Cost Appropriation": {"docstatus": 0},
			"Sales Invoice": { "outstanding_amount": (">", 0), "docstatus": ("<", 2) },
			"Purchase Invoice": {"docstatus": 0},
			"Leave Application": {"status": "Open"},
			"Expense Claim": {"approval_status": "Draft"},
			"Job Applicant": {"status": "Open"},
			"Delivery Note": {"docstatus": 0},
			"Stock Entry": {"docstatus": 0},
			"Material Request": {
				"docstatus": 0,
				"status": ("not in", ("Stopped",)),
				"per_ordered": ("<", 100)
			},
			"Request for Quotation": { "docstatus": 0 },
			"Supplier Quotation": {"docstatus": 0},
			"Purchase Order": {
				"docstatus": 0,
			},
			"Purchase Receipt": {"docstatus": 0},
			"Production Order": { "status": ("in", ("Draft", "Not Started", "In Process")) },
			"BOM": {"docstatus": 0},
			"Timesheet": {"status": "Draft"},
			"Travel Authorization": {
				"docstatus": 0,
				"document_status": ("not in", ("Rejected"))
			},
			"Travel Claim": {
				"docstatus": 0,
				"claim_status": ("not in", ("Rejected by HR", "Rejected by Supervisor"))
			},
			"MusterRoll Application": {"docstatus" :0},
			"Leave Encashment": {"docstatus": 0},
			"Break Down Report": {"docstatus": 0},
			"Job Card": {"docstatus": 0},
                        "BOQ": {"docstatus": 0},
                        "BOQ Adjustment": {"docstatus": 0},
                        "MB Entry": {"docstatus": 0},
                        "Project Advance": {"docstatus": 0},
                        "Project Invoice": {"status": ("in", ("Draft", "Unpaid"))},
                        "Project Payment": {"docstatus": 0},
                        "Cash Journal Entry": {"docstatus": 0},
                        "Equipment Hiring Form": {"docstatus": 0},
                        "Vehicle Logbook": {"docstatus": 0},
                        "Hire Charge Invoice": {"docstatus": 0},
                        "Mechanical Payment": {"docstatus": 0},
                        "Equipment Hiring Extension": {"docstatus": 0},
                        "Overtime Application": {"docstatus": 0},
                        "POL": {"docstatus": 0},
                        "Issue POL": {"docstatus": 0},
                        "Project Sales": {"docstatus": 0},
                        "Process MR Payment": {"docstatus": 0},
                        "PBVA": {"docstatus": 0},
                        "Leave Travel Concession": {"docstatus": 0},
                        "Bonus": {"docstatus": 0},
                        "Direct Payment": {"docstatus": 0},
                        "Budget": {"docstatus": 0},
                        "Revenue Target": {"docstatus": 0},
                        "Payment Entry": {"docstatus": 0},
			"Imprest Receipt": {"docstatus": 0},
                        "Imprest Recoup" : {"docstatus": 0},
			"SWS Application" : {"docstatus": 0},
			"HSD Payment" : {"docstatus": 0},
			"Equipment POL Transfer" : {"docstatus": 0},
            "Equipment Request" : {"percent_completed": ("<", "100"), "docstatus": 1},
            "Revenue Target Adjustment": {"docstatus": 0},
			"Employee Benefits" : {"docstatus": 0},
			"Asset Modifier": {"docstatus": 0},
			"Asset Movement": {"docstatus": 0},
			"Bulk Asset Transfer": {"docstatus": 0},
			"Supplementary Budget": {"docstatus": 0},
			"Budget Reappropiation": {"docstatus": 0},
			"TDS Remittance" : {"docstatus" : 0},
			"Asset Issue Details" : {"docstatus" : 0},
			"Vehicle Requisition" : {"docstatus" : 0},
			"Process Overtime Payment" : {"docstatus" : 0},
		}
	}
