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
from erpnext.accounts.report.financial_statements_gyalsung  import (get_period_list, get_columns, get_data)


class Project(Document):
        def autoname(self):
               	self.name = self.project_name

	def validate(self):
		self.update_expense()
		self.flags.dont_sync_tasks = True
		self.name = self.project_name
		self.check_required_data()
		self.validate_dates()
		self.task_dates()
		if self.is_group:
			self.parent_weightage = 100
			frappe.db.sql("""update `tabProject` set overall_mandays = {0}, parent_weightage = {1}, 
				physical_progress_weightage = round((mandays/overall_mandays)*100, 3)
				where parent_project = "{2}" and overall_mandays != {0}
			""".format(self.mandays, self.physical_progress_weightage, self.name))
			
		else:
			doc = frappe.get_doc("Project", self.parent_project)
			self.parent_weightage = doc.physical_progress_weightage
			self.overall_mandays = doc.mandays
		self.physical_progress_weightage = round(flt(self.mandays)/flt(self.overall_mandays) * 100, 3)
		#self.calculations()
		#self.update_parent()
		#self.get_budget()
		self.update_expense()
		if self.get("activity_tasks"):
			self.make_target_entries()
			self.make_group()
			#self.make_tsk_group()
		if not self.is_group:
			self.update_total_expense()

	def on_submit(self):
		self.flags.dont_sync_tasks = True
                self.update_progress()
		self.validate_dates()
		self.task_dates()
		#self.update_parent()

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
		total_days = 0.0
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
				
	#def after_insert
	def on_update_after_submit(self):
		self.flags.dont_sync_tasks = True
		# if not self.completion_date:
		# 	frappe.throw("Date of Update is Required", title="Missing Input")
		#if self.pe_id != frappe.session.user:
		#	frappe.throw(" Only {0} Can update this project".format(pe_name))

		if getdate(self.completion_date) > getdate(nowdate()):
			frappe.throw(_("Cannot Update For Future Dates"))

		self.physical_progress = round(flt(self.physical_progress), 7)
		if not self.is_group:
			self.make_tsk_group()
			self.update_progress(update=True)
			# self.update_parent()
		if self.percent_completed == 100:
			self.db_set("status", "Completed")
		if self.percent_completed < 100:
			self.db_set("status", "Ongoing")
		self.total_task_duration()
		self.post_achievement_entries()
		self.make_target_entries()
		self.update_expense()	
		if not self.is_group:
			self.update_total_expense()
		# self.validate_weightage()

	def validate_weightage(self):
                old_value = frappe.db.sql(""" select physical_progress_weightage from `tabProject` where name = "{0}" """.format(self.name))
                if old_value != self.physical_progress_weightage:
                        if frappe.session.user not in ('yeshinedup@gyalsunginfra.bt', 'Administrator'):
                                frappe.throw("You are not authorized to change project weightage, kindly contact Project CTM")
	
	def update_progress(self, update=False):
                total_achievement = 0.0
                for a in self.get("activity_tasks"):
			if a.task_completion_percent > 100:
				frappe.throw("Task Completion Percent Cannot Exceed 100 % at Sl. <b> {0} </b>".format(a.idx))
			'''if flt(a.get_db_value('task_completion_percent')) < flt(a.task_completion_percent):
				frappe.throw("Task Progress Percent Cannot be less than {0} at SL. {1}".format(a.get_db_value('task_completion_percent'), a.idx))
			'''
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
		self.update_parent()



	def update_parent(self):
		progress = frappe.db.sql(""" select sum(ifnull(physical_progress, 0)) as val from `tabProject` where parent_project = "{0}" 
			and is_group = 0 and docstatus <=1""".format(self.parent_project), as_dict = 1)
		if progress:
			doc = frappe.get_doc("Project", self.parent_project)
			doc.db_set("physical_progress", flt(progress[0].val)/100*flt(doc.physical_progress_weightage))
			doc.db_set("percent_completed", round(flt(doc.physical_progress)/flt(doc.physical_progress_weightage) * 100, 4)) 
		#progress = flt(progress[0].val)
		#completed = round(flt(doc.physical_progress)/flt(doc.physical_progress_weightage), 4)
		#frappe.db.sql(""" update `tabProject` set physical_progress = {0}, percent_completed = {1} where name = '{2}' and is_group = 1 and docstatus <= 1""".format(progress, completed, self.parent_project))


	def get_budget(self):
                self.reference_budget = None
                self.estimated_budget = 0.0
                from erpnext.accounts.accounts_custom_functions import get_child_cost_centers
                parent_cc = frappe.get_doc("Cost Center", self.name).parent_cost_center
                cost_centers = get_child_cost_centers(parent_cc)
                budget = frappe.db.sql(""" select sum(actual_total) as actual_total from `tabBudget` 
                where cost_center IN %(cost_center)s  and docstatus = 1""", {"cost_center": cost_centers}, as_dict =1)
                if self.is_group:
                        if budget:
                                self.reference_budget = None
                                self.estimated_budget = budget[0].actual_total
                                frappe.db.sql(""" update `tabProject` set estimated_budget = {0} where name = '{1}'
                                """.format(budget[0].actual_total, self.name))

                else:
                        budget1 = frappe.db.sql(""" select name, actual_total from `tabBudget` where cost_center = "%s" and 
                                        docstatus = 1""" %self.project_name, as_dict =1)
                        if budget1:
                                self.reference_budget = budget1[0].name
                                self.estimated_budget = budget1[0].actual_total
                                frappe.db.sql(""" update `tabProject` set estimated_budget = {0} where name = '{1}'
                                """.format(budget1[0].actual_total, self.name))

                                frappe.db.sql(""" update `tabProject` set estimated_budget = {0} where name = '{1}'
                                """.format(budget[0].actual_total, self.parent_project))	
	def on_update(self):
		self.flags.dont_sync_tasks = True
		self.make_group()
		self.make_tsk_group()

	def calculations(self):
                total_days = 0.0
                mandays = self.mandays
                contributed = 0.0
                for a in self.get("activity_tasks"):
                        if a.task_group:

                                doc = frappe.get_doc("Activity Tasks", a.task_group)
                                task_doc= frappe.db.sql(""" select sum(ifnull(task_duration, 0)) as task from `tabActivity Tasks` where parent = '{0}' and docstatus <=1 and task_group = '{1}' group by task_group, parent""".format(self.name, a.task_group), as_dict = 1)
                                if task_doc:
                                        a.task_weightage = flt(a.task_duration)/flt(task_doc[0].task)*flt(doc.task_weightage)
                        else:
                                a.task_weightage = round(flt(a.task_duration)/flt(self.mandays), 7)
                        a.one_day_weightage = round(flt(a.task_weightage)/flt(a.task_duration), 7)

                        if not a.is_milestone:
                                contributed += round(flt(a.task_achievement_percent), 7)
                self.physical_progress = round(contributed, 7)
                self.percent_completed = round(flt(self.physical_progress)/flt(self.physical_progress_weightage), 5) * 100
	
	def make_group(self):
                self.task_dates()
		wt = 0.0
                group_list = frappe.db.sql("""
                                        select t1.name, t1.task, t1.idx, t1.is_milestone,
                                                (select ifnull(min(t2.idx),9999)
                                                 from  `tabActivity Tasks` as t2
                                                 where t2.parent  = t1.parent
                                                 and   t2.is_milestone = t1.is_milestone
                                                 and   t2.idx > t1.idx
                                                ) as max_idx
                                        from `tabActivity Tasks` as t1
                                        where t1.parent = "{0}"
                                        and   t1.is_milestone = 1
                                        order by t1.idx
                                """.format(self.name), as_dict=1)
                for a in group_list:
			frappe.db.sql(""" update `tabActivity Tasks` set task_group = '' where name = '{0}' and is_milestone = 1 """.format(a.name, self.name))
                        frappe.db.sql(""" update  `tabActivity Tasks` set task_group = '{0}{1}' where  idx between {1} and {2} and parent = "{3}" and name != '{0}'""".format(a.name, a.idx, a.max_idx, self.name))
			'''weightage = frappe.db.sql(""" select sum(ifnull(task_weightage, 0)) as tweightage from `tabActivity Tasks` 
			where task_group = '{0}' and is_milestone = 0""".format(a.name), as_dict = 1)
			if weightage:
				wt = weightage[0].tweightage
				frappe.db.sql(""" update `tabActivity Tasks` set task_weightage = {0} where  name = '{1}'
				""".format(wt, a.name))'''


	def make_tsk_group(self):
		wt = percent_comp = 0.0
		for a in frappe.db.sql(""" select name, idx from `tabActivity Tasks` where is_milestone = 1 and parent = "{0}" 
			""".format(self.name), as_dict = 1):
			weightage = frappe.db.sql(""" select sum(ifnull(task_weightage, 0)) as tweightage, sum(ifnull(task_completion_percent, 0)) as tcompletion from `tabActivity Tasks` 
                        where task_group = '{0}{1}' and is_milestone = 0""".format(a.name, a.idx), as_dict = 1)
			task_count = frappe.db.sql(""" select count(*) as count from `tabActivity Tasks` 
                        where task_group = '{0}{1}' and is_milestone = 0""".format(a.name, a.idx), as_dict = 1)
			date_line = frappe.db.sql(""" select max(end_date) as max_date, min(start_date) as min_date from `tabActivity Tasks` 
                        where task_group = '{0}{1}' and is_milestone = 0""".format(a.name, a.idx), as_dict = 1)
			if weightage:
				wt = weightage[0].tweightage
				percent_comp = weightage[0].tcompletion / task_count[0].count
				frappe.db.sql(""" update `tabActivity Tasks` set task_weightage = {0}, task_completion_percent = {2}, start_date='{3}', end_date='{4}' where  name = '{1}'
							""".format(wt, a.name, percent_comp, date_line[0].min_date, date_line[0].max_date))
		frappe.db.commit()	
	def update_task_group(self):
                group_list = frappe.db.sql("""
                                        select t1.name, t1.task, t1.idx, t1.is_milestone,
                                                (select ifnull(min(t2.idx),9999)
                                                 from  `tabActivity Tasks` as t2
                                                 where t2.parent  = t1.parent
                                                 and   t2.is_milestone = t1.is_milestone
                                                 and   t2.idx > t1.idx
                                                ) as max_idx
                                        from `tabActivity Tasks` as t1
                                        where t1.parent = "{0}"
                                        and   t1.is_milestone = 1
                                        order by t1.idx
                                """.format(self.name), as_dict=1)


                frappe.db.sql(""" update `tabActivity Tasks` set task_group = '' where parent = '{0}'""".format(self.name))
                for a in group_list:
                        nn = a.name
                        frappe.db.sql(""" update `tabActivity Tasks` set task_group = '{0}' where  idx between {1} and {2} and parent = '{3}' and name != '{4}'""".format(a.name, a.idx, a.max_idx, self.name, a.nam))	
	def make_target_entries(self):
		frappe.db.sql(""" delete from `tabTarget Entry Sheet` where project = "{0}" """.format(self.name))
		target_tot = 0.0
		target_tot_overall = 0.0
		for from_date, to_date in self.get_period_date_ranges():
			old = frappe.db.sql(""" select percent_completed from `tabTarget Entry Sheet` 
					where project = "{0}" and to_date < '{1}' order by to_date desc limit 1
				""".format(self.name, from_date), as_dict = 1)
			old =  old[0].percent_completed if old else 0.0
			#for t in self.get("activity_tasks"):
			for t in frappe.db.sql(""" select task, start_date, end_date, ifnull(one_day_weightage,0) as one_day_weightage
				 from `tabActivity Tasks`
				where parent = "{0}" and is_milestone != 1 and docstatus <= 1""".format(self.name), as_dict = 1):	
				if getdate(t.start_date) >=  getdate(from_date) and getdate(t.end_date) <= getdate(to_date):
					hol_list = holiday_list(t.start_date, t.end_date, self.holiday_list)
					duration = date_diff(t.end_date, t.start_date) + 1 - flt(hol_list)
					target_tot += round(flt(duration) * flt(t.one_day_weightage), 9)

				if getdate(t.start_date) < getdate(from_date) and getdate(t.end_date) > getdate(to_date):
					hol_list = holiday_list(from_date, to_date, self.holiday_list)
					duration = date_diff(to_date, from_date) + 1 - flt(hol_list)
					target_tot += round(flt(duration) * flt(t.one_day_weightage), 9)	
	
				if getdate(to_date) >= getdate(t.start_date) >=  getdate(from_date) and getdate(t.end_date) > getdate(to_date):
					hol_list = holiday_list(t.start_date, to_date, self.holiday_list)
					duration = date_diff(to_date, t.start_date) + 1 - flt(hol_list)
					target_tot += round(flt(duration) * flt(t.one_day_weightage), 9)

				if getdate(t.start_date) < getdate(from_date) and getdate(from_date) <= getdate(t.end_date) <= getdate(to_date):
					hol_list = holiday_list(from_date, t.end_date, self.holiday_list)
					duration = date_diff(t.end_date, from_date) + 1 - flt(hol_list)
					target_tot += round(flt(duration) * flt(t.one_day_weightage),9)
					
			per = flt(target_tot) - flt(old)
			
			'''doc = frappe.new_doc("Target Entry Sheet")
			doc.project = self.name
                        doc.project_parent = self.parent_project
                        doc.entry_type =  'Monthly'
                        doc.from_date =  from_date
                        doc.to_date = to_date
                        doc.percent_completed = target_tot
                        doc.percent_completed_overall = round(flt(per)/100 * flt(self.physical_progress_weightage), 9)
                        doc.entry_name =  get_period(to_date, 'Monthly') 
			'''
			
			doc = frappe.get_doc({
				'doctype': 'Target Entry Sheet',
				'project': self.name,
				'project_parent': self.parent_project,
				'entry_type': 'Monthly',
				'from_date': from_date,
				'to_date': to_date,
				'percent_completed': target_tot,
				'entry_name': get_period(to_date, 'Monthly') 
				})
			doc.insert()
		""" convert into 100% work """
		total_percent = frappe.db.sql("select sum(percent_completed) tot from `tabTarget Entry Sheet` where project=%s", self.name, as_dict=True)
		
		if total_percent[0]['tot'] > 100:
			new_percent = 0
			for d in frappe.db.sql("select * from `tabTarget Entry Sheet` where project=%s", self.name, as_dict=True):
				new_percent += flt((flt(d.percent_completed)/flt(total_percent[0]['tot'])) * 100, 6)
				frappe.db.sql("update `tabTarget Entry Sheet` set percent_completed={} where name='{}'".format(flt(new_percent), d.name))

	def get_tasks_data(self, from_date, to_date):
                task = frappe.db.sql(""" select name, start_date, end_date, one_day_weightage, one_day_weightage_overall  
                        from `tabActivity Tasks` where parent = '{0}' and docstatus <= 1
			and (start_date between '{0}' and '{1}' or end_date between '{0}' and '{1}' or 
				'{0}' between start_date and end_date or '{1}' between start_date and end_date)""".format(self.name, from_date, to_date), as_dict =1)
                return task

	def get_period_date_ranges(self):
                from dateutil.relativedelta import relativedelta
                from_date, to_date = getdate(self.expected_start_date), getdate(self.expected_end_date)
		da = frappe.db.sql(""" select min(start_date) as min_date, max(end_date) as max_date from `tabActivity Tasks` 
			where parent = "{0}" and is_milestone != 1""".format(self.name), as_dict =1)
		if da:
			if from_date < getdate(da[0].min_date):
				from_date = getdate(da[0].min_date)
			if to_date > getdate(da[0].max_date):
				to_date = getdate(da[0].max_date)
                start_date = get_first_day(from_date)
                date_range = 'Monthly'
		#date_range = 'Weekly'
		increment = {
                        "Monthly": 1,
                        "Quarterly": 3,
                        "Half-Yearly": 6,
                        "Yearly": 12
                }.get(date_range,1)

                periodic_daterange = []
                for dummy in range(1, 53, increment):
                        if date_range == "Weekly":
                                period_end_date = start_date + relativedelta(days=6)
                        else:
                                period_end_date = start_date + relativedelta(months=increment, days=-1)

                        if period_end_date > to_date:
                                period_end_date = to_date
                        periodic_daterange.append([start_date, period_end_date])

                        start_date = period_end_date + relativedelta(days=1)
                        from_date = period_end_date + relativedelta(days=1)

                        if period_end_date == to_date:
                                break
                return periodic_daterange

	def post_achievement_entries(self):
		frappe.db.sql(""" delete from `tabAchievement Entry Sheet` where project = "{0}" and posting_date = '{1}'
				""".format(self.name, self.completion_date))
		entry = frappe.db.sql(""" select sum(percent_completed) as per_completed, sum(percent_completed_overall) as overall from `tabAchievement Entry Sheet` where project = "{0}" """.format(self.name), as_dict = 1)
		en = 0.0
		if entry:
			en = entry[0].per_completed
			en_overall = entry[0].overall
		com = round(flt(self.percent_completed) - flt(en),9)
		if flt(com) <0:
			frappe.throw("Update Cannot Be Negative")

		#com_overall  = round(flt(self.physical_progress) - flt(en_overall), 5)
		#if flt(self.percent_completed) - flt(en):
		doc = frappe.get_doc({
			'doctype': 'Achievement Entry Sheet',
			'project': self.name,
			'project_parent': self.parent_project,
			'percent_completed': com,
			'posting_date': self.completion_date
				})
		doc.insert()
		self.db_set('percent_completed_old', round(flt(self.percent_completed), 9))
		self.db_set('physical_progress_old', round(flt(self.physical_progress), 9))
		#self.completion_date = None
		#percent_completed_overall': flt(com)/100 * flt(self.physical_progress_weightage)

	def update_expense(self):
		exp = frappe.db.sql(""" select sum(debit) - sum(credit) as expense 
                      from `tabGL Entry` where cost_center = "{0}" and account in (select name from `tabAccount` 
			where root_type = 'Expense') and docstatus = 1""".format(self.name), as_dict = 1)
		if exp:
			self.db_set('expense', flt(exp[0].expense))


	def update_total_expense(self):
                from erpnext.accounts.accounts_custom_functions import get_child_cost_centers
                parent_cc = frappe.get_doc("Cost Center", self.parent_project).parent_cost_center
                cost_centers = get_child_cost_centers(parent_cc)

                exp = frappe.db.sql(""" select sum(debit) - sum(credit) as expense 
                      from `tabGL Entry` where cost_center IN %(cost_center)s  and account in (select name from `tabAccount` 
                        where root_type = 'Expense') and docstatus = 1""", {"cost_center": cost_centers}, as_dict = 1)

                if exp:
                        doc = frappe.get_doc("Project", self.parent_project)
                        doc.db_set('expense', flt(exp[0].expense))

	def notify_on_change(self):
		pass

