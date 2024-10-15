# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from erpnext.custom_workflow import validate_separation_workflow
from frappe.utils import today
from frappe.model.naming import make_autoname

class EmployeeSeparation(Document):
	def validate(self):
		self.check_duplicate()
		validate_separation_workflow(self)

	def autoname(self):
		abb = "EMPSEP"
		self.name = make_autoname(str(abb) + './.YYYY./.#####.')
	def on_submit(self):
		self.check_duplicate()
		# notify_workflow_states(self)

	def on_cancel(self):
		if self.separation_clearance:
			frappe.throw('Need to cancel separation clearance first')
		# notify_workflow_states(self)

	def check_duplicate(self):
		duplicates = frappe.db.sql("""select name from 
				`tabEmployee Separation` 
				where employee = '{0}'  
				and name != '{1}' 
				and docstatus != 2
			""".format(self.employee, self.name))
		if duplicates:
			frappe.throw("Employee Separation already created for the Employee '{}'".format(self.employee))

  
@frappe.whitelist()
def make_employee_benefit(source_name, target_doc=None, skip_item_mapping=False):
	def update_item(source, target, source_parent):
		target.separation_reference = source.name
		target.grade = source.employee_grade
		target.division = frappe.db.get_value("Employee",source.employee,"division")
		target.separation_date = source.separation_date
		
	mapper = {
		"Employee Separation": {
			"doctype": "Employee Benefits",
			"fieldmap": {
				"name": "employee_separation_id",
				"employee_grade": "grade",
			},
			"postprocess": update_item
		},
	}

	target_doc = get_mapped_doc("Employee Separation", source_name, mapper, target_doc)

	return target_doc

@frappe.whitelist()
def make_separation_clearance(source_name, target_doc=None, skip_item_mapping=False):
	def update_item(source_doc, target_doc, source_parent):
		# target.purpose = "Separation"
		target_doc.employee_separation_id = source_doc.name
		target_doc.cid = frappe.db.get_value("Employee",source_doc.employee,"passport_number")
		target_doc.phone_number = frappe.db.get_value("Employee",source_doc.employee,"phone_number")
		target_doc.grade = source_doc.employee_grade
		target_doc.division = frappe.db.get_value("Employee",source_doc.employee,"division")
		target_doc.approver = None
		target_doc.approver_name = None
		target_doc.approver_designation = None
		target_doc.employee = source_doc.employee
		target_doc.branch = frappe.db.get_value("Employee",source_doc.employee,"branch")
		target_doc.document_no = source_doc.name
	mapper = {
		"Employee Separation": {
			"doctype": "Employee Separation Clearance",
			"field_map":{
				"employee": "employee",
				"name": "employee_separation_id",   
				"employee_grade": "grade",
			},
            "postprocess": update_item,
		},
	}

	target_doc = get_mapped_doc("Employee Separation", source_name, mapper, target_doc)
	return target_doc

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)
	
	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabEmployee Separation`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabEmployee Separation`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabEmployee Separation`.approver = '{user}' and `tabEmployee Separation`.workflow_state != 'Draft')
	)""".format(user=user)
