# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr, flt, fmt_money, formatdate

class ProjectSales(Document):
	def validate(self):
		self.flags.ignore_permissions = 1

	def before_submit(self):
		self.validate_accounts()

	def on_submit(self):
		self.update_consumable_register()
		self.post_journal_entry()

	def before_cancel(self):
		cl_status = frappe.db.get_value("Journal Entry", self.jv, "docstatus")
		if cl_status and cl_status != 2:
			frappe.throw("You need to cancel the journal entry related to this document first!")
		
		self.db_set('jv', "")
		frappe.db.sql("delete from `tabConsumable Register Entry` where ref_doc = \'" + str(self.name) + "\'")

	
	def validate_accounts(self):
		if not self.items:
			frappe.throw("Cannot submit document without any Items in it")
		else:
			for a in self.items:
				if not a.expense_account:
					frappe.throw("Expense account for Material " + str(a.item_code) + " is mandatory")

	def update_consumable_register(self):
		for a in self.items:
			if frappe.db.get_value("Item", a.item_code, "maintain_in_register"):
				doc = frappe.new_doc("Consumable Register Entry")
				doc.flags.ignore_permissions = 1
				doc.branch = self.buying_branch
				doc.item_code = a.item_code
				doc.date = self.posting_date
				doc.issued_to = self.employee
				doc.ref_doc = self.name
				doc.qty = a.qty
				doc.insert()
				
	
	def post_journal_entry(self):
		ic_account = frappe.db.get_single_value("Accounts Settings", "intra_company_account")
		if not ic_account:
			frappe.throw("Setup Intra-Company Account in Accounts Settings")	
		sale_account = frappe.db.get_single_value("Projects Accounts Settings", "inventory_account")
		if not sale_account:
			frappe.throw("Setup Sale of Inventory Account in Maintenance Accounts Settings")	

		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1 
		je.title = "Project Sales (" + self.name + ")"
		je.voucher_type = 'Project Sales Invoice'
		je.naming_series = 'Project Sales Invoice'
		je.remark = 'Payment against Project Sales Invoice : ' + self.name;
		je.posting_date = self.posting_date
		je.branch = self.selling_branch

		total_amount = 0
		#Amount Segregation
		cc_amount = {}
		for a in self.items:
			if cc_amount.has_key(a.expense_account):
				cc_amount[a.expense_account] = cc_amount[a.expense_account] + a.amount
			else:
				cc_amount[a.expense_account] = a.amount;
			total_amount += a.amount
		
		if total_amount > 0:	
			for acc in cc_amount:
				je.append("accounts", {
						"account": acc,
						"cost_center": self.buying_cost_center,
						"debit_in_account_currency": flt(cc_amount[acc]),
						"debit": flt(cc_amount[acc]),
					})

			je.append("accounts", {
					"account": ic_account,
					"cost_center": self.buying_cost_center,
					"credit_in_account_currency": flt(total_amount),
					"credit": flt(total_amount),
				})
			je.append("accounts", {
					"account": ic_account,
					"cost_center": self.selling_cost_center,
					"debit_in_account_currency": flt(total_amount),
					"debit": flt(total_amount),
				})
			je.append("accounts", {
					"account": sale_account,
					"reference_type": "Project Sales",
					"reference_name": self.name,
					"cost_center": self.selling_cost_center,
					"credit_in_account_currency": flt(total_amount),
					"credit": flt(total_amount),
				})
			je.insert()
			self.db_set("jv", je.name)
		else:
			frappe.throw("Total Amount cannot be smaller than zero")


