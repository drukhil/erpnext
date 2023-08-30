# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate, formatdate, today, get_first_day, date_diff, add_years, flt

class DelayFactor(Document):
	def validate(self):
		self.no_of_days = date_diff(self.to_date, self.from_date) + 1
		self.update_project()

	def update_tasks(self):
		self.set('items', [])
		tasks = frappe.db.sql(""" select name, parent, task,  start_date, end_date from `tabActivity Tasks` where 
			parent = "{0}" and start_date >= '{1}'
			""".format(self.project, self.from_date), as_dict = 1, debug = 1)
		if not tasks:
			frappe.throw(""" No Work Schedule Defined for "{0}" """.format(self.project))
		for a in tasks:
			from_date = add_days(a.start_date, self.no_of_days)
			to_date = add_days(a.end_date, self.no_of_days)
			self.append("items", {
			"project_task": a.name,
			"task_name": a.task,
			"actual_from_date": a.start_date,
			"actual_to_date": a.end_date,
			"new_from_date": from_date,
			"new_to_date": to_date,
			"is_new_task": 0
                        })

	def update_project(self):
		for a in self.get('items'):
			#max_date = getdate(a.new_to_date)
			#if getdate(a.new_to_date) > max_date:
			#	max_date = a.new_to_date

			if not a.is_new_task:
				doc = frappe.get_doc('Activity Tasks', a.project_task)
				doc.db_set('start_date', a.new_from_date)
				doc.db_set('end_date', a.new_to_date)
		
		project = frappe.get_doc("Project", self.project)
		#if project.expected_end_date < max_date:
		#	project.expected_end_date = max_date
		#project.task_dates()
		#project.make_target_entries()
		project.expected_end_date = add_days(project.expected_end_date, self.no_of_days)
		project.validate()

@frappe.whitelist()
def calculate_durations(from_date = None, to_date = None):
        duration = date_diff(to_date, from_date) + 1
        return duration		
