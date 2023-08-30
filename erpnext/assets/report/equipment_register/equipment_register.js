// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Equipment Register"] = {
	"filters": [
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch"
		},
		{
			"fieldname": "owner",
			"label": __("Owned By"),
			"fieldtype": "Select",
			"options": ['', "Own", "Others"]
		},

		//{
		//	"fieldname": "include_disabled",
		//	"label": __("Include Disabled"),
		//	"fieldtype": "Check",
		//	"default": 0,
		//},

	]
}
