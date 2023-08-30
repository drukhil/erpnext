# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application \
	import get_leave_allocation_records, get_leave_balance_on, get_approved_leaves_for_period


def execute(filters=None):
	if filters.leave_type:
		leave_types = frappe.db.sql_list("select name from `tabLeave Type` where name = %s order by name asc", filters.leave_type)
	else:
		leave_types = frappe.db.sql_list("select name from `tabLeave Type` order by name asc")

	columns = get_columns(leave_types)
	data = get_data(filters, leave_types)

	return columns, data

def get_columns(leave_types):
	columns = [
		_("Employee") + ":Link/Employee:120",
		_("Employee Name") + "::150",
		_("Department") +"::150",
		_("Branch") +"::160",
		_("Employment Type") +"::160",


	]

	for leave_type in leave_types:
		columns.append(_(leave_type) + " " + _("Taken") + ":Float:160")
		columns.append(_(leave_type) + " " + _("Balance") + ":Float:160")

	return columns

def get_data(filters, leave_types):

	allocation_records_based_on_to_date = get_leave_allocation_records(filters.to_date)
	filters_dict = { "status": "Active", "company": filters.company}

        if filters.branch:
                filters_dict['branch'] = filters.branch
        if filters.employee:
                filters_dict['name'] = filters.employee

	if filters.employee_type:
		filters_dict['employment_type'] = filters.employee_type

	active_employees = frappe.get_all("Employee",
		filters = filters_dict,
		fields = ["name", "employee_name", "department", "branch", "employment_type"])

	data = []
	for employee in active_employees:
		row = [employee.name, employee.employee_name, employee.department, employee.branch, employee.employment_type]

		for leave_type in leave_types:
			# leaves taken
			leaves_taken = get_approved_leaves_for_period(employee.name, leave_type,
				filters.from_date, filters.to_date)
			
			# closing balance
			closing = get_leave_balance_on(employee.name, leave_type, filters.to_date,
				allocation_records_based_on_to_date.get(employee.name, frappe._dict()))
			
			row += [leaves_taken, closing]

		data.append(row)

	return data
