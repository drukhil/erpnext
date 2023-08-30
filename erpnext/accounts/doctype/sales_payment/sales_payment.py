# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.custom_utils import prepare_gl, check_future_date


class SalesPayment(Document):
	def validate(self):
		if not self.cost_center:
			frappe.throw("Cost Center Is Required")
		if not self.party:
			frappe.throw("Party Is Required")
		if not self.get("references"):
			frappe.throw("Pull the Invoices")
		tot = 0.0
		for d in self.get("references"):
			tot += flt(d.total_amount)
                self.total_amount = tot


	def get_invoices(self):
                query = frappe.db.sql("""select name as reference_name, "Invoice" as reference_doctype, posting_date, 
		total_amount from  tabInvoice where docstatus = 1 and paid = 0 
		and cost_center = "{0}" and customer = "{1}"  order by posting_date""".format(self.cost_center, self.party), as_dict = 1)
                self.set('references', [])

                total_amt = 0
                for d in query:
                        row = self.append('references', {})
                        row.update(d)
			total_amt+=flt(d.total_amount)
                self.total_amount = total_amt


	def on_submit(self):
		self.prepare_gl()
		for a in self.get("references"):
			doc = frappe.get_doc("Invoice", a.reference_name)
			doc.db_set("paid", 1)

	def on_cancel(self):
                frappe.db.sql(""" delete from `tabGL Entry` where voucher_no = '{0}'""".format(self.name))

	def prepare_gl(self):
                gl_entries = []
                default_rv_account = frappe.get_doc("Company", self.company).default_receivable_account
                if not default_rv_account:
                        frappe.throw("Default Receivable Account is not defined in Company" ,title="Data Not found")
                gl_entries.append(
                                prepare_gl(self, {"account": default_rv_account,
                                                 "party_type": "Customer",
                                                 "party": self.party,
                                                 "credit": flt(self.total_amount),
                                                 "credit_in_account_currency": flt(self.total_amount),
                                                 "cost_center": self.cost_center,
                                                  "remarks": "{0}  {1}".format(self.title, self.cost_center)
                                                })
                                )

		gl_entries.append(
			prepare_gl(self, {"account": self.revenue_bank_account,
					 "party_type": "Customer",
					 "party": self.party,
					 "debit": flt(self.total_amount),
					 "debit_in_account_currency": flt(self.total_amount),
					 "cost_center": self.cost_center,
					 "remarks": "{0}  {1}".format(self.title, self.cost_center)
					})
			)

                if gl_entries:
                        from erpnext.accounts.general_ledger import make_gl_entries
                        make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=True)

	