def get_period(posting_date, prange):
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        if prange == 'Weekly':
                period = "Week " + str(posting_date.isocalendar()[1]) + " " + str(posting_date.year)
        elif prange == 'Monthly':
                period = str(months[posting_date.month - 1]) + " " + str(posting_date.year)
        elif prange == 'Quarterly':
                period = "Quarter " + str(((posting_date.month-1)/3)+1) +" " + str(posting_date.year)
        else:
                year = get_fiscal_year(posting_date, company=filters.company)
                period = str(year[2])
        return period
	
@frappe.whitelist()
def calculate_durations(hol_list = None, from_date = None, to_date = None):
	holiday = holiday_list(from_date, to_date, hol_list)
	duration = date_diff(to_date, from_date) + 1 - flt(holiday)
	return duration


@frappe.whitelist()
def testing(from_date, to_date):
	return "hi"
	
#returns total holiday between given dates
def holiday_list(from_date, to_date, hol_list):
	holidays = 0.0
	if hol_list:
		holidays = frappe.db.sql("""select count(distinct holiday_date) from `tabHoliday` h1, `tabHoliday List` h2
	where h1.parent = h2.name and h1.holiday_date between %s and %s
	and h2.name = %s""", (from_date, to_date, hol_list))[0][0]
	return holidays

