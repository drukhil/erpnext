// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Ticket Status"] = {
	"filters": [
		{
                        "fieldname":"branch",
                        "label": ("Branch"),
                        "fieldtype": "Link",
                        "options" : "Branch"

                },

                {
                        "fieldname":"from_date",
                        "label": ("From Date"),
                        "fieldtype": "Date",

                },

                {
                        "fieldname":"to_date",
                        "label": ("To Date"),
                        "fieldtype": "Date",

                },
		{
                        "fieldname":"module_name",
                        "label": ("Module"),
                        "fieldtype": "Link",
                        "options" : "Support Module"

                },
		{
                        "fieldname":"status",
                        "label": ("Status"),
                        "fieldtype": "Select",
                        "options" : [
					"",
					"Open", 
					"Close"
				]

                },


	]
}
