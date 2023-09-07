frappe.views.calendar["Timesheet"] = {
	field_map: {
		"start": "from_date",
		"end": "to_date",
		"name": "parent",
		"id": "parent",
		"title": "description",
		"allDay": "allDay",
		"child_name": "name"
	},
	gantt: true,
	filters: [
		{
			"fieldtype": "Link",
			"fieldname": "project",
			"options": "Project",
			"label": __("Project")
		},
		{
			"fieldtype": "Link",
			"fieldname": "employee",
			"options": "Employee",
			"label": __("Employee")
		}
	],
	get_events_method: "erpnext.projects.doctype.timesheet.timesheet.get_events"
}