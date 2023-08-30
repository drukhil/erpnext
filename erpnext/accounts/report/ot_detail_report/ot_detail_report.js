// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["OT Detail Report"] = {
	"filters": [
		{

                        "fieldname":"branch",
                        "label": ("Branch"),
                        "fieldtype": "Link",
                        "options": "Branch",
                        "width": "100",

                },
                {
                        "fieldname" : "from_date",
                        "label" : ("From Date"),
                        "fieldtype" : "Date",
			"reqd": 1, 
		        "default": frappe.datetime.year_start()
                },
                {
                        "fieldname" : "to_date",
                        "label" : ("To Date"),
                        "fieldtype" : "Date",
			"reqd": 1,
                        "default": frappe.datetime.year_end()
                },
		{

                        "fieldname":"ot_reference",
                        "label": ("OT Reference"),
                        "fieldtype": "Link",
                        "options": "Process Overtime Payment",
                        "width": "100",

                }

	]
}
