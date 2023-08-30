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
from erpnext.custom_utils import check_future_date
from erpnext.custom_workflow import set_user

class DirectPayment(AccountsController):
	def validate(self):
		self.set_status()
		check_future_date(self.posting_date)
		if self.payment_type == "Receive":
			inter_company = frappe.db.get_value("Customer", self.party, "inter_company")
			if inter_company == 0:
				frappe.throw(_("Selected Customer {0} is not inter company ".format(self.party)))
		
		branch_name = frappe.db.get_value("Cost Center", self.cost_center, "branch")
		if branch_name != self.branch:
			frappe.throw(_("Branch {0} and Cost Center {1} doest not belong to each other".format(self.party)))
	
		set_user(self)

	
	def set_status(self):
                self.status = {
                        "0": "Draft",
                        "1": "Submitted",
                        "2": "Cancelled"
                }[str(self.docstatus or 0)]
	
	def on_submit(self):
		self.post_gl_entry()
		self.consume_budget()

	def on_cancel(self):
		self.post_gl_entry()
		self.cancel_budget_entry()

	##
        # Update the Committedd Budget for checking budget availability
        ##
        def consume_budget(self):
		if self.payment_type == "Payment":
			bud_obj = frappe.get_doc({
				"doctype": "Committed Budget",
				"account": self.debit_account,
				"cost_center": self.cost_center,
				"po_no": self.name,
				"po_date": self.posting_date,
				"amount": self.amount,
				"poi_name": self.name,
				"date": frappe.utils.nowdate()
				})
			bud_obj.flags.ignore_permissions = 1
			bud_obj.submit()

			consume = frappe.get_doc({
				"doctype": "Consumed Budget",
				"account": self.debit_account,
				"cost_center": self.cost_center,
				"po_no": self.name,
				"po_date": self.posting_date,
				"amount": self.amount,
				"pii_name": self.name,
				"com_ref": bud_obj.name,
				"date": frappe.utils.nowdate()})
			consume.flags.ignore_permissions=1
			consume.submit()

	##
        # Cancel budget check entry
        ##
        def cancel_budget_entry(self):
		if self.payment_type == "Payment":
                	frappe.db.sql("delete from `tabCommitted Budget` where po_no = %s", self.name)
                	frappe.db.sql("delete from `tabConsumed Budget` where po_no = %s", self.name)

	def post_gl_entry(self):
		gl_entries      = []
		total_amount    = 0.0
		#self.posting_date = nowdate()
		
		# total_amt = flt(self.net_amount) + flt(self.tds_amount) + flt(self.deduction_amount)
		# if total_amt == self.amount:
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
						'party': self.party,
						'party_type': self.party_type,						
						"company": self.company,
						"remarks": self.remarks
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
						'party': self.party,
						'party_type': self.party_type,
						"company": self.company,
						"remarks": self.remarks
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
						'party': self.party,
						'party_type': self.party_type,
						"company": self.company,
						"remarks": self.remarks
						})
					)
			if self.deduction_amount > 0:
									for d in self.get("deduct"):
											gl_entries.append(
													self.get_gl_dict({
													"account": d.account,
													"debit": d.amount,
													"debit_in_account_currency": d.amount,
													"voucher_no": self.name,
													"voucher_type": self.doctype,
													"cost_center": self.cost_center,
													'party': self.party,
						'party_type': self.party_type,
													"company": self.company,
													"remarks": self.remarks
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
						'party': self.party,
						'party_type': self.party_type,					
						"company": self.company,
						"remarks": self.remarks
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
						'party': self.party,
						'party_type': self.party_type,
						"company": self.company,
						"remarks": self.remarks
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
						'party': self.party,
						'party_type': self.party_type,						
						"company": self.company,
						"remarks": self.remarks
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
						'party': self.party,
						'party_type': self.party_type,						
						"company": self.company,
						"remarks": self.remarks
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
						'party': self.party,
						'party_type': self.party_type,
						"company": self.company,
						"remarks": self.remarks
						})
					)
			if self.deduction_amount > 0:
									for d in self.get("deduct"):
											gl_entries.append(
													self.get_gl_dict({
													"account": d.account,
													"credit": d.amount,
													"credit_in_account_currency": d.amount,
													"voucher_no": self.name,
													"voucher_type": self.doctype,
													"cost_center": self.cost_center,
													'party': self.party,
						'party_type': self.party_type,
													"company": self.company,
													"remarks": self.remarks
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
						'party': self.party,
						'party_type': self.party_type,
						"company": self.company,
						"remarks": self.remarks
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
						'party': self.party,
						'party_type': self.party_type,
						"company": self.company,
						"remarks": self.remarks
						})
					)
		make_gl_entries(gl_entries, cancel=(self.docstatus == 2),update_outstanding="No", merge_entries=False)
		#else:
		#frappe.throw("Total Debit is not equal to Total Credit. It should be equal")

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