""" This function exec from hooks daily """
def update_project_expense():
    # previous_date = add_days(nowdate(), -1)
    # next_date = add_days(nowdate(), 1)

    # distinct_activities = frappe.db.sql("""SELECT DISTINCT cost_center 
    #                                         FROM `tabGL Entry` 
    #                                         WHERE modified BETWEEN %s AND %s""",
    #                                     (getdate(previous_date), getdate(next_date)),
    #                                     as_dict=True)

    # for activity in distinct_activities:
    #     cost_center = activity.cost_center
    for cost_center in frappe.db.sql("select cost_center from tabProject where workflow_state in ('Update','Approved')", as_dict=1):

        if frappe.get_value("Project", cost_center, "name"):
            update_project_expense_for_cost_center(cost_center)

def update_project_expense_for_cost_center(cost_center):
    doc = frappe.get_doc("Project", cost_center)
    cost_centers = []
    if doc.is_group:
        cost_centers = [row[0] for row in frappe.db.sql("""SELECT name FROM `tabCost Center` WHERE parent_cost_center = %s and is_group=0""", (doc.parent_cost_center))]
    # parent_cc = frappe.get_value("Cost Center", cost_center, "parent_cost_center")
    # cost_centers = frappe.get_all("Cost Center", filters={"parent_cost_center": parent_cc}, pluck="name")
    # cost_centers = [row[0] for row in frappe.db.sql("""SELECT name FROM `tabCost Center` WHERE parent_cost_center = %s and is_group=0""", (parent_cc))]

        total_expense = frappe.db.sql("""SELECT SUM(debit) - SUM(credit) AS expense 
                                     FROM `tabGL Entry` 
                                     WHERE cost_center IN %s 
                                     AND account IN (SELECT name FROM `tabAccount` WHERE root_type = 'Expense') 
                                     AND docstatus = 1""",
                                 (cost_centers,),
                                 as_dict=True)[0].expense

    if not doc.is_group:
        total_expense = frappe.db.sql("""SELECT SUM(debit) - SUM(credit) AS expense 
                                                    FROM `tabGL Entry` 
                                                    WHERE cost_center = %s 
                                                    AND account IN (SELECT name FROM `tabAccount` WHERE root_type = 'Expense') 
                                                    AND docstatus = 1""",
                                                (doc.name,),
                                                as_dict=True)[0].expense
        frappe.db.sql("""UPDATE `tabProject` SET expense = %s WHERE name = %s""", (flt(total_expense), doc.name))
    else:
        frappe.db.sql("""UPDATE `tabProject` SET expense = %s WHERE name = %s""", (flt(total_expense), doc.name))

