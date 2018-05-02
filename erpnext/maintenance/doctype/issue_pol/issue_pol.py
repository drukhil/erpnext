# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.desk.reportview import get_match_cond
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import flt, getdate
from erpnext.custom_utils import check_future_date, get_branch_cc, prepare_gl, prepare_sl, check_budget_available
from erpnext.controllers.stock_controller import StockController

class IssuePOL(StockController):
	def validate(self):
		check_future_date(self.posting_date)
		self.validate_branch()
		self.populate_data()
		self.validate_data()
		self.validate_posting_time()
		self.validate_uom_is_integer("stock_uom", "qty")

	def validate_branch(self):
		if self.purpose == "Issue" and self.is_hsd_item and not self.tanker:
			frappe.throw("For HSD Issues, Tanker is Mandatory")

		if not self.is_hsd_item:
			self.tanker = ""

		if self.tanker and self.branch != frappe.db.get_value("Equipment", self.tanker, "branch"):
			frappe.throw("Selected Branch and Equipment Branch does not match")

	def populate_data(self):
		cc = get_branch_cc(self.branch)
		self.cost_center = cc
		warehouse = frappe.db.get_value("Cost Center", cc, "warehouse")
		if not warehouse:
			frappe.throw(str(cc) + " is not linked to any Warehouse")
		self.warehouse = warehouse

	def validate_data(self):
		if not self.purpose:
			frappe.throw("Purpose is Missing")
		if not self.cost_center or not self.warehouse:
			frappe.throw("Cost Center and Warehouse are Mandatory")

		for a in self.items:
			if not a.equipment_warehouse or not a.equipment_cost_center:
				frappe.throw("<b>"+str(a.equipment_number) + "</b> does have a Warehouse and Cost Center Defined")
			if not flt(a.qty) > 0:
				frappe.throw("Quantity for <b>"+str(a.equipment_number)+"</b> should be greater than 0")

	def on_submit(self):
		if not self.items:
			frappe.throw("Should have a POL Issue Details to Submit")

		self.update_stock_gl_ledger()

		if self.purpose == "Issue":
			self.consume_pol()

	def update_stock_gl_ledger(self):
		sl_entries = []
		gl_entries = []

		wh_account = frappe.db.get_value("Account", {"account_type": "Stock", "warehouse": self.warehouse}, "name")
		if not wh_account:
			frappe.throw(str(self.warehouse) + " is not linked to any account.")

		for a in self.items:
			from erpnext.stock.stock_ledger import get_valuation_rate
			valuation_rate = get_valuation_rate(self.pol_type, self.warehouse)

			ec = frappe.db.get_value("Equipment", a.equipment, "equipment_category")
			budget_account = frappe.db.get_value("Equipment Category", ec, "budget_account")
			if not budget_account:
				frappe.throw("Set Budget Account in Equipment Category")		

			if self.purpose == "Issue":
				sl_entries.append(prepare_sl(self, 
						{
							"actual_qty": -1 * flt(a.qty), 
							"warehouse": self.warehouse, 
							"incoming_rate": 0 
						}))

				gl_entries.append(
					prepare_gl(self, {"account": wh_account,
							 "credit": flt(valuation_rate),
							 "credit_in_account_currency": flt(valuation_rate),
							 "cost_center": self.cost_center,
							})
					)

				gl_entries.append(
					prepare_gl(self, {"account": budget_account,
							 "debit": flt(valuation_rate),
							 "debit_in_account_currency": flt(valuation_rate),
							 "cost_center": a.equipment_cost_center,
							})
					)
				
				#Do IC Accounting Entry if different branch
				if a.equipment_branch != self.branch:
					ic_account = frappe.db.get_single_value("Accounts Settings", "intra_company_account")
					if not ic_account:
						frappe.throw("Setup Intra-Company Account in Accounts Settings")

					gl_entries.append(
						prepare_gl(self, {"account": ic_account,
								 "debit": flt(valuation_rate),
								 "debit_in_account_currency": flt(valuation_rate),
								 "cost_center": self.cost_center,
								})
						)

					gl_entries.append(
						prepare_gl(self, {"account": ic_account,
								 "credit": flt(valuation_rate),
								 "credit_in_account_currency": flt(valuation_rate),
								 "cost_center": a.equipment_cost_center,
								})
						)
					
			else : #Transfer only if different warehouse
				if a.equipment_warehouse != self.warehouse:
					#Stock Ledger Entries
					sl_entries.append(prepare_sl(self, 
							{
								"actual_qty": -1 * flt(a.qty), 
								"warehouse": self.warehouse, 
								"incoming_rate": 0 
							}))

					sl_entries.append(prepare_sl(self,
							{
								"actual_qty": flt(a.qty), 
								"warehouse": a.equipment_warehouse, 
								"incoming_rate": valuation_rate
							}))

				#Do IC Accounting Entry if different branch
				if a.equipment_branch != self.branch:
					ic_account = frappe.db.get_single_value("Accounts Settings", "intra_company_account")
					if not ic_account:
						frappe.throw("Setup Intra-Company Account in Accounts Settings")

					twh_account = frappe.db.get_value("Account", {"account_type": "Stock", "warehouse": a.equipment_warehouse}, "name")
					if not twh_account:
						frappe.throw(str(self.warehouse) + " is not linked to any account.")

					gl_entries.append(
						prepare_gl(self, {"account": wh_account,
								 "credit": flt(valuation_rate),
								 "credit_in_account_currency": flt(valuation_rate),
								 "cost_center": self.cost_center,
								})
						)

					gl_entries.append(
						prepare_gl(self, {"account": twh_account,
								 "debit": flt(valuation_rate),
								 "debit_in_account_currency": flt(valuation_rate),
								 "cost_center": a.equipment_cost_center,
								})
						)

					gl_entries.append(
						prepare_gl(self, {"account": ic_account,
								 "debit": flt(valuation_rate),
								 "debit_in_account_currency": flt(valuation_rate),
								 "cost_center": self.cost_center,
								})
						)

					gl_entries.append(
						prepare_gl(self, {"account": ic_account,
								 "credit": flt(valuation_rate),
								 "credit_in_account_currency": flt(valuation_rate),
								 "cost_center": a.equipment_cost_center,
								})
						)

		if sl_entries: 
			if self.docstatus == 2:
				sl_entries.reverse()

			if getdate(self.posting_date) > getdate("2018-03-31"):
				self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')

		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries
			make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=True)

	def on_cancel(self):
		self.update_stock_gl_ledger()
		if self.purpose == "Issue":
			self.cancel_consumed_pol()

	def consume_pol(self):
		for a in self.items:
			con = frappe.new_doc("Consumed POL")	
			con.equipment = a.equipment
			con.branch = self.branch
			con.pol_type = self.pol_type
			con.date = self.posting_date
			con.qty = a.qty
			con.reference_type = "Issue POL"
			con.reference_name = self.name
			con.submit()
	
	def cancel_consumed_pol(self):
		frappe.db.sql("delete from `tabConsumed POL` where reference_type = 'Issue POL' and reference_name = %s", (self.name))

