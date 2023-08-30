# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class PriorityProject(Document):
	def validate(self):
		self.get_details()
		if self.items:
			total = 0
			for d in self.items:
				total += flt(d.mandays)
				self.total_mandays= total
		
		self.calculate_values()
		self.calculate_values1()
		


	def calculate_values(self):
		for d in self.items:
			new_w = flt(d.mandays)/self.total_mandays
			d.new_weightage = new_w
			new_c = round(flt(d.percent_completed) * flt(d.new_weightage), 2)
			d.new_completion = new_c
			# frappe.msgprint("test" '{0}' '{1}' '{2}'.format(total, new_c, d.new_completion))

				
	def calculate_values1(self):
		tot = 0
		for d in self.items:
			new_c = round(flt(d.percent_completed) * flt(d.new_weightage), 2)
			d.new_completion = new_c
			tot +=d.new_completion
			self.total_completion = tot

	

	def get_details(self):
		query = """ select name as project, physical_progress_weightage, percent_completed, physical_progress, mandays from 
                                `tabProject` where parent_project= '{0}' 
                                and priority ='High'
                                """.format(self.parent_project)	
		

		entries = frappe.db.sql(query, as_dict=True)
		if not entries:
			frappe.msgprint("No Record Found")

		self.set('items', [])

		for d in entries:
			row = self.append('items', {})
			row.update(d)

def update_priority():
	pro = frappe.db.sql("""select name from `tabPriority Project`""",  as_dict=True)
	for a in pro:
		print(str(a))
		doc = frappe.get_doc("Priority Project", a)
		doc.save()