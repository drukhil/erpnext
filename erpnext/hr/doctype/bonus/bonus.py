# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.hr.doctype.salary_structure.salary_structure import get_salary_tax

class Bonus(Document):
	def validate(self):
		self.validate_duplicate()
		self.calculate_values()

	def on_submit(self):
		cc_amount = {}
		for a in self.items:
			tax = get_salary_tax(a.amount)
			cc = frappe.db.get_value("Employee", a.employee, "cost_center")
			if cc_amount.has_key(cc):
				cc_amount[cc]['amount'] = cc_amount[cc]['amount'] + a.amount
				cc_amount[cc]['tax'] = cc_amount[cc]['tax'] + a.tax_amount
				cc_amount[cc]['balance_amount'] = cc_amount[cc]['balance_amount'] + a.balance_amount
			else:
				row = {"amount": a.amount, "tax": a.tax_amount, "balance_amount":a.balance_amount}
				cc_amount[cc] = row;

		self.post_journal_entry(cc_amount)

	def validate_duplicate(self):
		doc = frappe.db.sql("select name from `tabBonus` where docstatus != 2 and fiscal_year = \'"+str(self.fiscal_year)+"\' and name != \'"+str(self.name)+"\'")	
		if doc:
			frappe.throw("Can not create multiple Bonuses for the same year")

	def calculate_values(self):
		if self.items:
			tot = tax = 0
			for a in self.items:
				a.tax_amount = get_salary_tax(a.amount)
				a.balance_amount = flt(a.amount) - flt(a.tax_amount)
				tot += flt(a.amount)
				tax += flt(a.tax_amount)
			self.total_amount = tot
			self.tax_amount = tax
		else:
			frappe.throw("Cannot save without employee details")

	#Populate Bonus details 
	def get_employees(self):
		if not self.fiscal_year:
			frappe.throw("Fiscal Year is Mandatory")
		start, end = frappe.db.get_value("Fiscal Year", self.fiscal_year, ["year_start_date", "year_end_date"])
		query = "select b.employee, b.employee_name, b.branch, a.amount as basic_pay from `tabSalary Detail` a, `tabSalary Structure` b, tabEmployee e where a.parent = b.name and b.employee = e.name and a.salary_component = 'Basic Pay' and (b.is_active = 'Yes' or e.relieving_date between \'"+str(start)+"\' and \'"+str(end)+"\') and b.eligible_for_annual_bonus = 1 "
		query += " order by b.branch"
		entries = frappe.db.sql(query, as_dict=True)
		self.set('items', [])

		for d in entries:
			d.amount = 0
			row = self.append('items', {})
			row.update(d)

	def post_journal_entry(self, cc_amount):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1 
		je.title = "Annual Bonus for " + self.branch + "(" + self.name + ")"
		je.voucher_type = 'Bank Entry'
		je.naming_series = 'Bank Payment Voucher'
		je.remark = 'Bonus payment against : ' + self.name;
		je.posting_date = self.posting_date
		je.branch = self.branch

		bonus_account = frappe.db.get_single_value("HR Accounts Settings", "bonus_account")
		tax_account = frappe.db.get_single_value("HR Accounts Settings", "salary_tax_account")
		expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		if not bonus_account:
			frappe.throw("Setup Bonus Account in HR Accounts Settings")
		if not tax_account:
			frappe.throw("Setup Salary Tax Account in HR Accounts Settings")
		if not expense_bank_account:
			frappe.throw("Setup Expense Bank Account for your branch")
		
		for key in cc_amount.keys():
			je.append("accounts", {
					"account": bonus_account,
					"reference_type": "Bonus",
					"reference_name": self.name,
					"cost_center": key,
					"debit_in_account_currency": flt(cc_amount[key]['amount']),
					"debit": flt(cc_amount[key]['amount']),
				})
		
			je.append("accounts", {
					"account": expense_bank_account,
					"cost_center": key,
					"credit_in_account_currency": flt(cc_amount[key]['balance_amount']),
					"credit": flt(cc_amount[key]['balance_amount']),
				})
			
			je.append("accounts", {
					"account": tax_account,
					"cost_center": key,
					"credit_in_account_currency": flt(cc_amount[key]['tax']),
					"credit": flt(cc_amount[key]['tax']),
				})

		je.insert()

		self.db_set("journal_entry", je.name)

	def on_cancel(self):
		jv = frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus")
		if jv != 2:
			frappe.throw("Can not cancel Bonus Entry without canceling the corresponding journal entry " + str(self.journal_entry))
		else:
			self.db_set("journal_entry", "")