def old_update_project_expense():
	previous_date = add_days(nowdate(), -1)
	next_date = add_days(nowdate(), 1)
	distinct_activities = frappe.db.sql("""Select distinct cost_center From `tabGL Entry` Where modified Between 
				'{}' And '{}' """.format(getdate(previous_date), getdate(next_date)), as_dict=True)
	if len(distinct_activities):
		for d in distinct_activities:
			if frappe.db.exists("Project", str(d.cost_center)):
				
				doc = frappe.get_doc("Project", d.cost_center)
				from erpnext.accounts.accounts_custom_functions import get_child_cost_centers
				parent_cc = frappe.get_doc("Cost Center", d.cost_center).parent_cost_center
				cost_centers = get_child_cost_centers(parent_cc)

				all_total_exp = frappe.db.sql(""" select sum(debit) - sum(credit) as expense from `tabGL Entry` 
							where cost_center IN %(cost_center)s  and account in (select name from `tabAccount` where root_type = 'Expense') 
							and docstatus = 1""", {"cost_center": cost_centers}, as_dict = 1)
				if not doc.is_group:
						total_exp = frappe.db.sql(""" select sum(debit) - sum(credit) as expense 
								from `tabGL Entry` where cost_center = "{0}" and 
								account in (select name from `tabAccount` where root_type = 'Expense')""".format(doc.name), as_dict = 1)
						
						frappe.db.sql(""" update `tabProject` set expense = {0} where 
								name = "{1}" """.format(flt(total_exp[0].expense), doc.name))

						'''if total_exp:
						doc = frappe.get_doc("Project", parent)
						doc.db_set('expense', flt(total_exp[0].expense))'''

						frappe.db.sql(""" update `tabProject` set expense = {0}
								where name = "{1}" """.format(flt(all_total_exp[0].expense), doc.parent_project))
				else:
					frappe.db.sql(""" update `tabProject` set expense = {0}
							where name = "{1}" """.format(flt(all_total_exp[0].expense), doc.name))