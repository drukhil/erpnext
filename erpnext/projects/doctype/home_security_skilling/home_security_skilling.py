# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate, formatdate, today, get_first_day, date_diff, add_years, flt, now

class HomeSecuritySkilling(Document):
	def validate(self):
		self.validate_fields()
		if self.is_group:
			self.parent_project = ""
			self.parent_cost_center = "GA-Jamtsholing - GYALSUNG"
			self.project_category = ""
			self.project_sub_category = ""
		self.check_required_data()
		self.validate_dates()
		self.task_dates()
		if self.is_group:
			self.overall_mandays = self.mandays
		else:
			doc = frappe.get_doc("Home Security Skilling", self.parent_project)
			self.overall_mandays = doc.mandays
			self.make_group()
			self.update_milestone_date()
		self.physical_progress_weightage = round(flt(self.mandays)/flt(self.overall_mandays) * 100, 3)

	def validate_fields(self):
		if not self.cost_center:
			self.cost_center = frappe.db.get_value("Cost Center", {"branch": self.branch}, "name")
	
	def on_submit(self):
		if not self.is_group and not len(self.get("activity_tasks")):
			frappe.throw("Activity task detail is missing.")
		self.validate_dates()
		self.task_dates()
		self.update_progress()

	def on_update_after_submit(self):
		if getdate(self.completion_date) > getdate(nowdate()):
			self.db_set('completion_date', now())
			frappe.throw(_("Cannot Update For Future Dates"))
		if getdate(self.completion_date) == '':
			frappe.throw("Select Date of Update!")
		self.physical_progress = round(flt(self.physical_progress), 7)
		if not self.is_group:
			self.make_tsk_group()
			self.update_progress(update=True)
		self.set_status()

		self.post_achievement_entries()
		self.update_expense()	
		if not self.is_group:
			self.update_total_expense()
		
	def check_required_data(self):
		if not self.expected_start_date or not self.expected_end_date:
			frappe.throw("<b> Expected Start/End Date Is Required </b> ", title = 'Missing Input')
		if not self.overall_mandays:
			frappe.throw("<b> Mandays for Academy Is Required </b> ", title = 'Missing Input')
		if not self.mandays:
			frappe.throw("<b> Mandays for Activity Is Required </b>", title = 'Missing Input')
		if not self.physical_progress_weightage:
			frappe.throw("<b> Activity Weightage Is required </b>", title = 'Missing Input')
		if not self.is_group and not self.project_category:
			frappe.throw("<b> Activity Category Is Required </b>", title = 'Missing Input')
		if not self.is_group and not self.project_sub_category:
			frappe.throw("<b> Activity Sub Category Is Required </b>", title = 'Missing Input')
		if not self.is_group and not self.parent_project:
			frappe.throw("<b> Academy(Parent Activity) Is Required </b>", title = 'Missing Input')
		if not self.holiday_list:
			frappe.throw("<b> Holiday List Is Missing </b>", title = 'Missing Input')
		#if not self.is_group and not self.reference_budget:
		#	frappe.msgprint("<b> Budget Not Defined!, Kindly Contact Finance Manager </b>", title = 'For Information')
		if flt(self.mandays) > flt(self.overall_mandays):
			frappe.throw("<b> Activity Mandays Cannot be greather than Academy Mandays </b>", title = 'Invalid Input')

	def validate_dates(self):
		if self.expected_start_date and self.expected_end_date:
			if getdate(self.expected_start_date) > getdate(self.expected_end_date):
				frappe.throw("Start Date Cannot be before End Date")
			holiday  = holiday_list(self.expected_start_date, self.expected_end_date, self.holiday_list)
			self.total_duration = date_diff(self.expected_end_date, self.expected_start_date) + 1 - flt(holiday)
			self.man_power_required = round(flt(self.mandays)/flt(self.total_duration))
		self.physical_progress = 0.0
		self.percent_completed = 0.0
		self.percent_completed_old = 0.0

	def task_dates(self):
		total_duration = 0.0		
		for a in self.get("activity_tasks"):
			""" first task should be a milestone """
			if a.idx == 1 and not a.is_milestone:
				frappe.throw("First Task list should start as Milestone at Row: {0}".format(a.idx))
			if not a.is_milestone and getdate(a.start_date) > getdate(a.end_date):
				frappe.throw("Task Start Date Cannot be Greater than End Date at Row {0}".format(a.idx))
			if flt(a.task_completion_percent) > 100:
				frappe.throw(" Percent Cannot exceed 100%")

			if flt(a.task_completion_percent) < 0:
				frappe.throw("Percent Cannot be less than 0%")

			if not a.is_milestone and getdate(a.start_date) < getdate(self.expected_start_date):
				frappe.throw("Task Start Date Cannot be before Activity Start Date at Row {0}".format(a.idx))

			if not a.is_milestone and getdate(a.end_date) > getdate(self.expected_end_date):
				frappe.throw("Task End Date Cannot Exceed the Activity End Date at Row {0}".format(a.idx))
			
			if not a.is_milestone:
				holiday  = holiday_list(a.start_date, a.end_date, self.holiday_list)
				a.task_duration = date_diff(a.end_date, a.start_date) + 1 - flt(holiday)	
				if not a.task_duration:
					frappe.throw("Cannot Schedule Task on Off Days at Row <b> {0} </b> ".format(a.idx))	
				total_duration = self.total_task_duration()
				#a.task_weightage = round(flt(a.task_duration)/flt(total_duration)*self.physical_progress_weightage, 7)
				a.task_weightage = round(flt(a.task_duration)/flt(total_duration) * 100, 7)
				a.one_day_weightage = round(flt(a.task_weightage)/flt(a.task_duration), 7)
				a.one_day_weightage_overall = flt(a.one_day_weightage)/100 * flt(self.physical_progress_weightage)
				a.task_achievement_percent = 0.0	
				a.one_day_achievement = 0.0
				a.task_completion_percent = 0.0

	def total_task_duration(self):
		total_duration = 0.0
		for a in self.get("activity_tasks"):
			if a.is_milestone:
				a.task_duration = 0
			total_duration += flt(a.task_duration)
		return total_duration

	def make_group(self):
		# self.task_dates()
		group_list = frappe.db.sql("""
								select t1.name, t1.task, t1.idx, t1.is_milestone,
										(select ifnull(min(t2.idx),9999)
											from  `tabHSS Activity Task` as t2
											where t2.parent  = t1.parent
											and   t2.is_milestone = t1.is_milestone
											and   t2.idx > t1.idx
										) as max_idx
								from `tabHSS Activity Task` as t1
								where t1.parent = "{0}"
								and   t1.is_milestone = 1
								order by t1.idx
						""".format(self.name), as_dict=1)
		for a in group_list:
			frappe.db.sql(""" update `tabHSS Activity Task` set task_group = '' where name = '{0}' and is_milestone = 1 """.format(a.name, self.name))
			frappe.db.sql(""" update  `tabHSS Activity Task` set task_group = '{0}{1}' where  idx between {1} and {2} and parent = "{3}" and name != '{0}'""".format(a.name, a.idx, a.max_idx, self.name))

	def update_milestone_date(self):
		for a in frappe.db.sql(""" select name, idx from `tabHSS Activity Task` where is_milestone = 1 and parent = "{0}" 
			""".format(self.name), as_dict = 1):
			date_line = frappe.db.sql(""" select max(end_date) as max_date, min(start_date) as min_date from `tabHSS Activity Task` 
                        where task_group = '{0}{1}' and is_milestone = 0""".format(a.name, a.idx), as_dict = 1)
			frappe.db.sql(""" update `tabHSS Activity Task` set start_date='{0}', end_date='{1}' where  name = '{2}'
						""".format(date_line[0].min_date, date_line[0].max_date, a.name))

	def update_progress(self, update=False):
		total_achievement = 0.0
		for a in self.get("activity_tasks"):
			if a.task_completion_percent > 100:
				frappe.throw("Task Completion Percent Cannot Exceed 100 % at Sl. <b> {0} </b>".format(a.idx))
			
			if not a.is_milestone:
				a.task_achievement_percent = round(flt(a.task_completion_percent)/100 * flt(a.task_weightage), 7)
				a.one_day_achievement = round(flt(a.task_achievement_percent)/flt(a.task_duration), 7)
				total_achievement += flt(a.task_achievement_percent)
                #self.physical_progress = round(total_achievement, 3)
		#self.physical_progress = round(flt(total_achievement)/100 * flt(self.physical_progress_weightage), 3)
		if not update:
			self.percent_completed = round(total_achievement, 4)	
			self.physical_progress = round(flt(self.percent_completed)/100 * flt(self.physical_progress_weightage), 3)	
		else:
			self.db_set("percent_completed", round(total_achievement, 4))
			self.db_set("physical_progress", round(round(total_achievement, 4)/100 * flt(self.physical_progress_weightage), 3))
			self.reload()
		#self.percent_completed = round(flt(self.physical_progress)/flt(self.physical_progress_weightage)*100, 3)
		if not self.is_group:
			self.update_parent()

	def update_parent(self):
		progress = frappe.db.sql(""" select sum(ifnull(physical_progress, 0)) as val from `tabHome Security Skilling` where parent_project = "{0}" 
			and is_group = 0 and docstatus <=1""".format(self.parent_project), as_dict = 1)
		if progress:
			doc = frappe.get_doc("Home Security Skilling", self.parent_project)
			doc.db_set("physical_progress", flt(progress[0].val)/100*flt(doc.physical_progress_weightage))
			doc.db_set("percent_completed", round(flt(doc.physical_progress)/flt(doc.physical_progress_weightage) * 100, 4)) 

	def make_tsk_group(self):
		wt = percent_comp = 0.0
		for a in frappe.db.sql(""" select name, idx from `tabHSS Activity Task` where is_milestone = 1 and parent = "{0}" 
			""".format(self.name), as_dict = 1):
			weightage = frappe.db.sql(""" select sum(ifnull(task_weightage, 0)) as tweightage, sum(ifnull(task_completion_percent, 0)) as tcompletion from `tabHSS Activity Task` 
                        where task_group = '{0}{1}' and is_milestone = 0""".format(a.name, a.idx), as_dict = 1)
			task_count = frappe.db.sql(""" select count(*) as count from `tabHSS Activity Task` 
                        where task_group = '{0}{1}' and is_milestone = 0""".format(a.name, a.idx), as_dict = 1)
			if weightage:
				wt = weightage[0].tweightage
				percent_comp = flt(weightage[0].tcompletion) / flt(task_count[0].count)
				frappe.db.sql(""" update `tabHSS Activity Task` set task_weightage = {0}, task_completion_percent = {2} where  name = '{1}'
							""".format(wt, a.name, percent_comp))

	def set_status(self):
		if self.percent_completed == 100:
			self.db_set("status", "Completed")
		if self.percent_completed < 100:
			self.db_set("status", "Ongoing")

	def update_expense(self):
		exp = frappe.db.sql(""" select sum(debit) - sum(credit) as expense 
                      from `tabGL Entry` where cost_center = "{0}" and account in (select name from `tabAccount` 
			where root_type = 'Expense') and docstatus = 1""".format(self.name), as_dict = 1)
		if exp:
			self.db_set('expense', flt(exp[0].expense))
				
	def update_total_expense(self):
		lft,rgt = frappe.get_value("Cost Center", self.parent_project, ['lft','rgt'])

		exp = frappe.db.sql(""" select sum(debit) - sum(credit) as expense 
				from `tabGL Entry` where cost_center IN (select name from `tabCost Center` where lft >= {lft} and rgt <= {rgt} and is_group=0 and is_disabled=0) 
				and account in (select name from `tabAccount` where root_type = 'Expense') and docstatus = 1""".format(lft=lft, rgt=rgt), as_dict = 1)

		if exp:
				doc = frappe.get_doc("Home Security Skilling", self.parent_project)
				doc.db_set('expense', flt(exp[0].expense))

	def post_achievement_entries(self):
		frappe.db.sql(""" delete from `tabHSS Achievement Entry` where project = "{0}" and posting_date = '{1}'
				""".format(self.name, self.completion_date))
		entry = frappe.db.sql(""" select sum(percent_completed) as per_completed, sum(percent_completed_overall) as overall from `tabHSS Achievement Entry` where project = "{0}" """.format(self.name), as_dict = 1)
		en = 0.0
		if entry:
			en = entry[0].per_completed
		com = round(flt(self.percent_completed) - flt(en),9)
		# if flt(com) <0:
		# 	frappe.throw("Update Cannot Be Negative")

		doc = frappe.get_doc({
			'doctype': 'HSS Achievement Entry',
			'project': self.name,
			'project_parent': self.parent_project,
			'percent_completed': com,
			'posting_date': self.completion_date
				})
		doc.insert()
		self.db_set('percent_completed_old', round(flt(self.percent_completed), 9))
		self.db_set('physical_progress_old', round(flt(self.physical_progress), 9))

@frappe.whitelist()
def calculate_durations(hol_list = None, from_date = None, to_date = None):
	holiday = holiday_list(from_date, to_date, hol_list)
	duration = date_diff(to_date, from_date) + 1 - flt(holiday)
	return duration

#returns total holiday between given dates
def holiday_list(from_date, to_date, hol_list):
	holidays = 0.0
	if hol_list:
		holidays = frappe.db.sql("""select count(distinct holiday_date) from `tabHoliday` h1, `tabHoliday List` h2
	where h1.parent = h2.name and h1.holiday_date between %s and %s
	and h2.name = %s""", (from_date, to_date, hol_list))[0][0]
	return holidays