// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["MR Payment Report"] = {
	"filters": [
		{
			"fieldname": "branch",
			"label": ("Branch"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Branch",

		},
		{
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year"
		},
			{
				"fieldname":"month",
				"label": __("Month"),
				"fieldtype": "Select",
				"options": ['', 'Jan', 'Feb', 'Mar',  'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
			},	
		{
			"fieldname":"employee_type",
			"label": __("Employee Type"),
			"fieldtype": "Select",
			"options": [" ", "Muster Roll Employee", "Operator", "Open Air Prisoner"]
		},
				
	]
}
