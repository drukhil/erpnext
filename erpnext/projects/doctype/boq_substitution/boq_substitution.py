# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.model.naming import make_autoname
from frappe.utils import cstr, flt, getdate, today, nowdate, now_datetime

class BOQSubstitution(Document):
	def validate(self):
		self.remove_unselected_items()
		self.update_defaults()
		self.validate_boq_and_items()
		#self.append_substituted_boq()
		#self.log_old_boq()

	def on_submit(self):
		self.log_old_boq()
		self.append_substituted_boq()
		self.insert_new_boq_items()
		self.insert_substitution_history()
		self.update_boq_and_project()

	def on_cancel(self):
		self.insert_substitution_history()
		self.insert_new_boq_items()
		self.log_old_boq()
		self.update_boq_and_project()

	def remove_unselected_items(self):
		to_remove = []
		for a in self.get('boq_item'):
			if not a.substitute:
				to_remove.append(a)

		[self.remove(d) for d in to_remove]
		if not self.get('boq_item'):
			frappe.throw("Substitution Item is Mandiatory")

	#Will check if the item to be replaced is already used and perform action accordingly
	def check_used_items(self):
		pass


	def update_defaults(self):
		item_group = ""
		total_amount       = 0.0
		initial_amount     = 0.0
		implication_amount = 0.0
		idx = 0
		for item in self.boq_item:
			idx += 1
			if item.is_group:
				item_group              = item.item
				item.quantity           = 0.0
				item.rate               = 0.0
				item.amount             = 0.0
				item.initial_amount     = 0.0
				item.implication_amount = 0.0
				item.claimed_quantity   = 0.0
				item.claimed_amount     = 0.0
				item.booked_quantity    = 0.0
				item.booked_amount      = 0.0
				item.balance_quantity   = 0.0
				item.balance_amount     = 0.0
			else:
				item.amount             = flt(item.quantity)*flt(item.rate)
				item.implication_amount = flt(item.amount) - flt(item.initial_amount)
				item.initial_amount     = flt(frappe.get_doc("BOQ Item", item.boq_item_name).amount)
			if item.amount <= 0:
					frappe.throw("Amount Should be Greater Than Zero at Index '{0}'".format(item.idx))

			total_amount        += flt(item.amount)
			initial_amount      += flt(item.initial_amount)
			implication_amount  += flt(item.implication_amount)
				
			item.parent_item = item_group
			item.claimed_quantity   = 0.0
			item.claimed_amount     = 0.0
			item.booked_quantity    = 0.0
			item.booked_amount      = 0.0
			item.balance_rate       = 0.0
			item.balance_quantity   = 0.0
			item.balance_amount     = 0.0
			item.idx                = idx
		self.total_amount       = flt(total_amount)
		self.initial_amount     = flt(initial_amount)
		self.implication_amount = flt(implication_amount)

		if flt(self.total_amount) <= 0:
			frappe.throw("Total Amount Should be Greater Than Zero")
	
	def validate_boq_and_items(self):
				# validate substitution date
				if self.substitution_date  < self.boq_date:
					frappe.throw(_("Substitution Date cannot be earlier to BOQ Date"),title="Invalid Data")
				elif self.substitution_date > today():
					frappe.throw(_("Substitution Date cannot be a future date"),title="Invalid Data")

				# validate items
				for i in self.boq_item:
					if i.substitute:
						if i.is_group:
							if flt(i.quantity) or flt(i.amount):
								frappe.throw(_("Row#{0} : Quantity/Amount against group items not permitted.").format(i.idx), title="Not permitted")	
						else:
							if not flt(i.quantity) or not flt(i.amount):
								frappe.throw(_("ROw#{0} : Quantity/Amount/Rate Cannot be Zero.").format(i.idx), title="Invalid Data")



	def append_substituted_boq(self):
		for d in self.boq_item:
			if d.substitute:
				new_doclist = get_mapped_doc("BOQ Item", d.boq_item_name, {
						"BOQ Item": {
								"doctype": "Initial BOQ",
								"field_map": {
												"amount": "amount"
												}
										}
								})
				new_doclist.parentfield = 'initial_boq_item'
				new_doclist.parent = self.name
				new_doclist.parenttype = self.doctype
				new_doclist.ref_type = self.doctype
				new_doclist.save(ignore_permissions=True)
				new_doclist.submit()
				frappe.db.commit()


	def log_old_boq(self):
		for d in self.boq_item:
			if d.substitute:
				if self.docstatus == 2:
					#frappe.delete_doc("Initial BOQ", {'ref_name': d.name})
					frappe.db.sql(""" delete from `tabInitial BOQ` where ref_name= '{0}'""".format(d.name))
				else:
					new_doclist = get_mapped_doc("BOQ Item", d.boq_item_name, {
						"BOQ Item": {
							"doctype": "Initial BOQ",
							"field_map": {
									"parent": "parent",
									"parenttype": "parenttype",
									}
								}
							})
					new_doclist.parentfield = 'initial_boq_item'
					new_doclist.ref_type = self.doctype
					new_doclist.ref_name = d.name
					new_doclist.save(ignore_permissions=True)
					new_doclist.submit()
					frappe.db.commit()
	
	def insert_new_boq_items(self):
		boq = frappe.get_doc("BOQ", self.boq)
		for d in self.boq_item:
			if d.substitute:
				if self.docstatus == 2:
					#frappe.delete_doc("BOQ Item", {'ref_name': d.name})
					frappe.db.sql(""" delete from `tabBOQ Item` where ref_name  = '{0}'""".format(d.name))
					#restore the old boq
					frappe.db.sql(""" update `tabBOQ Item` set parentfield = 'boq_item' where name = '{0}'
					""".format(d.boq_item_name))

				else:
					boq_item = frappe.get_doc("BOQ Item", d.boq_item_name)
					boq_item.boq_code = d.boq_code
					boq_item.item = d.item
					boq_item.uom = d.uom
					boq_item.is_group = d.is_group
					boq_item.no =  d.no
					boq_item.length = d.length
					boq_item.height = d.height
					boq_item.breath = d.breath
					boq_item.coefficient = d.coefficient
					boq_item.quantity = d.quantity
					boq_item.rate = d.rate
					boq_item.rate_analysis = d.rate_analysis
					boq_item.amount = d.amount
					boq_item.claimed_quantity =  0.0
					boq_item.adjustment_amount = 0.0
					boq_item.claimed_amount =  0.0
					boq_item.booked_quantity = 0.0
					boq_item.booked_amount =  0.0
					boq_item.balance_quantity =  flt(d.quantity)
					boq_item.balance_rate =  flt(d.rate)
					boq_item.balance_amount =  flt(d.amount)
					boq_item.remarks = d.remarks
					boq_item.ref_type = d.parenttype
					boq_item.ref_name = d.name
					boq_item.idx = boq_item.idx
					boq_item.insert(ignore_permissions=True)
					boq_item.submit()
					frappe.db.sql(""" update `tabBOQ Item` set parentfield = '' where name = '{0}'""".format(d.boq_item_name))
					#frappe.db.sql(""" delete from `tabBOQ Item` where name = '{0}'""".format(d.boq_item_name))

	def insert_substitution_history(self):
				boq = frappe.get_doc("BOQ", self.boq)
				if self.docstatus == 2:
						frappe.db.sql(""" 
								delete from `tabBOQ Substitution History` where parent='{boq}' and  transaction_name = '{transaction_name}'
						""".format(boq = self.boq, transaction_name=self.name))
				else:
						boq.append("boq_substitution_item",{
								"transaction_type": self.doctype,
								"transaction_date": self.substitution_date,
								"transaction_name": self.name,
								"initial_amount":  flt(boq.total_amount),
								"substitution_amount": flt(self.total_amount),
								"final_amount":  flt(boq.total_amount) + flt(self.implication_amount),
								"owner": frappe.session.user,
								"creation": now_datetime(),
								"modified_by": frappe.session.user,
								"modified": now_datetime()
						})
						boq.save(ignore_permissions=True)
						boq.submit()

	def update_boq_and_project(self):
				#update Total Amount for BOQ and Project 
			if self.total_amount:
				mul_factor = -1 if self.docstatus == 2 else 1
				# Update BOQ
				boq_doc = frappe.get_doc("BOQ", self.boq)
				boq_doc.total_amount   = flt(boq_doc.total_amount) + flt(self.implication_amount) * flt(mul_factor)
				boq_doc.balance_amount = flt(boq_doc.balance_amount) + flt(self.implication_amount) * flt(mul_factor)
				boq_doc.substitution_amount = flt(boq_doc.substitution_amount) + flt(self.implication_amount) * flt(mul_factor)
				boq_doc.save(ignore_permissions = True)
				frappe.db.commit()

				# Update Project
				pro_doc = frappe.get_doc("Project", self.project)
				pro_doc.flags.dont_sync_tasks = True
				pro_doc.project_value = flt(pro_doc.project_value) + flt(self.implication_amount) * flt(mul_factor)
				pro_doc.save(ignore_permissions = True)
				frappe.db.commit()

@frappe.whitelist()
def get_boq_list(boq):
		result = frappe.db.sql("""
				select *
				from `tabBOQ Item`
				where parent = '{boq}'
				and docstatus = 1 and quantity = balance_quantity  order by idx asc
				""".format(boq=boq) , as_dict=True)

		return result
