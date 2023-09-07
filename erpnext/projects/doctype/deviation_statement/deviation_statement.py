# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
class DeviationStatement(Document):
	def validate(self):
		self.calculate_rate()
		self.calculate_rebate()

	def calculate_rate(self):
		amount = amount_within_20 = amount_beyond_20 = financial_implication = 0.0
		for a  in self.get('items'):
			a.rate_within_20 = a.rate_beyond_20 = a.rate
			#within 20% DL
			if flt(a.executed_quantity) < flt(a.quantity):
				a.quantity_within_20 = flt(a.quantity) * 0.8
			else:
				a.quantity_within_20 = flt(a.quantity) * 1.2
			#beyong 20% DL
			if flt(a.executed_quantity)  <= flt(a.quantity_within_20):
				a.quantity_beyond_20 = 0.0
			else:
				a.quantity_beyond_20 = flt(a.executed_quantity) - flt(a.quantity_within_20)
			#Amount	
			a.amount = flt(a.rate) * flt(a.quantity)
			a.amount_within_20 = flt(a.rate_within_20) * flt(a.quantity_within_20)
			a.amount_beyond_20 = flt(a.rate_beyond_20) * flt(a.quantity_beyond_20)
			a.financial_implication = flt(a.amount_within_20) + flt(a.amount_beyond_20) - flt(a.amount)
			amount += flt(a.amount)
			amount_within_20 += flt(a.amount_within_20)
			amount_beyond_20  += flt(a.amount_beyond_20)
			financial_implication += flt(a.financial_implication)

			#Check
			a.check = (flt(a.quantity_beyond_20) * flt(a.rate))/flt(a.amount) * 0.01
		self.amount = flt(amount)
		self.amount_within_20 = flt(amount_within_20)
		self.amount_beyond_20 = flt(amount_beyond_20)
		self.financial_implication = flt(financial_implication)

	def calculate_rebate(self):
		self.rebate_amount = self.rebate_within_20 = self.rebate_boyond_20 = flt(self.rebate)
		if flt(self.rebate_in_percent):
			if flt(self.rebate) > 100:
				frappe.throw("Rebate % Cannot Exceed 100%", title = 'Invalid UI')
			self.rebate_amount        = flt(self.rebate) * 0.01 * flt(self.amount)
			self.rebate_within_20     = flt(self.rebate) * 0.01 * flt(self.amount_within_20)
			self.rebate_beyond_20     = flt(self.rebate) * 0.01 * flt(self.amount_beyond_20)
		self.after_rebate         = flt(self.amount) - flt(self.rebate_amount)
		self.after_rebate_within  = flt(self.amount_within_20) - flt(self.rebate_within_20)
		self.after_rebate_beyond  = flt(self.amount_beyond_20) - flt(self.rebate_beyond_20)

	def get_boq_lists(self):
		init_contract_amount = frappe.db.get_value("Project", self.project, "project_value")
		result = frappe.db.sql("""
			select boq_item.name as ref_name, boq_item.boq_code, boq_item.item, boq_item.uom,
			boq_item.is_group, boq_item.ref_type, boq_item.quantity, boq_item.amount,
			boq_item.balance_quantity, boq_item.rate, boq_item.remarks
			from  `tabBOQ` boq, `tabBOQ Item` boq_item
			where boq.name = boq_item.parent and boq.project = '{0}' and
			boq_item.quantity != boq_item.balance_quantity
			and boq.docstatus = 1 order by boq.name, boq_item.idx asc """.format(self.project), as_dict = 1)
		self.set('items', [])
		for d in result:	
			d.executed_quantity = flt(d.quantity) - flt(d.balance_quantity)
			d.rate_within_20 = flt(d.rate)
			d.rate_beyond_20 = flt(d.rate)
			d.quantity_within_20 = flt(d.quantity) * 0.8 if flt(d.executed_quantity, 2) < flt(d.quantity, 2) else flt(d.quantity) * 1.2
			d.quantity_beyond_20 = 0 if flt(d.executed_quantity, 2) == flt(d.quantity_within_20, 2) else flt(d.executed_quantity, 2) - flt(d.quantity_within_20, 2)
			d.check = (flt(d.quantity_beyond_20 * d.rate, 2)/init_contract_amount) * 100
			d.amount_within_20 = flt(d.quantity_within_20, 2) * d.rate_within_20
			d.amount_beyond_20 = flt(d.quantity_beyond_20, 2) * d.rate_beyond_20
			d.financial_implication = (flt(d.amount_within_20) + flt(d.amount_beyond_20)) - d.amount
			row = self.append('items', {})
			row.update(d)
