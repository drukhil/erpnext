# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, datetime, get_last_day
from calendar import monthrange
from erpnext.custom_utils import check_budget_available, get_branch_cc

class ProcessMRPayment(Document):
	def validate(self):
                # Setting `monthyear`
		month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(self.month) + 1
		month = str(month) if cint(month) > 9 else str("0" + str(month))
		self.monthyear = str(self.fiscal_year)+str(month)
		total_days = monthrange(cint(self.fiscal_year), cint(month))[1]
                
		if self.items:
			total_ot = total_wages = total_health = salary = 0.0
			
			for a in self.items:
				if self.workflow_state != "Rejected":
					self.duplicate_entry_check(a.employee, a.employee_type, a.idx)
				a.fiscal_year   = self.fiscal_year
				a.month         = self.month
                                
			#	a.total_ot_amount = flt(a.hourly_rate) * flt(a.number_of_hours)
			#	a.total_wage = flt(a.daily_rate) * flt(a.number_of_days)
				
				if a.employee_type == "GEP Employee":
					salary = frappe.db.get_value("GEP Employee", a.employee, "salary")
					if flt(a.total_wage) > flt(salary):
						a.total_wage = flt(salary)

					if flt(total_days) == flt(a.number_of_days):
						a.total_wage = flt(salary)
                                        
				# Ver.1.0.20200205 Begins, Following code added by SHIV on 2020/01/05
				a.total_wage = round(a.total_wage)
				a.total_ot_amount = round(a.total_ot_amount)
				#frappe.throw("total_ot_amount: "+str(a.total_ot_amount))
				# Ver.1.0.20200205 Ends

				a.total_amount = flt(a.total_ot_amount) + flt(a.total_wage)
				total_ot += flt(a.total_ot_amount)
				total_wages += flt(a.total_wage)
				if a.employee_type == "GEP Employee":
					# Ver.1.0.20200205 Begins, Following code added by SHIV on 2020/01/05
					# Follwoing line replcaed by subsequent by SHIV
					#a.health = flt(a.total_wage) * 0.01
					#a.health = round(flt(a.total_wage) * 0.01)
					# Ver.1.0.20200205 Ends
					a.wage_payable = flt(a.total_wage) - flt(a.health)
					total_health += flt(a.health)
				
			total = total_ot + total_wages
			self.wages_amount = flt(total_wages)
			self.ot_amount = flt(total_ot)
			self.total_overall_amount = flt(total)
			if a.employee_type == "GEP Employee":
				self.total_health_amount = total_health
			

	def on_submit(self):
		self.check_budget()
		self.post_journal_entry()

	def before_cancel(self):
		cl_status = frappe.db.get_value("Journal Entry", self.payment_jv, "docstatus")
		if cl_status and cl_status != 2:
			frappe.throw("You need to cancel the journal entry related to this payment first!")
		
		self.db_set('payment_jv', "")
		
	def check_budget(self):
			budget_error= []
			overtime_account = frappe.db.get_single_value ("Projects Accounts Settings",  "mr_overtime_account")
			wages_account = frappe.db.get_single_value ("Projects Accounts Settings", "mr_wages_account")

			error = check_budget_available(self.cost_center, overtime_account, self.posting_date, self.ot_amount, False)
			if error:
					budget_error.append(error)

			errors= check_budget_available(self.cost_center, wages_account, self.posting_date, self.wages_amount, throw_error = False)
			if errors:
					budget_error.append(errors)
			if budget_error:
					for e in budget_error:
							frappe.msgprint(str(e))
					frappe.throw("", title="Insufficient Budget")


	def duplicate_entry_check(self, employee, employee_type, idx):
			pl = frappe.db.sql("""
                                select
                                        i.name,
                                        i.parent,
                                        i.docstatus,
                                        i.person_name,
                                        i.employee
                                from `tabMR Payment Item` i, `tabProcess MR Payment` m
                                where i.employee = '{0}'
                                and i.employee_type = '{1}'
                                and i.fiscal_year = '{2}'
                                and i.month = '{3}'
                                and m.docstatus in (0,1)
                                and i.parent != '{4}'
				and i.parent = m.name
				and m.cost_center = '{5}'
                        """.format(employee, employee_type, self.fiscal_year, self.month, self.name, self.cost_center), as_dict=1)

			for l in pl:
					msg = 'Payment already processed for `{2}({3})`<br>RowId#{1}: Reference# <a href="#Form/Process MR Payment/{0}">{0}</a>'.format(l.parent, idx, l.person_name, l.employee)
					frappe.throw(_("{0}").format(msg), title="Duplicate Record Found")                        
                
	#Populate Budget Accounts with Expense and Fixed Asset Accounts
	def load_employee(self):
		if self.employee_type == "GEP Employee":
			query = "select 'GEP Employee' as employee_type, name as employee, person_name, id_card, rate_per_day as daily_rate, rate_per_hour as hourly_rate from `tabGEP Employee` where status = 'Active'"
		elif self.employee_type == "Muster Roll Employee":
			query = "select 'Muster Roll Employee' as employee_type, r.name as employee, r.person_name, r.id_card, m.rate_per_day as daily_rate, m.rate_per_hour as hourly_rate from `tabMuster Roll Employee` r, tabMusterroll m where r.status = 'Active' and r.name=m.parent order by m.rate_per_day desc limit 1"
		else:
			frappe.throw("Select employee record first!")
	
		if not self.branch:
			frappe.throw("Set Branch before loading employee data")
		else:
			query += " and branch = \'" + str(self.branch) + "\'"	
			
		entries = frappe.db.sql(query, as_dict=True)
		if not entries:
			frappe.msgprint("No Attendance and Overtime Record Found")

		self.set('items', [])

		for d in entries:
			row = self.append('items', {})
			row.update(d)

	def post_journal_entry(self):
		expense_bank_account  = frappe.db.get_single_value("HR Accounts Settings", "salary_payable_account")
		if not expense_bank_account:
			frappe.throw("Setup Default Salary Payable Account in `HR Accounts Settings`")
			
		if self.employee_type == "Muster Roll Employee":
			ot_account = frappe.db.get_single_value("Projects Accounts Settings", "mr_overtime_account")
			if not ot_account:
				frappe.throw("Setup MR Overtime Account in Projects Accounts Settings")
			wage_account = frappe.db.get_single_value("Projects Accounts Settings", "mr_wages_account")
			if not wage_account:
				frappe.throw("Setup MR Wages Account in Projects Accounts Settings")
		elif self.employee_type == "GEP Employee":
			ot_account = frappe.db.get_single_value("Projects Accounts Settings", "gep_overtime_account")
			if not ot_account:
				frappe.throw("Setup GEP Overtime Account in Projects Accounts Settings")
			wage_account = frappe.db.get_single_value("Projects Accounts Settings", "gep_wages_account")
			if not wage_account:
				frappe.throw("Setup GEP Wages Account in Projects Accounts Settings")
		else:
			frappe.throw("Invalid Employee Type")

		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1 
		je.title = "Payment for " + self.employee_type  + " (" + self.branch + ")"
		je.voucher_type = 'Bank Entry'
		je.naming_series = 'Bank Payment Voucher'
		je.remark = 'Payment against : ' + self.name
		je.posting_date = self.posting_date
		je.branch = self.branch
		total_amount = self.total_overall_amount

		if self.total_health_amount and self.employee_type == "GEP Employee":
			total_amount -= flt(self.total_health_amount)

		je.append("accounts", {
				"account": expense_bank_account,
				"cost_center": self.cost_center,
				"credit_in_account_currency": flt(total_amount),
				"credit": flt(total_amount),
			})
	
		if self.ot_amount:	
			je.append("accounts", {
					"account": ot_account,
					"reference_type": "Process MR Payment",
					"reference_name": self.name,
					"cost_center": self.cost_center,
					"debit_in_account_currency": flt(self.ot_amount),
					"debit": flt(self.ot_amount),
				})

		if self.wages_amount:
			if self.total_health_amount and self.employee_type == "GEP Employee":
				health_account = frappe.db.get_value("Salary Component", "Health Contribution", "gl_head")
				if not health_account:
					frappe.throw("No GL Account for Health Contribution")
				je.append("accounts", {
						"account": health_account,
						"reference_type": "Process MR Payment",
						"reference_name": self.name,
						"cost_center": self.cost_center,
						"credit_in_account_currency": flt(self.total_health_amount),
						"credit": flt(self.total_health_amount),
					})

			je.append("accounts", {
					"account": wage_account,
					"reference_type": "Process MR Payment",
					"reference_name": self.name,
					"cost_center": self.cost_center,
					"debit_in_account_currency": flt(self.wages_amount),
					"debit": flt(self.wages_amount),
				})

		je.insert()
		self.db_set("payment_jv", je.name)

		
		if self.total_health_amount and self.employee_type == "GEP Employee":
			health_account = frappe.db.get_value("Salary Component", "Health Contribution", "gl_head")
			if not health_account:
				frappe.throw("No GL Account for Health Contribution")
			hjv = frappe.new_doc("Journal Entry")
			hjv.flags.ignore_permissions = 1 
			hjv.title = "Health Contribution for " + self.employee_type  + " (" + self.branch + ")"
			hjv.voucher_type = 'Bank Entry'
			hjv.naming_series = 'Bank Payment Voucher'
			hjv.remark = 'HC Payment against : ' + self.name
			hjv.posting_date = self.posting_date
			hjv.branch = self.branch

			hjv.append("accounts", {
					"account": health_account,
					"reference_type": "Process MR Payment",
					"reference_name": self.name,
					"cost_center": self.cost_center,
					"debit_in_account_currency": flt(self.total_health_amount),
					"debit": flt(self.total_health_amount),
				})

			hjv.append("accounts", {
					"account": expense_bank_account,
					"cost_center": self.cost_center,
					"credit_in_account_currency": flt(self.total_health_amount),
					"credit": flt(self.total_health_amount),
				})
			hjv.insert()
			

