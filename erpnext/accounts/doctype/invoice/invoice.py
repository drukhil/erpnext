# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.custom_utils import prepare_gl

class Invoice(Document):
	def validate(self):
		total = 0.0
		discount = 0.0
		for a in self.get("items"):
			revenue_account = frappe.get_doc("Item", a.item).income_account
			if not revenue_account:
				frappe.throw("Set Up Revenue Account in Item Master")
			a.income_account = revenue_account
			a.amount = flt(a.qty) * flt(a.rate) - flt(a.discount)
			if flt(a.amount) < 0:
				frappe.throw("Amount Cannot be negative at row '{0}'".format(a.idx))
			total += (flt(a.qty) * flt(a.rate) - flt(a.discount))
			discount += flt(a.discount)
		self.total_amount = flt(total)
		self.total_discount = flt(discount)

		#self.net_receivable = self.total_amount - self.discount_amount
			
		if flt(self.total_amount) < 0:
			frappe.throw("Receivable Amount cannot be negative")
	
	def  on_submit(self):
		cc = {}
		for a in self.get("items"):
			if cc.has_key(a.income_account):
				cc[a.income_account] = cc[a.income_account]+ flt(a.amount)
			else:
				cc.setdefault(a.income_account, a.amount)
		self.prepare_gl(cc)
	
	def on_cancel(self):
		frappe.db.sql(""" delete from `tabGL Entry` where voucher_no = '{0}'""".format(self.name))

	def prepare_gl(self, cc):
		gl_entries = []
		default_rv_account = frappe.get_doc("Company", self.company).default_receivable_account
                if not default_rv_account:
                        frappe.throw("Default Receivable Account is not defined in Company" ,title="Data Not found")
		gl_entries.append(
                                prepare_gl(self, {"account": default_rv_account,
                                                 "party_type": "Customer",
                                                 "party": self.customer,
                                                 "debit": flt(self.total_amount),
                                                 "debit_in_account_currency": flt(self.total_amount),
                                                 "cost_center": self.cost_center,
					          "remarks": "{0}  {1}".format(self.title, self.cost_center)
                                                })
                                )

		for a in cc.items():
			gl_entries.append(
                                prepare_gl(self, {"account": a[0],
                                                 "party_type": "Customer",
                                                 "party": self.customer,
                                                 "credit": flt(a[1]),
                                                 "credit_in_account_currency": flt(a[1]),
                                                 "cost_center": self.cost_center,
						 "remarks": "{0}  {1}".format(self.title, self.cost_center)
                                                })
                                )

                if gl_entries:
                        from erpnext.accounts.general_ledger import make_gl_entries
                        make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=True)

