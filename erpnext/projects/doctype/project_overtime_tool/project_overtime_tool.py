# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document


class ProjectOvertimeTool(Document):
	pass

@frappe.whitelist()
def get_employees(employee_type, cost_center, branch, date, number_of_hours,unit):
	attendance_not_marked = []
	attendance_marked = []

	employee_list = frappe.get_list(employee_type, fields=["name", "person_name"], filters={
		"status": "Active", "cost_center": cost_center, "branch": branch, "unit":unit}, order_by="person_name")
	marked_employee = {}
	for emp in frappe.get_list("Overtime Entry", fields=["number", "number_of_hours"],
							   filters={"date": date}):
		marked_employee[emp['number']] = emp['number']

	for employee in employee_list:
		if employee['name'] not in marked_employee:
			attendance_not_marked.append(employee)
		else:
			attendance_marked.append(employee)
	return {
		"marked": attendance_marked,
		"unmarked": attendance_not_marked
	}


@frappe.whitelist()
def allocate_overtime(employee_list, cost_center, branch, date, number_of_hours, employee_type, purpose=None):
	employee_list = json.loads(employee_list)
	for employee in employee_list:
		attendance = frappe.new_doc("Overtime Entry")
        attendance.ignore_permissions=True
		attendance.date = date
		attendance.purpose = purpose
		attendance.cost_center = cost_center
		attendance.branch = branch
		attendance.number_of_hours = number_of_hours
		attendance.number = employee['name']
		attendance.employee_type = employee_type
		attendance.submit()