def equipment_query(doctype, txt, searchfield, start, page_len, filters):
	if not filters['branch']:
		filters['branch'] = '%'
        return frappe.db.sql("""
                        select
                                e.name,
                                e.equipment_type,
                                e.equipment_number
                        from `tabEquipment` e
                        where e.branch like %(branch)s
                        and e.is_disabled != 1
                        and e.not_cdcl = 0
                        and exists(select 1
                                     from `tabEquipment Type` t
                                    where t.name = e.equipment_type
                                      and t.is_container = 1)
                        and (
                                {key} like %(txt)s
                                or
                                e.equipment_type like %(txt)s
                                or
                                e.equipment_number like %(txt)s
                        )
                        {mcond}
                        order by
                                if(locate(%(_txt)s, e.name), locate(%(_txt)s, e.name), 99999),
                                if(locate(%(_txt)s, e.equipment_type), locate(%(_txt)s, e.equipment_type), 99999),
                                if(locate(%(_txt)s, e.equipment_number), locate(%(_txt)s, e.equipment_number), 99999),
                                idx desc,
                                e.name, e.equipment_type, e.equipment_number
                        limit %(start)s, %(page_len)s
                        """.format(**{
                                'key': searchfield,
                                'mcond': get_match_cond(doctype)
                        }),
                        {
				"txt": "%%%s%%" % txt,
				"_txt": txt.replace("%", ""),
				"start": start,
				"page_len": page_len,
                                "branch": filters['branch']
			})

