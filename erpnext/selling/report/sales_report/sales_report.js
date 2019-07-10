// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Report"] = {
	"filters": [
		{
                        "fieldname": "company",
                        "label": ("Company"),
                        "fieldtype": "Link",
                        "options": "Company",
                        "default": frappe.defaults.get_user_default("Company"),
                        "reqd": 1
                },
                {
                        "fieldname": "cost_center",
                        "label": ("Parent Branch"),
                        "fieldtype": "Link",
                        "options": "Cost Center",
                        "get_query": function() {
                                var company = frappe.query_report.filters_by_name.company.get_value();
                                return {
                                        'doctype': "Cost Center",
                                        'filters': [
                                                ['is_disabled', '!=', '1'],
                                                ['company', '=', company]
                                        ]
                                }
                        },
                        "on_change": function(query_report) {
                                var cost_center = query_report.get_values().cost_center;
                                query_report.filters_by_name.branch.set_input(null);
                                query_report.filters_by_name.location.set_input(null);
                                query_report.trigger_refresh();
                                if (!cost_center) {
                                        return;
                                }
			frappe.call({
                                        method: "erpnext.custom_utils.get_branch_from_cost_center",
                                        args: {
                                                "cost_center": cost_center,
                                        },
                                        callback: function(r) {
                                                query_report.filters_by_name.branch.set_input(r.message)
                                                query_report.trigger_refresh();
                                        }
                                })
                        },
                        "reqd": 1,
                },
                {
                        "fieldname": "branch",
                        "label": ("Branch"),
                        "fieldtype": "Link",
                        "options": "Branch",
                        "read_only": 1,
                        "get_query": function() {
                                var company = frappe.query_report.filters_by_name.company.get_value();
                                return {"doctype": "Branch", "filters": {"company": company, "is_disabled": 0}}
                        }
                },
                {
                        "fieldname": "location",
                        "label": ("Location"),
                        "fieldtype": "Link",
                        "options": "Location",
                        "get_query": function() {
                                var branch = frappe.query_report.filters_by_name.branch.get_value();
                                return {"doctype": "Location", "filters": {"branch": branch, "is_disabled": 0}}
                        }
                },
		
		/*{
                        "fieldname": "adhoc_production",
                        "label": ("Adhoc Production"),
                        "fieldtype": "Link",
                        "options": "Adhoc Production",
                        "get_query": function() {
                                var loc = frappe.query_report.filters_by_name.location.get_value();
                                return {"doctype": "Adhoc Production", "filters": {"location": loc, "is_disabled": 0}}
                        }
                },*/
                {
                        "fieldname": "from_date",
                        "label": __("From Date"),
                        "fieldtype": "Date",
                        "default": frappe.defaults.get_user_default("year_start_date"),
                        "reqd": 1,
                },
                {
                        "fieldname": "to_date",
                        "label": __("To Date"),
                        "fieldtype": "Date",
                        "default": frappe.defaults.get_user_default("year_end_date"),
                        "reqd": 1,
                },
		{
                        "fieldtype": "Break",
                },
		
		{
                        "fieldname": "item_group",
                        "label": ("Material Group"),
                        "fieldtype": "Link",
                        "options": "Item Group",
                        "get_query": function() {
                                return {"doctype": "Item Group", "filters": {"is_group": 0, "is_production_group": 1}}
                        },
                },
                {
                        "fieldname": "item_sub_group",
                        "label": ("Material Sub Group"),
                        "fieldtype": "Link",
                        "options": "Item Sub Group",
                        "get_query": function() {
                                var item_group = frappe.query_report.filters_by_name.item_group.get_value();
                                return {"doctype": "Item Sub Group", "filters": {"item_group": item_group}}
                        }
                },
                {
                        "fieldname": "item",
                        "label": ("Material"),
                        "fieldtype": "Link",
                        "options": "Item",
                        "get_query": function() {
                                var sub_group = frappe.query_report.filters_by_name.item_sub_group.get_value();
                                return {"doctype": "Item", "filters": {"item_sub_group": sub_group, "is_production_item": 1}}
                        }
                },
			
		/*{
                        "fieldname": "production_type",
                        "label":("Production Type"),
                        "fieldtype" : "Select",
                        "width" :"80",
                        "options": ["All", "Planned","Adhoc"],
                        "default": "All",
                        "reqd" : 1
                },*/
                {
                        "fieldname": "timber_species",
                        "label": ("Timber Species"),
                        "fieldtype": "Link",
                        "options": "Timber Species",
                        "get_query": function() {
                                var item_group = frappe.query_report.filters_by_name.item_group.get_value();
                                if (!item_group || item_group != "Timber Products") {
                                        return {"doctype": "Timber Species", "filters": {"docstatus": 5}}
                                }
                                else {
                                        return {"doctype": "Timber Species"}
                                }
                        }
                },


		{
                        "fieldname": "timber_class",
                        "label": ("Timber Class"),
                        "fieldtype": "Link",
                        "options": "Timber Class",
                        "get_query": function() {
                                var item_group = frappe.query_report.filters_by_name.item_group.get_value();
                                if (!item_group || item_group != "Timber Products") {
                                        return {"doctype": "Timber Class", "filters": {"docstatus": 5}}
                                }
                                else {
                                        return {"doctype": "Timber Class"}
                                }
                        }
                },
                {
                        "fieldname": "warehouse",
                        "label": ("Warehouse"),
                        "fieldtype": "Link",
                        "options": "Warehouse",
                        "get_query": function() {
                         /*     var branch = frappe.query_report.filters_by_name.branch.get_value();
                                if (!branch) {
                                        return
                                } */
                                return {"doctype": "Warehouse", "filters": {"disabled": 0}}
                        }
                },

		{
                        "fieldname": "timber_type",
                        "label":("Timber Type"),
                        "fieldtype" : "Select",
                        "width" :"80",
                        "options": ["All", "Conifer","Broadleaf"],
                        "default": "All",
                        "reqd" : 1
                },
                {
                        "fieldname": "group_by",
                        "label": ("Group By"),
                        "fieldtype": "Select",
                        "options": ["Sales Order", "Delivery Note"],
			"default": "Sales Order"
                },
		{
                        "fieldname": "aggrigate",
                        "label": ("Show Aggregate"),
                        "fieldtype": "Check",
                        "default": 0
		},
		{
                        "fieldname": "product_wise_customer",
                        "label": ("Product Wise Customer"),
                        "fieldtype": "Check",
                        "default": 0
                }
	]
}
