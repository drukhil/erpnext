# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
2.0		  SHIV		                    2017/08/15         'Project Name', 'Tasks' are moved to parent doctype
                                                                        'Timesheet' in order to provide more flexibility
                                                                        in recording time logs against a single task.
                                                                        However same fields from child doctype 'Timesheet Details'
                                                                        are hidden and populated automatically.
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''
from __future__ import unicode_literals
import frappe
from frappe import _

import json
from datetime import timedelta
from frappe.utils import flt, time_diff_in_hours, get_datetime, getdate, cint, get_datetime_str, date_diff, today
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from erpnext.manufacturing.doctype.workstation.workstation import (check_if_within_operating_hours,
	WorkstationHolidayError)
from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import get_mins_between_operations
# Autonaming is changed, SHIV on 23/10/2017
from frappe.model.naming import make_autoname

class OverlapError(frappe.ValidationError): pass
class OverProductionLoggedError(frappe.ValidationError): pass

class Timesheet(Document):
        def autoname(self):
                cur_year  = str(today())[0:4]
                cur_month = str(today())[5:7]
                if self.project:
                        serialno  = make_autoname("TSM" + self.project[-4:] + ".####")
                        #self.name = serialno[0:3] + cur_year + cur_month + serialno[3:]
                else:
                        serialno  = make_autoname("TSM.YY.MM.####")

                self.name = serialno
                
	def validate(self):
                # ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++
                # Following two methods introduced by SHIV on 15/08/2017
                self.validate_target_quantity()
                self.set_defaults()
                self.set_dates()
                # +++++++++++++++++++++ Ver 2.0 ENDS +++++++++++++++++++++
		self.set_status()
		self.validate_dates()
		self.validate_time_logs()
		self.update_cost()
		self.calculate_total_amounts()

	def before_submit(self):
		self.set_dates()
		self.calculate_target_quantity()

	def before_cancel(self):
		self.set_status()
                
	def on_cancel(self):
		self.update_production_order(None)
		self.update_task_and_project()
                # ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++
                # Following methods introduced by SHIV on 15/08/2017
                self.calculate_target_quantity()
                self.reset_time_log_order()
                # +++++++++++++++++++++ Ver 2.0 ENDS +++++++++++++++++++++		

        '''
        def on_trash(self):
                self.calculate_target_quantity()
                self.reset_time_log_order()

        '''
        
        def after_delete(self):
                self.calculate_target_quantity()
                self.reset_time_log_order()
                
	def on_submit(self):
		self.validate_mandatory_fields()
		self.update_production_order(self.name)
		self.update_task_and_project()

        def on_update(self):
                # ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++
                # Following methods introduced by SHIV on 15/08/2017
                self.calculate_target_quantity()
                self.reset_time_log_order()
                # +++++++++++++++++++++ Ver 2.0 ENDS +++++++++++++++++++++

        def validate_target_quantity(self):
                curr_balance = 0.0

                prev_balance = get_target_quantity_complete(self.name, self.task)
                '''
                result = frappe.db.sql("""
                        select sum(case
                                        when parent != '{0}' then ifnull(target_quantity_complete,0)
                                        else 0
                                   end) as prev_balance
                        from  `tabTimesheet Detail`
                        where task = '{2}'
                        and   docstatus < 2
                """.format(self.name, self.name, self.task), as_dict=1)[0]
                '''
                
                for tl in self.time_logs:
                        curr_balance += flt(tl.target_quantity_complete)
                
                if flt(self.target_quantity) < (flt(prev_balance)+flt(curr_balance)):
                        frappe.throw(_("`Total Achieved Value` cannot be more than `Total Target Value`."))
                
        def reset_time_log_order(self):
                idx = 0
                tl_list = frappe.db.sql("""
                                        select *
                                        from `tabTimesheet Detail`
                                        where parent = '{0}'
                                        order by from_date, to_date
                                """.format(self.name), as_dict=1)

                for tl in tl_list:
                        idx += 1
                        frappe.db.sql("""
                                update `tabTimesheet Detail`
                                set idx = {0}
                                where name = '{1}'
                        """.format(idx, tl.name))
                
	def calculate_total_amounts(self):
		self.total_hours = 0.0
		self.total_billing_amount = 0.0
		self.total_costing_amount = 0.0
		
		for d in self.get("time_logs"):
			self.total_hours += flt(d.hours)
			
			if d.billable: 
				self.total_billing_amount += flt(d.billing_amount)
				self.total_costing_amount += flt(d.costing_amount)

        # ++++++++++++++++++++ Ver 1.0 BEGINS ++++++++++++++++++++
        # Following method introduced by SHIV on 2017/08/15
        def set_defaults(self):
                # Defaults
                if self.project:
                        base_project    = frappe.get_doc("Project", self.project)
                        self.branch     = base_project.branch
                        self.cost_center= base_project.cost_center

                        if base_project.status in ('Completed','Cancelled'):
                                frappe.throw(_("Operation not permitted on already {0} Project.").format(base_project.status),title="Timesheet: Invalid Operation")
                                
                # `Timesheet Detail` Validations
                total_target_quantity           = 0.0
                total_target_quantity_complete  = 0.0
                for tl in self.time_logs:
                        total_target_quantity           += flt(tl.target_quantity)
                        total_target_quantity_complete  += flt(tl.target_quantity_complete)
                        tl.from_time = tl.from_date
                        tl.to_time   = tl.to_date

                        if tl.from_date > tl.to_date:
                                frappe.throw(_("Row {0}: From Date cannot be after To Date.").format(tl.idx))
                                
                if flt(total_target_quantity_complete) > flt(self.target_quantity):
                        frappe.throw(_("Total Achieved value({0}) cannot be more than Target value({1})").format(flt(total_target_quantity_complete),flt(self.target_quantity)))
                
                # Setting `Timesheet` Defaults
                if self.task:
                        base_task = frappe.get_doc("Task", self.task)
                        
                        self.task_name          = base_task.subject
                        self.work_quantity      = base_task.work_quantity
                        self.exp_start_date     = base_task.exp_start_date
                        self.exp_end_date       = base_task.exp_end_date
                        self.target_uom         = base_task.target_uom
                        self.target_quantity    = base_task.target_quantity

                        self.target_quantity_complete = 0.0
                        for item in self.time_logs:
                                self.target_quantity_complete += flt(item.target_quantity_complete)

                
                # Setting `Timesheet Detail` Defaults
                for data in self.time_logs:
                        if not data.project or data.project <> self.project:
                                data.project = self.project

                        if not data.task or data.task <> self.task:
                                data.task = self.task
                                
        # Following method added by SHIV on 2017/08/16
        def calculate_target_quantity(self):
                if flt(self.target_quantity_complete) > flt(self.target_quantity):
                        frappe.throw(_("Total Achieved value({0}) cannot be greater than Task's Target value({1}).").format(flt(self.target_quantity_complete),flt(self.target_quantity)))
                else:
                        if self.project:
                                # Updating Project Progress                        
                                base_project = frappe.get_doc("Project",self.project)
                                base_project.update_task_progress()
                                #base_project.update_project_progress()
                                base_project.update_group_tasks()

                                total = frappe.db.sql("""
                                                select
                                                        sum(
                                                                case
                                                                when additional_task = 0 and status in ('Closed', 'Cancelled') then 1
                                                                else 0
                                                                end
                                                        ) as completed_count,
                                                        sum(
                                                                case
                                                                when additional_task = 0 then 1
                                                                else 0
                                                                end
                                                        ) as count,
                                                        sum(
                                                                case
                                                                when additional_task = 1 and status in ('Closed', 'Cancelled') then 1
                                                                else 0
                                                                end
                                                        ) as add_completed_count,
                                                        sum(
                                                                case
                                                                when additional_task = 1 then 1
                                                                else 0
                                                                end
                                                        ) as add_count,
                                                        sum(
                                                                case
                                                                when additional_task = 0 then ifnull(work_quantity,0)
                                                                else 0
                                                                end
                                                        ) as tot_work_quantity,
                                                        sum(
                                                                case
                                                                when additional_task = 1 then ifnull(work_quantity,0)
                                                                else 0
                                                                end
                                                        ) as tot_add_work_quantity,
                                                        sum(
                                                                case
                                                                when additional_task = 0 then ifnull(work_quantity_complete,0)
                                                                else 0
                                                                end
                                                        ) as tot_work_quantity_complete,
                                                        sum(
                                                                case
                                                                when additional_task = 1 then ifnull(work_quantity_complete,0)
                                                                else 0
                                                                end
                                                        ) as tot_add_work_quantity_complete
                                                from tabTask
                                                where project=%s
                                                and is_group=0
                                        """, self.project, as_dict=1)[0]
                                
                                percent_complete           = 0.0
                                add_percent_complete       = 0.0
                                tot_wq_percent             = 0.0
                                tot_wq_percent_complete    = 0.0
                                tot_add_wq_percent         = 0.0
                                tot_add_wq_percent_complete= 0.0

                                if total.count:
                                        percent_complete   = flt(flt(total.completed_count) / total.count * 100, 2)
                                        tot_wq_percent     = flt(total.tot_work_quantity,2)
                                        tot_wq_percent_complete = flt(total.tot_work_quantity_complete,2)

                                if total.add_count:
                                        add_percent_complete = flt(flt(total.add_completed_count) / total.add_count * 100, 2)
                                        tot_add_wq_percent = flt(total.tot_add_work_quantity,2)
                                        tot_add_wq_percent_complete = flt(total.tot_add_work_quantity_complete,2)                                

                                frappe.db.sql("""
                                        update `tabProject`
                                        set
                                                percent_complete = ifnull({1},0),
                                                add_percent_complete = ifnull({2},0),
                                                tot_wq_percent = ifnull({3},0),
                                                tot_wq_percent_complete = ifnull({4},0),
                                                tot_add_wq_percent = ifnull({5},0),
                                                tot_add_wq_percent_complete = ifnull({6},0)
                                        where name = '{0}'
                                """.format(self.project, flt(percent_complete), flt(add_percent_complete), flt(tot_wq_percent), flt(tot_wq_percent_complete), flt(tot_add_wq_percent), flt(tot_add_wq_percent_complete)))
        # +++++++++++++++++++++ Ver 1.0 ENDS +++++++++++++++++++++				                        
                        
	def set_status(self):
		self.status = {
			"0": "Draft",
			"1": "Submitted",
			"2": "Cancelled"
		}[str(self.docstatus or 0)]

		if self.sales_invoice:
			self.status = "Billed"

		if self.salary_slip:
			self.status = "Payslip"

		if self.sales_invoice and self.salary_slip:
			self.status = "Completed"

	def set_dates(self):
		if self.docstatus < 2:
			start_date = min([d.from_time for d in self.time_logs])
			end_date = max([d.to_time for d in self.time_logs])

			if start_date and end_date:
				self.start_date = getdate(start_date)
				self.end_date = getdate(end_date)

                        if not self.total_days:
                                self.total_days = flt(date_diff(getdate(end_date),getdate(start_date)))+1

	def validate_mandatory_fields(self):
		if self.production_order:
			production_order = frappe.get_doc("Production Order", self.production_order)
			pending_qty = flt(production_order.qty) - flt(production_order.produced_qty)

		for data in self.time_logs:
			if not data.from_time and not data.to_time:
				frappe.throw(_("Row {0}: From Time and To Time is mandatory.").format(data.idx))

			if not data.activity_type and self.employee:
				frappe.throw(_("Row {0}: Activity Type is mandatory.").format(data.idx))

                        # ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++
                        # Following condition is commented by SHIV on 12/09/2017
                        """
			if flt(data.hours) == 0.0:
				frappe.throw(_("Row {0}: Hours value must be greater than zero.").format(data.idx))
                        """
			# +++++++++++++++++++++ Ver 1.0 ENDS +++++++++++++++++++++

			if self.production_order and flt(data.completed_qty) == 0:
				frappe.throw(_("Row {0}: Completed Qty must be greater than zero.").format(data.idx))

			if self.production_order and flt(pending_qty) < flt(data.completed_qty) and flt(pending_qty) > 0:
				frappe.throw(_("Row {0}: Completed Qty cannot be more than {1} for operation {2}").format(data.idx, pending_qty, data.operation),
					OverProductionLoggedError)

	def update_production_order(self, time_sheet):
		if self.production_order:
			pro = frappe.get_doc('Production Order', self.production_order)

			for timesheet in self.time_logs:
				for data in pro.operations:
					if data.name == timesheet.operation_id:
						summary = self.get_actual_timesheet_summary(timesheet.operation_id)
						data.time_sheet = time_sheet
						data.completed_qty = summary.completed_qty 
						data.actual_operation_time = summary.mins
						data.actual_start_time = summary.from_time
						data.actual_end_time = summary.to_time

			pro.flags.ignore_validate_update_after_submit = True
			pro.update_operation_status()
			pro.calculate_operating_cost()
			pro.set_actual_dates()
			pro.save()

	def get_actual_timesheet_summary(self, operation_id):
		"""Returns 'Actual Operating Time'. """
		return frappe.db.sql("""select
			sum(tsd.hours*60) as mins, sum(tsd.completed_qty) as completed_qty, min(tsd.from_time) as from_time,
			max(tsd.to_time) as to_time from `tabTimesheet Detail` as tsd, `tabTimesheet` as ts where 
			ts.production_order = %s and tsd.operation_id = %s and ts.docstatus=1 and ts.name = tsd.parent""",
			(self.production_order, operation_id), as_dict=1)[0]

	def update_task_and_project(self):
		for data in self.time_logs:
			if data.task:
				task = frappe.get_doc("Task", data.task)
				task.update_time_and_costing()
				task.save()

			elif data.project:
				frappe.get_doc("Project", data.project).update_project()

	def validate_dates(self):
                # ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++
                # Following code is commented by SHIV on 13/09/2017
                """
		for data in self.time_logs:
			if time_diff_in_hours(data.to_time, data.from_time) < 0:
				frappe.throw(_("To date cannot be before from date"))
                """
		# +++++++++++++++++++++ Ver 1.0 ENDS +++++++++++++++++++++

	def validate_time_logs(self):
		for data in self.get('time_logs'):
			self.check_workstation_timings(data)
			# Commented by SHIV on 19/10/2017
			#self.validate_overlap(data)

	def validate_overlap(self, data):
		if self.production_order:
			self.validate_overlap_for("workstation", data, data.workstation)
		else:
			self.validate_overlap_for("user", data, self.user)
			self.validate_overlap_for("employee", data, self.employee)

	def validate_overlap_for(self, fieldname, args, value):
		if not value: return

		existing = self.get_overlap_for(fieldname, args, value)
		if existing:
			frappe.throw(_("Row {0}: From Time and To Time of {1} is overlapping with {2}")
				.format(args.idx, self.name, existing.name), OverlapError)

	def get_overlap_for(self, fieldname, args, value):
		cond = "ts.`{0}`".format(fieldname)
		if fieldname == 'workstation':
			cond = "tsd.`{0}`".format(fieldname)

		existing = frappe.db.sql("""select ts.name as name, tsd.from_time as from_time, tsd.to_time as to_time from 
			`tabTimesheet Detail` tsd, `tabTimesheet` ts where {0}=%(val)s and tsd.parent = ts.name and
			(
				(%(from_time)s > tsd.from_time and %(from_time)s < tsd.to_time) or
				(%(to_time)s > tsd.from_time and %(to_time)s < tsd.to_time) or
				(%(from_time)s <= tsd.from_time and %(to_time)s >= tsd.to_time))
			and tsd.name!=%(name)s
			and ts.docstatus < 2""".format(cond),
			{
				"val": value,
				"from_time": args.from_time,
				"to_time": args.to_time,
				"name": args.name or "No Name"
			}, as_dict=True)

		return existing[0] if existing else None

	def check_workstation_timings(self, args):
		"""Checks if **Time Log** is between operating hours of the **Workstation**."""
		if args.workstation and args.from_time and args.to_time:
			check_if_within_operating_hours(args.workstation, args.operation, args.from_time, args.to_time)

	def schedule_for_production_order(self, index):
		for data in self.time_logs:
			if data.idx == index:
				self.move_to_next_day(data) #check for workstation holiday
				self.move_to_next_non_overlapping_slot(data) #check for overlap
				break

	def move_to_next_non_overlapping_slot(self, data):
		overlapping = self.get_overlap_for("workstation", data, data.workstation)
		if overlapping:
			time_sheet = self.get_last_working_slot(overlapping.name, data.workstation)
			data.from_time = get_datetime(time_sheet.to_time) + get_mins_between_operations()
			data.to_time = self.get_to_time(data)
			self.check_workstation_working_day(data)

	def get_last_working_slot(self, time_sheet, workstation):
		return frappe.db.sql(""" select max(from_time) as from_time, max(to_time) as to_time 
			from `tabTimesheet Detail` where workstation = %(workstation)s""",
			{'workstation': workstation}, as_dict=True)[0]

	def move_to_next_day(self, data):
		"""Move start and end time one day forward"""
		self.check_workstation_working_day(data)

	def check_workstation_working_day(self, data):
		while True:
			try:
				self.check_workstation_timings(data)
				break
			except WorkstationHolidayError:
				if frappe.message_log: frappe.message_log.pop()
				data.from_time = get_datetime(data.from_time) + timedelta(hours=24)
				data.to_time = self.get_to_time(data)

	def get_to_time(self, data):
		return get_datetime(data.from_time) + timedelta(hours=data.hours)

	def update_cost(self):
		for data in self.time_logs:
			if data.activity_type and (not data.billing_amount or not data.costing_amount):
				rate = get_activity_cost(self.employee, data.activity_type)
				hours =  data.hours or 0
				if rate:
					data.billing_rate = flt(rate.get('billing_rate'))
					data.costing_rate = flt(rate.get('costing_rate'))
					data.billing_amount = data.billing_rate * hours
					data.costing_amount = data.costing_rate * hours

