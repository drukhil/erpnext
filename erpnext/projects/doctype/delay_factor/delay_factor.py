# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate, formatdate, today, get_first_day, date_diff, add_years, flt, now

class DelayFactor(Document):
	def validate(self):
		self.no_of_days = date_diff(self.to_date, self.from_date) + 1
		if not self.project_end_date:
			self.project_from_date = frappe.db.get_value("Project", self.project, "expected_start_date")
			self.project_end_date = frappe.db.get_value("Project", self.project, "expected_end_date")
		if not self.branch:
			self.branch = frappe.db.get_value("Project", self.project, "branch")

	def on_submit(self):
		# self.posting_date = now()
		self.db_set('posting_date', now())
		for d in frappe.db.get_list("Delay Factor", {"posting_date": ("<", self.posting_date), "docstatus": 0, "project": self.project}):
			frappe.throw("Another Delay Factor {} created before this for same Project. Please complete it first.".format(frappe.get_desk_link("Delay Factor", d.name)))
		self.update_project()

	def on_cancel(self):
		for d in frappe.db.get_list("Delay Factor", {"posting_date": (">", self.posting_date), "docstatus": 1, "project": self.project}):
			frappe.throw("There exist another Delay Factor {} created after this for same Project.".format(frappe.get_desk_link("Delay Factor", d.name)))
		self.update_old_dates()

	def update_old_dates(self):
		for a in self.get('items'):
			if not a.is_new_task:
				doc = frappe.get_doc('Activity Tasks', a.project_task)
				doc.db_set('start_date', a.actual_from_date)
				doc.db_set('end_date', a.actual_to_date)
		
		project = frappe.get_doc("Project", self.project)
		project.db_set('expected_end_date', getdate(self.project_end_date))
		project.validate()

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
		max_end_date = frappe.db.sql("select max(end_date) m_end_date from `tabActivity Tasks` where parent='{}'".format(frappe.db.escape(self.project)), as_dict=1)

		project.db_set('expected_end_date', getdate(max_end_date[0]['m_end_date']))
		#if project.expected_end_date < max_date:
		#	project.expected_end_date = max_date
		#project.task_dates()
		#project.make_target_entries()
		# project.expected_end_date = add_days(project.expected_end_date, self.no_of_days)
		project.validate()
		# project.save()

@frappe.whitelist()
def calculate_durations(from_date = None, to_date = None):
        duration = date_diff(to_date, from_date) + 1
        return duration		
