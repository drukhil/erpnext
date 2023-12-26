// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Employee Leave Balance"] = {
	"filters": [
                {
                        "fieldname":"leave_type",
                        "label": __("Leave Type"),
                        "fieldtype": "Link",
                        "options": "Leave Type",
			"reqd": 1,
                },
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.year_start()
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.year_end()
		},
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		},
		{
                        "fieldname":"branch",
                        "label": __("Branch"),
                        "fieldtype": "Link",
                        "options": "Branch",
                },
		{
                        "fieldtype": "Break"
                },
		{
			"fieldname": "employee_type",
			"label": __("Employee Type"),
			"fieldtype": "Link",
			"options": "Employment Type" 
		},
		{
			"fieldname":"employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"get_query": function() {
				var branch = frappe.query_report.filters_by_name.branch.get_value();
				var employee_type = frappe.query_report.filters_by_name.employee_type.get_value();
				if(branch) {
					return {"doctype": "Employee", "filters": {"branch": branch, "status": "Active"}}
				}
				else if (employee_type){
					return {"doctype": "Employee", "filters": {"employment_type": employee_type, "status": "Active"}}
				} 
				else 
				{
					return {"doctype": "Employee", "filters": {"status": "Active"}}
				}
			}
		},
		{
			"fieldname":"organization",
			"label": __("Organization"),
			"fieldtype": "Link",
			"options": "Organization",
			"reqd": 0,
		}
	]
}
