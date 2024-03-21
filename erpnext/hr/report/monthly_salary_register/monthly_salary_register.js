// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Monthly Salary Register"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": sys_defaults.fiscal_year,
		},
		{
			"fieldname":"month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": "\nJan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
			"default": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
				"Dec"][frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()],
		},
		{
                        "fieldname":"division",
                        "label": __("Division"),
                        "fieldtype": "Link",
                        "options": "Division",
                },
		{
                        "fieldname":"cost_center",
                        "label": __("Cost Center"),
                        "fieldtype": "Link",
                        "options": "Cost Center",
                },
                {
                        "fieldname":"employee",
                        "label": __("Employee"),
                        "fieldtype": "Link",
                        "options": "Employee",
			"get_query": function() {
				var branch = frappe.query_report.filters_by_name.branch.get_value();
				if(branch) {
					return {"doctype": "Employee", "filters": {"branch": branch, "status": "Active"}}
				}
				else {
					return {"doctype": "Employee", "filters": {"status": "Active"}}
				}
			}
                },
		{
			"fieldname": "process_status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "All\nSubmitted\nUn-Submitted\nCancelled",
			"default": "All"
		},
		{
			"fieldname": "report_type",
			"label": __("Report Type"),
			"fieldtype": "Select",
			"options": "Salary\nArrear\nBulk Leave Encashment",
			"default": "Salary"
		},
	]
}