def get_pay_details(employee_type, employee, year, month):
	from_date = "-".join([str(year), str(month), '01'])
	to_date   = str(get_last_day(from_date))

	if employee_type == "GEP Employee":
		return frappe.db.sql("""
			SELECT 
				salary, rate_per_day, rate_per_hour, rate_per_hour_normal
			FROM `tabGEP Employee`
			WHERE name = "{employee}"
		""".format(employee = employee), as_dict = True)
	else:
		return frappe.db.sql("""
			SELECT
				rate_per_day, rate_per_hour, rate_per_hour_normal
			FROM `tabMusterroll`
			WHERE parent = '{employee}'
			AND '{from_date}' <= IFNULL(to_date, '{to_date}')
			AND '{to_date}' >= IFNULL(from_date, '{from_date}')
			ORDER BY IFNULL(to_date,'{to_date}') DESC
			LIMIT 1
		""".format(employee=employee, from_date=from_date, to_date=to_date), as_dict = True)

# def update_mr_rates(employee_type, employee, cost_center, from_date, to_date):
# 	# Updating wage rate
# 	rates = frappe.db.sql("""
# 		SELECT
#             GREATEST(IFNULL(from_date,'{from_date}'),'{from_date}') AS from_date, 
# 			LEAST(IFNULL(to_date,'{to_date}'),'{to_date}') AS to_date, 
# 			rate_per_day, rate_per_hour, rate_per_hour_normal
# 		FROM `tabMusterroll`
# 		WHERE parent = '{employee}'
# 		AND '{year_month}' BETWEEN DATE_FORMAT(IFNULL(from_date,'{from_date}'),'%Y%m') 
# 			AND DATE_FORMAT(IFNULL(to_date,'{to_date}'),'%Y%m')
# 	""".format(employee=employee, year_month=str(to_date)[:4]+str(to_date)[5:7],
# 	from_date=from_date, to_date=to_date), as_dict = True)
 
