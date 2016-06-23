frappe.query_reports["Material Shortage Report"] = {
	"filters": [
	{
		"fieldname":"operator_sign",						
		"label": __("Filter (<,>)"),
		"fieldtype": "Data",
		"default": "<",
		"reqd": 1
	},
	{
		"fieldname":"proj_qty",						
		"label": __("Projected Quantity"),
		"fieldtype": "Int",
		"default": 0
	}
	]
}