@frappe.whitelist()
def make_sales_invoice(source_name, target=None):
	target = frappe.new_doc("Sales Invoice")

	target.append("timesheets", get_mapped_doc("Timesheet", source_name, {
		"Timesheet": {
			"doctype": "Sales Invoice Timesheet",
			"field_map": {
				"total_billing_amount": "billing_amount",
				"name": "time_sheet"
			},
		}
	}))
	
	target.run_method("calculate_billing_amount_from_timesheet")

	return target

@frappe.whitelist()
def make_salary_slip(source_name, target_doc=None):
	target = frappe.new_doc("Salary Slip")
	set_missing_values(source_name, target)
	
	target.append("timesheets", get_mapped_doc("Timesheet", source_name, {
		"Timesheet": {
			"doctype": "Salary Slip Timesheet",
			"field_map": {
				"total_hours": "working_hours",
				"name": "time_sheet"
			},
		}
	}))
	
	target.run_method("get_emp_and_leave_details")

	return target

def set_missing_values(time_sheet, target):
	doc = frappe.get_doc('Timesheet', time_sheet)
	target.employee = doc.employee
	target.employee_name = doc.employee_name
	target.salary_slip_based_on_timesheet = 1
	target.start_date = doc.start_date
	target.end_date = doc.end_date

