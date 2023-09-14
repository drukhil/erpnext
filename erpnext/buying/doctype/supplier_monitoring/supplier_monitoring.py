# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate, formatdate, today, get_first_day, date_diff, add_years, flt

class SupplierMonitoring(Document):
	def validate(self):
		if not self.items:
			frappe.throw("No items found for the the given Purchase Order")
		self.check_requirements()
		self.update_ld()
		self.check_duplicate()
		self.validate_smt_po_qty()
		self.calc_ld_total()

	def calc_ld_total(self):
		tot = 0.0
		for a in self.get("items"):
			tot += flt(a.liquidated_damage)
		self.total = tot

	def validate_smt_po_qty(self):
		for d in self.get("items"):
			po_bal_qty = flt(frappe.db.sql("""select (qty - received_qty) as bal_qty 
						from `tabPurchase Order Item` 
						where name=%s and parent=%s and docstatus=1 """, (str(d.purchase_order_item), self.purchase_order)
					)[0][0]
				)
			if flt(d.received_quantity) > flt(po_bal_qty):
				frappe.throw("Received Quantity {0} cannot be greater than the difference of PO quantity and received quantity {1}".format(d.received_quantity, flt(po_bal_qty)))

	def update_ld(self):
		for a in self.get("items"):
			# if getdate(a.received_date):
			# 	a.days_delayed = date_diff(a.received_date, a.schedule_date)
			a.balance_quantity =flt(a.qty) - flt(a.received_quantity)
			a.received_amount = flt(a.rate) * flt(a.received_quantity)
			a.undelivered_amount =flt(a.rate) * flt(a.balance_quantity)
			if a.liquidated_damage > 0:
				a.liquidated_damage = flt(a.received_amount) * flt(a.days_delayed) * .001
			else:
				a.liquidated_damage == 0
			

	def check_duplicate(self):
		data = []
		for d in self.get("items"):
			if d.item_code not in data:
				data.append(d.item_code)
			else:
				frappe.throw("Duplicate Item entry at #Row. {}".format(d.idx))
		# if frappe.db.exists("Supplier Monitoring", {'purchase_order': self.purchase_order, 'docstatus': 1}):
        #     		frappe.throw(('You have already created a Supplier Monitoring transaction for the purchase Order,  <b>{}</b>, This is the document number <b>{}</b>'.format(self.purchase_order, self.name)))
	

	def get_items(self, po):
		data = frappe.db.sql("""
			SELECT 
				item_code, item_name, uom, qty, rate, amount, schedule_date, received_qty, name as purchase_order_item from `tabPurchase Order Item` 
			WHERE	
			parent = '{0}' and docstatus = 1
		""".format(po), as_dict=1)
		
		if not data:
			frappe.throw("No items found for the Purchase Order {}".format(po))
		self.set('items', [])
		for d in data:
			if flt(d.qty) == flt(d.received_qty):
				continue
			row = self.append('items', {})
			row.received_quantity = flt(d.qty) - flt(d.received_qty)
			row.update(d)

	def check_requirements(self):		
		for a in self.get("items"):
			max_amount = flt(a.amount)*.1
			# if getdate(a.received_date) < getdate(a.schedule_date):
			# 	frappe.throw("Received Date Cannot be Earlier than Delivery Date at Row {0}".format(a.idx))
			
			if flt(a.received_quantity) > flt(a.qty):
				frappe.throw("Received Quantity cannot be greater than the PO quantity at Row {}".format(a.idx))
			if flt(a.liquidated_damage) > max_amount:
				frappe.throw("Liquidated Damage cannot be more than the 10% of the PO Amount")
			# if flt(a.received_quantity) > a.qty:
			# 	frappe.throw("Received Quantity cannot be more than the PO quantity")

@frappe.whitelist()
def calculate_durations(from_date = None, to_date = None):
	duration = date_diff(to_date, from_date)
	if duration > 100:
		frappe.throw("Days Delayed cannot be more than 100 days")
	elif duration < 0:
		return 0
	else:
		return duration