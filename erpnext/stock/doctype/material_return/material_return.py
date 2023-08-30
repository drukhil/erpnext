# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.stock.utils import get_stock_balance
from frappe.utils import cstr, flt, cint, get_datetime
from erpnext.custom_utils import check_future_date, get_branch_cc, prepare_gl, prepare_sl
from erpnext.controllers.stock_controller import StockController

class MaterialReturn(StockController):
	def validate(self):
		check_future_date(self.posting_date)
		self.validate_details()
	

	def validate_details(self):
		for a in self.items:
			qty, rate = get_stock_balance(a.item_code, a.warehouse, self.posting_date, self.posting_time, with_valuation_rate=True)
			item_name, uom, item_group, expense_account = frappe.db.get_value("Item", a.item_code, ["item_name", "stock_uom", "item_group", "expense_account"])
			a.item_group = item_group
			a.stock_uom = uom
			a.valuation_rate = rate
			a.basic_rate = rate
			a.item_name = item_name
			a.amount = flt(a.qty) * flt(a.basic_rate)
			a.expense_account = expense_account

	def on_submit(self):
		self.make_sl_entry()
		self.make_gl_entry()

	def on_cancel(self):
		self.make_sl_entry()
		self.make_gl_entry()

	def make_sl_entry(self):
		sl_entries = []
		for d in self.get('items'):
			if cstr(d.warehouse):
				sl_entries.append(self.get_sl_entries(d, {
					"warehouse": cstr(d.warehouse),
					"actual_qty": flt(d.qty),
					"incoming_rate": flt(d.valuation_rate, 2)
				}))

		if self.docstatus == 2:
				sl_entries.reverse()

		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')
	
	def make_gl_entry(self):
		gl_entries = []

		for a in self.items:
			wh_account = frappe.db.get_value("Account", {"account_type": "Stock", "warehouse": a.warehouse}, "name")
			if not wh_account:
				frappe.throw(str(self.warehouse) + " is not linked to any account.")

			expense_account = frappe.db.get_value("Item", a.item_code, "expense_account")
			if not expense_account:
				frappe.throw("Setup Default Expense Account in Item for {}".format(a.item_name))
							
			gl_entries.append(
				prepare_gl(self, {"account": wh_account,
						 "debit": flt(a.amount),
						 "debit_in_account_currency": flt(a.amount),
						 "cost_center": self.cost_center,
						 "remarks": a.remarks
						 
						})
				)

			gl_entries.append(
				prepare_gl(self, {"account": expense_account,
						 "credit": flt(a.amount),
						 "credit_in_account_currency": flt(a.amount),
						 "cost_center": self.cost_center,
						 "remarks": a.remarks
						 
						})
				)

		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries
			make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=True)
