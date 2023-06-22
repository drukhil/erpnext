// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Material Purchase History Report"] = {
	"filters": [
		{
			"fieldname":"from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
			
		},
		{
			"fieldname":"to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
			
		},
		{
			"fieldname":"branch",
            "label": __("Branch"),
            "fieldtype": "Link",
        	"options": "Branch"
		},
		{
			"fieldname": "material_code",
			"label": __("Material Code"),
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname": "material_group",
			"label": __("Material Group"),
			"fieldtype": "Link",
			"options": "Item Group"
		},
		{
			"fieldname": "vendor",
			"label": __("Vendor"),
			"fieldtype": "Link",
			"options": "Supplier"
		},
		{
			"fieldname": "accumulate",
			"label": __("Accumulate"),
			"fieldtype": "Check"
		}
	]
}
