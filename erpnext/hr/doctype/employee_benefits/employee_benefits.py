# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class EmployeeBenefits(Document):
	def validate(self):
		pass

	def on_submit(self):
		if self.purpose == "Separation":
			self.update_employee()
		self.post_journal()

	def post_journal(self):
		emp = frappe.get_doc("Employee", self.employee)
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		je.branch = emp.branch
		je.posting_date = self.posting_date
		je.title = str(self.purpose) + " Benefit (" + str(self.employee_name) + ")"
		je.voucher_type = 'Bank Entry'
		je.naming_series = 'Bank Payment Voucher'
		je.remark = str(self.purpose) + ' Benefit payments for ' + str(self.employee_name) + "("+str(self.employee)+")";

		total_amount = 0
		for a in self.items:
			je.append("accounts", {
					"account": a.gl_account,
					"party_type": "Employee",
					"party": self.employee,
					"reference_type": "Employee Benefits",
					"reference_name": self.name,
					"cost_center": emp.cost_center,
					"debit_in_account_currency": flt(a.amount),
					"debit": flt(a.amount),
				})
			total_amount = flt(total_amount) + flt(a.amount)
		je.append("accounts", {
				"account": frappe.db.get_value("Branch", emp.branch, "expense_bank_account"),
				"cost_center": emp.cost_center,
				"credit_in_account_currency": flt(total_amount),
				"credit": flt(total_amount),
			})
		je.insert()
		self.journal = je.name

	def update_employee(self):
		emp = frappe.get_doc("Employee", self.employee)
		emp.status = "Left"
		emp.relieving_date = self.separation_date

		for a in self.items:
			doc = frappe.new_doc("Separation Benefits")
			doc.parent = self.employee
			doc.parentfield = "separation_benefits"
			doc.parenttype = "Employee"
			doc.s_b_type = a.benefit_type
			doc.s_b_currency = a.amount
			doc.save()
		emp.save()	

	def on_cancel(self):
		self.check_journal()

	def check_journal(self):
		docs = frappe.db.sql("select parent from `tabJournal Entry Account` where reference_name = %s and docstatus != 2", self.name, as_dict=True)
		if docs:
			frappe.throw("Cancel Journal Entry <b>" + str(docs[0].parent) + "</b> before cancelling this document")

@frappe.whitelist()
def set_amount(benefit_type, employee):
	salary_structure = frappe.db.get_value("Salary Structure",{"employee" :employee, "is_active":"Yes"},"name")
	basic_pay = frappe.db.get_value("Salary Detail",{"parent":salary_structure,"salary_component":"Basic Pay"},"amount")
	employee_grade = frappe.db.get_value("Employee",employee,"employee_subgroup")
	tada_amount = frappe.db.get_value("Employee Grade",employee_grade,"dsa")
	if benefit_type =="Transfer Grant":
		amount= basic_pay
	elif benefit_type =="TADA-Incountry":
		amount = tada_amount
	else:
		amount =0
	return amount
