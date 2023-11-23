# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, cstr, flt, fmt_money, formatdate, nowdate
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.custom_utils import generate_receipt_no, check_future_date, get_branch_cc

class MechanicalPayment(AccountsController):
	def validate(self):
		check_future_date(self.posting_date)
		self.set_status()
		#self.validate_allocated_amount()
		total= 0
                for a in self.deducts:
                        total +=flt(a.amount)
                self.deduction_amount = total

		self.validate_allocated()
		self.set_missing_values()
		self.clearance_date = None

	def set_status(self):
                self.status = {
                        "0": "Draft",
                        "1": "Submitted",
                        "2": "Cancelled"
                }[str(self.docstatus or 0)]

        def before_submit(self):
                self.remove_unallocated_items()

	def set_missing_values(self):
		self.cost_center = get_branch_cc(self.branch)
		sub_net = 0
                sub_net = self.deduction_amount + self.tds_amount
                if sub_net > 0:
                        self.net_amount = self.receivable_amount - sub_net

		else:
			self.net_amount = self.receivable_amount
 
		if self.net_amount < 0:
			frappe.throw("Net Amount cannot be less than Zero")
		if self.tds_amount < 0:
			frappe.throw("TDS Amount cannot be less than Zero")

	def validate_allocated_amount(self):
		if not self.receivable_amount > 0:
			frappe.throw("Amount should be greater than 0")	
		to_remove = []
		total = flt(self.receivable_amount)
		total_actual = 0
		for d in self.items:
			allocated = 0
			if total > 0 and total >= d.outstanding_amount:
				allocated = d.outstanding_amount
				total_actual += flt(d.outstanding_amount)
			elif total > 0 and total < d.outstanding_amount:
				total_actual += flt(d.outstanding_amount)
				allocated = total
			else:
				allocated = 0
		
			d.allocated_amount = allocated
			total-=allocated
			if d.allocated_amount == 0:
				to_remove.append(d)

		[self.remove(d) for d in to_remove]
		self.actual_amount = total_actual 
		
		if self.receivable_amount > self.actual_amount:
			frappe.throw("Receivable Amount Cannot be grater than Total Outstanding Amount")

        def validate_allocated(self):
                if not self.receivable_amount > 0:
                        frappe.throw("Amount should be greater than 0")

                total = 0
                for d in self.items:
                        if flt(d.allocated_amount) < 0 or flt(d.allocated_amount) > flt(d.outstanding_amount):
                                frappe.throw("Allocated Amount should be between zero and Outstanding Amount on row {0}".format(d.idx))
                        total = flt(total) + flt(d.allocated_amount)

                if total != self.receivable_amount:
                        frappe.throw("Total Allocated Amount should be equal to Receivable Amount")
                if self.receivable_amount > self.actual_amount:
                        frappe.throw("Receivable Amount Cannot be grater than Total Outstanding Amount")
        def remove_unallocated_items(self):
                to_remove = []
                for d in self.items:
                        if d.allocated_amount == 0:
                                to_remove.append(d)
                [self.remove(d) for d in to_remove]

	def on_submit(self):
		self.make_gl_entry()
		self.update_ref_doc()

	def before_cancel(self):
                self.set_status()
	
	def on_cancel(self):	
		if self.clearance_date:
                        frappe.throw("Already done bank reconciliation.")

		self.make_gl_entry()
		self.update_ref_doc(cancel=1)

	def check_amount(self):
		if self.net_amount < 0:
			frappe.throw("Net Amount cannot be less than Zero")
		if self.tds_amount < 0:
			frappe.throw("TDS Amount cannot be less than Zero")
			
	def update_ref_doc(self, cancel=None):
		for a in self.items:
			doc = frappe.get_doc(a.reference_type, a.reference_name)
			if cancel:
				amount = flt(doc.outstanding_amount) + flt(a.allocated_amount)
			else:
				amount = flt(doc.outstanding_amount) -  flt(a.allocated_amount) 

			if a.reference_type == "Job Card":
				payable_amount = doc.total_amount
			else:
				payable_amount = doc.balance_amount

			if amount < 0:
				frappe.throw("Outstanding Amount for {0} cannot be less than 0".format(a.reference_name))
			if amount > payable_amount:
				frappe.throw("Outstanding Amount for {0} cannot be greater than payable amount".format(a.reference_name))
				
			doc.db_set("outstanding_amount", amount)

	def get_series(self):
		fiscal_year = getdate(self.posting_date).year
		generate_receipt_no(self.doctype, self.name, self.branch, fiscal_year)

	def make_gl_entry(self):
		from erpnext.accounts.general_ledger import make_gl_entries
		receivable_account = frappe.db.get_single_value("Maintenance Accounts Settings", "default_receivable_account")
		if not receivable_account:
			frappe.throw("Setup Default Receivable Account in Maintenance Setting")

		gl_entries = []
		if flt(self.net_amount) > 0:
			gl_entries.append(
				self.get_gl_dict({"account": self.income_account,
					 "debit": flt(self.net_amount),
					 "debit_in_account_currency": flt(self.net_amount),
					 "cost_center": self.cost_center,
					 "party_check": 1,
					 "reference_type": self.doctype,
					 "reference_name": self.name,
					 "remarks": self.remarks
					})
			)

		if self.tds_amount:
			gl_entries.append(
				self.get_gl_dict({"account": self.tds_account,
						 "debit": flt(self.tds_amount),
						 "debit_in_account_currency": flt(self.tds_amount),
						 "cost_center": self.cost_center,
						 "party_check": 1,
						 "party_type": "Customer",
						 "party": self.customer,
						 "reference_type": self.doctype,
						 "reference_name": self.name,
						 "remarks": self.remarks
						})
				)
		
		for a in self.items:
			#Get against voucher and type for correct Receivable report
			against_voucher, against_voucher_type = None, None
			doc = frappe.get_doc(a.reference_type, a.reference_name)
			if a.reference_type == "Job Card":
				if doc.jv:
					against_voucher_type = "Journal Entry"
					against_voucher = doc.jv
			if doc.customer != a.customer:
				frappe.throw(" {} customer selected but the customer must be {} as per {} {}. ".format(a.customer, doc.customer, a.reference_type, a.reference_name))

			gl_entries.append(
				self.get_gl_dict({"account": receivable_account,
						"credit": flt(a.allocated_amount),
						"credit_in_account_currency": flt(a.allocated_amount),
						"cost_center": self.cost_center,
						"party_check": 1,
						"party_type": "Customer",
						"party": a.customer if a.customer else self.customer,
						"reference_type": self.doctype,
						"reference_name": self.name,
						"against_voucher_type":against_voucher_type if against_voucher_type else a.reference_type,
						"against_voucher": against_voucher if against_voucher else a.reference_name,						
						"remarks": self.remarks
						})
				)
	
		if self.deducts:
			for a in self.deducts:
				gl_entries.append(
					self.get_gl_dict({"account": a.accounts,
									"debit": flt(a.amount),
									"debit_in_account_currency": flt(a.amount),
									"cost_center": self.cost_center,
									"party_check": 1,
									"party_type": a.party_type,
									"party": a.party,
									"reference_type": self.doctype,
									"reference_name": self.name,
									"remarks": self.remarks
								})
                )


		make_gl_entries(gl_entries, cancel=(self.docstatus == 2),update_outstanding="No", merge_entries=False)

	def get_transactions(self):
		if not self.branch or not self.customer or not self.payment_for:
			frappe.throw("Branch, Customer and Payment For is Mandatory")
		transactions = frappe.db.sql("select name, outstanding_amount, customer from `tab{0}` where customer = '{1}' and branch = '{2}' and outstanding_amount > 0 and docstatus = 1 order by creation".format(self.payment_for, self.customer, self.branch), as_dict=1)
		self.set('items', [])

		total = 0
		for d in transactions:
			d.reference_type = self.payment_for
			d.reference_name = d.name
			d.allocated_amount = d.outstanding_amount
			row = self.append('items', {})
			row.update(d)
			total += flt(d.outstanding_amount)
		self.receivable_amount = total
		self.actual_amount = total
