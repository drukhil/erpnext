# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
import datetime
from frappe.model.naming import make_autoname
from frappe.utils import add_days, getdate, nowdate, formatdate, today, get_first_day, date_diff, add_years, flt
from erpnext.accounts.utils import get_fiscal_year

class Design(Document):
	def autoname(self):
        	self.name = self.design_name

	def validate(self):
		# frappe.throw("i am here")
		self.flags.dont_sync_tasks = True
		self.name = self.design_name
		self.check_required_data()
		self.validate_dates()
		self.task_dates()
		self.calculations()
		# self.update_progress()
		

	def on_submit(self):
		# frappe.throw("inside submit")
		self.flags.dont_sync_tasks = True
                self.update_progress()
		self.validate_dates()
		self.task_dates()
	
	def on_update_after_submit(self):
		# frappe.throw("inside update")
		self.flags.dont_sync_tasks = True
		if not self.completion_date:
			frappe.throw("Date of Update is Required", title="Missing Input")
	
		if getdate(self.completion_date) > getdate(nowdate()):
			frappe.throw(_("Cannot Update For Future Dates"))

		self.physical_progress = round(flt(self.physical_progress), 7)
		self.update_progress(update=True)
		if self.percent_completed == 100:
			self.db_set("status", "Completed")
		if self.percent_completed < 100:
			self.db_set("status", "Ongoing")
		

	def check_required_data(self):
		if not self.expected_start_date or not self.expected_end_date:
			frappe.throw("<b> Expected Start/End Date Is Required </b> ", title = 'Missing Input')
		
		if not self.physical_progress_weightage:
			frappe.throw("<b> Activity Weightage Is required </b>", title = 'Missing Input')
		if not self.project_category:
			frappe.throw("<b> Activity Category Is Required </b>", title = 'Missing Input')
		if not self.project_sub_category:
			frappe.throw("<b> Activity Sub Category Is Required </b>", title = 'Missing Input')
		if not self.parent_project:
			frappe.throw("<b> Academy(Parent Activity) Is Required </b>", title = 'Missing Input')
		
	def validate_dates(self):
		if self.expected_start_date and self.expected_end_date:
			if getdate(self.expected_start_date) > getdate(self.expected_end_date):
				frappe.throw("Start Date Cannot be before End Date")
			self.total_duration = date_diff(self.expected_end_date, self.expected_start_date) + 1
		self.physical_progress = 0.0
		self.percent_completed = 0.0
		self.percent_completed_old = 0.0

	def task_dates(self):
		total_duration = 0.0		
		for a in self.get("activity_tasks"):
			if getdate(a.start_date) > getdate(a.end_date):
				frappe.throw("Task Start Date Cannot be Greater than End Date at Row {0}".format(a.idx))
			if flt(a.task_completion_percent) > 100:
				frappe.throw(" Percent Cannot exceed 100%")

			if flt(a.task_completion_percent) < 0:
				frappe.throw("Percent Cannot be less than 0%")

			if getdate(a.start_date) < getdate(self.expected_start_date):
				frappe.throw("Task Start Date Cannot be before Activity Start Date at Row {0}".format(a.idx))

			if getdate(a.end_date) > getdate(self.expected_end_date):
				frappe.throw("Task End Date Cannot Exceed the Activity End Date at Row {0}".format(a.idx))
			
			a.task_duration = date_diff(a.end_date, a.start_date) + 1	
			if not a.task_duration:
				frappe.throw("Task Duration needed at Row <b> {0} </b> ".format(a.idx))	
			# total_duration = self.total_duration()
			a.one_day_weightage = round(flt(a.task_weightage)/flt(a.task_duration), 7)
			# a.one_day_weightage_overall = flt(a.one_day_weightage)/100 * flt(self.physical_progress_weightage)
			a.task_achievement_percent = 0.0	
			a.one_day_achievement = 0.0
			# a.task_completion_percent = 0.0

	def calculations(self):
		total_days = 0.0
        	contributed = 0.0
        	for a in self.get("activity_tasks"):
            		a.one_day_weightage = round(flt(a.task_weightage)/flt(a.task_duration), 7)
            		contributed += round(flt(a.task_achievement_percent), 7)
        	self.percent_completed = round(contributed * 100, 7)
    		self.physical_progress = round(flt(self.percent_completed)*flt(self.physical_progress_weightage), 5)
	
	

	def update_progress(self, update=False):
		total_achievement = 0.0
        	for a in self.get("activity_tasks"):
		#	total_achievement = 0.0
			if a.task_completion_percent > 100:
				frappe.throw("Task Completion Percent Cannot Exceed 100 % at Sl. <b> {0} </b>".format(a.idx))
			a.task_achievement_percent = round(flt(a.task_completion_percent)/100 * flt(a.task_weightage), 7)
			a.one_day_achievement = round(flt(a.task_achievement_percent)/flt(a.task_duration), 7)
			total_achievement += flt(a.task_achievement_percent)
        	#self.percent_completed = round(total_achievement, 3)
		#self.physical_progress = round(flt(self.percent_completed)*flt(self.physical_progress_weightage), 5)
		if not update:
			self.percent_completed = round(total_achievement * 100, 3)
			self.physical_progress = round(flt(self.percent_completed)*flt(self.physical_progress_weightage), 5)
		else:
			self.db_set("percent_completed", round(total_achievement * 100, 3))
			self.db_set("physical_progress", round(round(total_achievement, 3)*flt(self.physical_progress_weightage), 5))
			self.reload()

@frappe.whitelist()
def calculate_durations(from_date = None, to_date = None):
	duration = date_diff(to_date, from_date) + 1
	return duration
	
