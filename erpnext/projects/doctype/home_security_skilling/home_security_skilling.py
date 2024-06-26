# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate, formatdate, today, get_first_day, date_diff, add_years, flt

class HomeSecuritySkilling(Document):
	def validate(self):
		self.validate_fields()

	def validate_fields(self):
		if not self.cost_center:
			self.cost_center = frappe.db.get_value("Cost Center", {"branch": self.branch}, "name")
		if self.is_group:
			self.parent_project = ""
			self.parent_cost_center = "GA-Jamtsholing - GYALSUNG"
			self.project_category = ""
			self.project_sub_category = ""
		self.check_required_data()
		self.validate_dates()
		self.task_dates()

	
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
			if a.idx == 1 and a.is_milestone == 0:
				frappe.throw("First Task list should start as Milestone at Row: {0}".format(a.idx))
			if getdate(a.start_date) > getdate(a.end_date):
				frappe.throw("Task Start Date Cannot be Greater than End Date at Row {0}".format(a.idx))
			if flt(a.task_completion_percent) > 100:
				frappe.throw(" Percent Cannot exceed 100%")

			if flt(a.task_completion_percent) < 0:
				frappe.throw("Percent Cannot be less than 0%")

			if getdate(a.start_date) < getdate(self.expected_start_date):
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