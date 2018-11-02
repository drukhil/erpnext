# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, get_datetime, get_url, nowdate, now_datetime, money_in_words
from erpnext.accounts.general_ledger import make_gl_entries
from frappe import _
from erpnext.controllers.accounts_controller import AccountsController

class DirectPayment(AccountsController):
	def validate(self):
		if self.payment_type == "Receive":
			inter_company = frappe.db.get_value("Customer", self.customer, "inter_company")
			if inter_company == 0:
				frappe.throw(_("Selected Customer {0} is not inter company ".format(self.customer)))
		self.clearance_date = None

	def on_submit(self):
		self.post_gl_entry()

	def on_cancel(self):
		if self.clearance_date:
			frappe.throw("Already done bank reconciliation.")
		self.post_gl_entry()

	def post_gl_entry(self):
		gl_entries      = []
		total_amount    = 0.0
		self.posting_date = nowdate()
		if (self.net_amount + self.tds_amount) == self.amount:
			if self.payment_type == "Receive":
				account_type = frappe.db.get_value("Account", self.debit_account, "account_type") or ""
				if account_type == "Receivable" or account_type == "Payable":
					gl_entries.append(
						self.get_gl_dict({
							"account": self.debit_account,
							"debit": self.net_amount,
							"debit_in_account_currency": self.net_amount,
							"voucher_no": self.name,
							"voucher_type": self.doctype,
							"cost_center": self.cost_center,
							'party': self.customer,
							'party_type': 'Customer',						
							"company": self.company,
							"remarks": self.remarks,
							"posting_date": self.posting_date,
							"business_activity": self.business_activity
							})
						)
				else:
					gl_entries.append(
						self.get_gl_dict({
							"account": self.debit_account,
							"debit": self.net_amount,
							"debit_in_account_currency": self.net_amount,
							"voucher_no": self.name,
							"voucher_type": self.doctype,
							"cost_center": self.cost_center,
							"company": self.company,
							"remarks": self.remarks,
							"posting_date": self.posting_date,
							"business_activity": self.business_activity
							})
						)
				if self.tds_amount > 0:
					gl_entries.append(
						self.get_gl_dict({
							"account": self.tds_account,
							"debit": self.tds_amount,
							"debit_in_account_currency": self.tds_amount,
							"voucher_no": self.name,
							"voucher_type": self.doctype,
							"cost_center": self.cost_center,
							"company": self.company,
							"remarks": self.remarks,
							"posting_date": self.posting_date,
							"business_activity": self.business_activity
							})
						)
				account_type1 = frappe.db.get_value("Account", self.credit_account, "account_type") or ""
				if account_type1 == "Receivable" or account_type1 == "Payable":
					gl_entries.append(
						self.get_gl_dict({
							"account": self.credit_account,
							"credit": self.amount,
							"credit_in_account_currency": self.amount,
							"voucher_no": self.name,
							"voucher_type": self.doctype,
							"cost_center": self.cost_center,
							'party': self.customer,
							'party_type': 'Customer',					
							"company": self.company,
							"remarks": self.remarks,
							"posting_date": self.posting_date,
							"business_activity": self.business_activity				
							})
						)
				else:
					gl_entries.append(
						self.get_gl_dict({
							"account": self.credit_account,
							"credit": self.amount,
							"credit_in_account_currency": self.amount,
							"voucher_no": self.name,
							"voucher_type": self.doctype,
							"cost_center": self.cost_center,
							"company": self.company,
							"remarks": self.remarks,
							"posting_date": self.posting_date,
							"business_activity": self.business_activity					
							})
						)
			else:
				account_type = frappe.db.get_value("Account", self.debit_account, "account_type") or ""
				if account_type == "Payable" or account_type == "Receivable":
					gl_entries.append(
						self.get_gl_dict({
							"account": self.debit_account,
							"debit": self.amount,
							"debit_in_account_currency": self.amount,
							"voucher_no": self.name,
							"voucher_type": self.doctype,
							"cost_center": self.cost_center,
							'party': self.supplier,
							'party_type': 'Supplier',						
							"company": self.company,
							"remarks": self.remarks,
							"posting_date": self.posting_date,
							"business_activity": self.business_activity
							})
						)
				else:
					gl_entries.append(
						self.get_gl_dict({
							"account": self.debit_account,
							"debit": self.amount,
							"debit_in_account_currency": self.amount,
							"voucher_no": self.name,
							"voucher_type": self.doctype,
							"cost_center": self.cost_center,						
							"company": self.company,
							"remarks": self.remarks,
							"posting_date": self.posting_date,
							"business_activity": self.business_activity
							})
						)
				if self.tds_amount > 0:
					gl_entries.append(
						self.get_gl_dict({
							"account": self.tds_account,
							"credit": self.tds_amount,
							"credit_in_account_currency": self.tds_amount,
							"voucher_no": self.name,
							"voucher_type": self.doctype,
							"cost_center": self.cost_center,
							"company": self.company,
							"remarks": self.remarks,
							"posting_date": self.posting_date,
							"business_activity": self.business_activity
							})
						)
				account_type1 = frappe.db.get_value("Account", self.credit_account, "account_type") or ""
				if account_type1 == "Payable" or account_type1 == "Receivable":
					gl_entries.append(
						self.get_gl_dict({
							"account": self.credit_account,
							"credit": self.net_amount,
							"credit_in_account_currency": self.net_amount,
							"voucher_no": self.name,
							"voucher_type": self.doctype,
							"cost_center": self.cost_center,
							'party': self.supplier,
							'party_type': 'Supplier',
							"company": self.company,
							"remarks": self.remarks,
							"posting_date": self.posting_date,
							"business_activity": self.business_activity
							})
						)
				else:
					gl_entries.append(
						self.get_gl_dict({
							"account": self.credit_account,
							"credit": self.net_amount,
							"credit_in_account_currency": self.net_amount,
							"voucher_no": self.name,
							"voucher_type": self.doctype,
							"cost_center": self.cost_center,
							"company": self.company,
							"remarks": self.remarks,
							"posting_date": self.posting_date,
							"business_activity": self.business_activity
							})
						)
			make_gl_entries(gl_entries, cancel=(self.docstatus == 2),update_outstanding="No", merge_entries=False)
		else:
			frappe.throw("Total Debit is not equal to Total Credit. It should be equal")

@frappe.whitelist()
def get_tds_account(percent, payment_type):
	if payment_type == "Payment":
		if percent:
			if cint(percent) == 2:
				field = "tds_2_account"		
			elif cint(percent) == 3:
				field = "tds_3_account"		
			elif cint(percent) == 5:
				field = "tds_5_account"		
			elif cint(percent) == 10:
				field = "tds_10_account"		
			else:
				frappe.throw("Set TDS Accounts in Accounts Settings and try again")
			return frappe.db.get_single_value("Accounts Settings", field)
				
	elif payment_type == "Receive":
		if percent:
			field = "tds_deducted"
			return frappe.db.get_single_value("Accounts Settings", field)

	