# 	for r in rates:
# 		frappe.db.sql("""
# 			update `tabAttendance Others`
# 			set rate_per_day = {rate_per_day}
# 			where employee_type = '{employee_type}'
# 			and employee = '{employee}'
# 			and `date` between '{from_date}' and '{to_date}'
# 			and status = 'Present'
# 			and docstatus = 1 
# 		""".format(
# 			rate_per_day=r.rate_per_day,
# 			employee_type=employee_type,
# 			employee=employee,
# 			from_date=r.from_date,
# 			to_date=r.to_date
# 		))
# 		frappe.db.sql("""
# 			update `tabOvertime Entry`
# 			set rate_per_hour = {rate_per_hour}, rate_per_hour_normal = {rate_per_hour_normal}
# 			where employee_type = '{employee_type}'
# 			and number = '{employee}'
# 			and `date` between '{from_date}' and '{to_date}'
# 			and docstatus = 1 
# 		""".format(
# 			rate_per_hour=r.rate_per_hour,
# 			rate_per_hour_normal = r.rate_per_hour_normal,
# 			employee_type=employee_type,
# 			employee=employee,
# 			from_date=r.from_date,
# 			to_date=r.to_date
# 		))
# 	frappe.db.commit()

@frappe.whitelist()
def get_records(employee_type, fiscal_year, fiscal_month, cost_center, branch, dn):
	''' 
	This method updates the follwoing details for the given month 
		1. `tabAttendance Others`.rate_per_day
		2. `tabOvertime Entry`.rate_per_hour & `tabOvertimeEntry.rate_per_hour_normal`
	'''
	month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(fiscal_month) + 1
	month = str(month) if cint(month) > 9 else str("0" + str(month))

	total_days = monthrange(cint(fiscal_year), cint(month))[1]
	from_date = str(fiscal_year) + '-' + str(month) + '-' + str('01')
	to_date   = str(fiscal_year) + '-' + str(month) + '-' + str(total_days)

	data    = []
	master  = frappe._dict()
	emp_list = frappe.db.sql("""
		SELECT e.name, e.person_name, e.id_card, e.status, e.designation, 
			e.salary, bank_name AS bank, bank_ac_no AS account_no
		FROM `tab{employee_type}` as e
		INNER JOIN `tabMusterroll`
		INNER JOIN 
			(
				SELECT employee
				FROM `tabAttendance Others`
				WHERE employee_type = '{employee_type}'
				AND date between '{from_date}' and '{to_date}'
				AND cost_center = '{cost_center}'
				AND status = 'Present'
				AND docstatus = 1
			  	UNION
				SELECT number as employee
				FROM `tabOvertime Entry`
				WHERE employee_type = '{employee_type}'
				AND date between '{from_date}' and '{to_date}'
				AND cost_center = '{cost_center}'
				AND docstatus = 1
			) as r
			ON e.name=r.employee
		WHERE e.status = 'Active'
			AND NOT EXISTS(
					SELECT 1
					FROM `tabMR Payment Item` i, `tabProcess MR Payment` m
					WHERE m.fiscal_year = '{fiscal_year}'
					AND m.month = '{fiscal_month}'
					AND m.docstatus < 2
					AND m.cost_center = '{cost_center}'
					AND m.name != '{dn}'
					AND i.parent = m.name
					AND i.employee = e.name
					AND i.employee_type = '{employee_type}'
				)
	""".format(employee_type=employee_type, fiscal_year=fiscal_year, fiscal_month=fiscal_month,
	dn=dn, cost_center=cost_center, from_date = from_date, to_date = to_date), as_dict=True)

	for e in emp_list:
		pay_details=get_pay_details(employee_type, e.name, fiscal_year, month)
		rate_per_day 		 = flt(pay_details[0].get("rate_per_day"))
		rate_per_hour 		 = flt(pay_details[0].get("rate_per_hour"))
		rate_per_hour_normal = flt(pay_details[0].get("rate_per_hour_normal"))
		master.setdefault(e.name, frappe._dict({
			"type": employee_type,
			"employee": e.name,
			"person_name": e.person_name,
			"id_card": e.id_card,
			"rate_per_day": rate_per_day,
			"rate_per_hour": rate_per_hour,
			"rate_per_hour_normal": rate_per_hour_normal,
			"designation" : e.designation,
			"account_no" : e.account_no,
			"bank" : e.bank,
			"salary": e.salary
		}))
			
	rest_list = frappe.db.sql("""
		SELECT employee,
			SUM(number_of_days)     AS number_of_days,
			SUM(number_of_hours)    AS number_of_hours,
			SUM(number_of_hours_special)    AS number_of_hours_special,
			SUM(total_wage)         AS total_wage,
			SUM(total_ot)           AS total_ot,
			{total_days} 			AS noof_days_in_month
		FROM (
			SELECT DISTINCT employee, date, 
				1 AS number_of_days, 0 AS number_of_hours, 0 AS number_of_hours_special,
				IFNULL(rate_per_day,0) AS total_wage, 0 AS total_ot
			FROM `tabAttendance Others`
			WHERE employee_type = '{employee_type}' AND docstatus = 1
			AND date BETWEEN '{from_date}' AND '{to_date}'
			AND cost_center = '{cost_center}' AND status = 'Present'
			UNION ALL
			SELECT DISTINCT number AS employee, date, 
				0 AS number_of_days, ifnull(number_of_hours,0) AS number_of_hours,
				ifnull(number_of_hours_special,0) AS number_of_hours_special, 0 AS total_wage, 
			    (IFNULL(number_of_hours,0) * IFNULL(rate_per_hour_normal,0) + IFNULL(number_of_hours_special,0) * IFNULL(rate_per_hour,0)) AS total_ot	
			FROM `tabOvertime Entry`
			WHERE employee_type = '{employee_type}'
			AND date BETWEEN '{from_date}' AND '{to_date}'
			AND cost_center = '{cost_center}'
			AND docstatus = 1
		) AS abc
		GROUP BY employee
	""".format(employee_type = employee_type, from_date = from_date, to_date = to_date, 
	cost_center = cost_center, total_days = total_days), as_dict=True)

	#ifnull(number_of_hours,0)*ifnull(rate_per_hour_normal,0) as total_ot
	for r in rest_list:
		if master.get(r.employee) and (flt(r.total_wage)+flt(r.total_ot)):
			r.employee_type = r.type
			master[r.employee].update(r)
			data.append(master[r.employee])
					
	if data:
		return data
	else:
		frappe.throw(_("No data found!"),title="No Data Found!")

@frappe.whitelist()
def check_if_holiday_overtime_entry(branch, date, fiscal_year = None, fiscal_month = None):
	from datetime import datetime
	is_holiday = 0
	holiday_list = frappe.db.get_value("Branch", branch, "holiday_list")

	holiday_dates = frappe.db.sql("select holiday_date from `tabHoliday` where parent='{}'".format(holiday_list), as_dict=1)

	# date = []
	for holiday_date in holiday_dates:
		if datetime.strptime(str(date),"%Y-%m-%d") == datetime.strptime(str(holiday_date.holiday_date),"%Y-%m-%d"):
			is_holiday = 1
	return is_holiday