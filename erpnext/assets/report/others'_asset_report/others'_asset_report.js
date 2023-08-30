// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Others' Asset Report"] = {
	"filters": [
		{
                        "fieldname": "branch",
                        "label": __("Branch"),
                        "fieldtype": "Link",
                        "options": "Branch"
                },
                //{
                //        "fieldname": "from_date",
                //        "label": __("From Date"),
                //        "fieldtype": "Date",
                //        "default": frappe.defaults.get_user_default("year_start_date"),
                //        "reqd": 1 
                //},
		//{
                //        "fieldname": "to_date",
                //        "label": __("To Date"),
                //        "fieldtype": "Date",
                //        "default": frappe.defaults.get_user_default("year_start_date"),
                //        "reqd": 1 
                //},
		{
                        "fieldname": "owner",
                        "label": __("Owner"),
                        "fieldtype": "Link",
                        "options": "Organization"
                },
		{
                        "fieldname": "custodian",
                        "label": __("Custodian"),
                        "fieldtype": "Link",
                        "options": "Employee"
                },
                //{
               //       "fieldname": "include_disabled",
               //         "label": __("Include Disabled"),
                //        "fieldtype": "Check",
                //        "default": 0,
               // },

	]
}