@frappe.whitelist()
def get_activity_cost(employee=None, activity_type=None):
	rate = frappe.db.get_values("Activity Cost", {"employee": employee,
		"activity_type": activity_type}, ["costing_rate", "billing_rate"], as_dict=True)
	if not rate:
		rate = frappe.db.get_values("Activity Type", {"activity_type": activity_type},
			["costing_rate", "billing_rate"], as_dict=True)

	return rate[0] if rate else {}
		
@frappe.whitelist()
def get_events(start, end, filters=None):
	# frappe.msgprint("get_events")
	"""Returns events for Gantt / Calendar view rendering.
	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	filters = json.loads(filters)

	conditions = get_conditions(filters)
	
	'''
	return frappe.db.sql("""select `tabTimesheet Detail`.name as name, `tabTimesheet Detail`.parent as parent,
		from_time, hours, activity_type, project, to_time from `tabTimesheet Detail`, 
		`tabTimesheet` where `tabTimesheet Detail`.parent = `tabTimesheet`.name and 
		(from_time between %(start)s and %(end)s) {conditions}""".format(conditions=conditions),
		{
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})
        '''

	result = frappe.db.sql("""select `tabTimesheet Detail`.name as name, `tabTimesheet Detail`.parent as parent,
		`tabTimesheet Detail`.from_date, `tabTimesheet Detail`.days, `tabTimesheet Detail`.description, activity_type, `tabTimesheet Detail`.project,
		`tabTimesheet Detail`.to_date from `tabTimesheet Detail`, 
		`tabTimesheet` where `tabTimesheet Detail`.parent = `tabTimesheet`.name and 
		(from_date between %(start)s and %(end)s) {conditions}""".format(conditions=conditions),
		{
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})
	# frappe.msgprint(_("{0}").format(result))
	return result

def get_conditions(filters):
	conditions = []
	abbr = {'employee': 'tabTimesheet', 'project': 'tabTimesheet Detail'}
	for key in filters:
		if filters.get(key):
			conditions.append("`%s`.%s = '%s'"%(abbr.get(key), key, filters.get(key)))

	return " and {}".format(" and ".join(conditions)) if conditions else ""

@frappe.whitelist()
def get_target_quantity_complete(docname = None, task = None):
        td = frappe.db.sql("""
                select sum(ifnull(tsd.target_quantity_complete, 0)) as target_quantity_complete
                from `tabTimesheet Detail` tsd, `tabTimesheet` ts
                where ts.task = '{0}'
                and ts.name != '{1}'
                and ts.docstatus != 2
                and tsd.parent = ts.name                
        """.format(task, docname), as_dict=1)

        if td:
                return flt(td[0].target_quantity_complete)
        else:
                return 0.0
