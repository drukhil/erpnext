# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint
from calendar import monthrange
from erpnext.custom_utils import check_budget_available, get_branch_cc

class ProcessMRPayment(Document):
	def validate(self):
		self.validate_duplicate_entry()
                # Setting `monthyear`
		month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(self.month) + 1
		month = str(month) if cint(month) > 9 else str("0" + str(month))
                self.monthyear = str(self.fiscal_year)+str(month)
                total_days = monthrange(cint(self.fiscal_year), cint(month))[1]
		if self.items:
			total_ot = total_wage = total_health = salary = total_gratuity = 0.0
			
			for a in self.items:
                                self.duplicate_entry_check(a.employee, a.employee_type, a.idx)
                                a.fiscal_year   = self.fiscal_year
                                a.month         = self.month
 	
				if a.employee_type  == "Operator":
					#"Open Air Prisoner"):
                                        salary = frappe.db.get_value(a.employee_type, a.employee, "salary")
                                        if flt(a.total_wage) > flt(salary):
                                                a.total_wage = flt(salary)

                                        if flt(total_days) == round(flt(a.number_of_days),2):
                                                a.total_wage = flt(salary)
                                if a.employee_type == 'DFG':
					salary = frappe.db.get_value(a.employee_type, a.employee, "salary")
					if flt(a.total_wage) > flt(salary):
						a.total_wage = flt(salary)
					if flt(total_days) == round(flt(a.number_of_days),2):
						a.total_wage = flt(salary)
					if round(flt(a.number_of_days),2) >= 21:
						a.total_wage = flt(salary)

				if a.employee_type == 'Open Air Prisoner':
					salary = flt(total_days) * flt(a.daily_rate)
					if flt(a.total_wage) > flt(salary):
                                                a.total_wage = flt(salary)

                                        if flt(total_days) == round(flt(a.number_of_days),2):
                                                a.total_wage = flt(salary)
        
				# Ver.1.0.20200205 Begins, Following code added by SHIV on 2020/01/05
				a.total_wage = round(a.total_wage)
				a.total_ot_amount = round(a.total_ot_amount)
				a.gratuity_amount = round(a.gratuity_amount)
				# Ver.1.0.20200205 Ends

				if a.employee_type == "Open Air Prisoner":
					gratuity_percent = frappe.db.get_single_value("HR Settings", "gratuity_percent")
					#gratuity changed from 75% to 50% on 28/12/2020 as per instruction from Ms. Thinley Dema
					#a.total_gratuity = 0.75 * flt(total_wage)
					a.total_gratuity = flt(gratuity_percent)/100 * flt(total_wage)
					a.wage_payable = flt(a.total_wage) - flt(a.gratuity_amount)
				a.total_amount = flt(a.total_ot_amount) + flt(a.total_wage)
                                total_ot += flt(a.total_ot_amount)
                                total_wage += flt(a.total_wage)
                                total_gratuity += flt(a.gratuity_amount)

			total = total_ot + total_wage
			self.wages_amount = flt(total_wage)
			self.ot_amount = flt(total_ot)
			self.total_overall_amount = flt(total)
			self.gratuity_amount = flt(total_gratuity)
			

	def on_submit(self):
		# self.check_budget()
		self.post_journal_entry()

	def before_cancel(self):
		cl_status = frappe.db.get_value("Journal Entry", self.payment_jv, "docstatus")
		if cl_status and cl_status != 2:
			frappe.throw("You need to cancel the journal entry related to this payment first!")
		
		self.db_set('payment_jv', "")
		
	def check_budget(self):
                budget_error= []
		expense_bank_account, ot_account, wage_account, gratuity_account = self.prepare_gls()
		wages_amount = self.wages_amount
		if self.employee_type == 'Open Air Prisoner' and self.gratuity_amount:
			wages_amount = wages_amount - flt(self.gratuity_amount)

                error = check_budget_available(self.cost_center, ot_account, self.posting_date, self.ot_amount, False)
                if error:
                        budget_error.append(error)

                errors= check_budget_available(self.cost_center, wage_account, self.posting_date, wages_amount, throw_error = False)
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
                        """.format(employee, employee_type, self.fiscal_year, self.month, self.name, frappe.db.escape(self.cost_center)), as_dict=1)

                for l in pl:
                        msg = 'Payment already processed for `{2}({3})`<br>RowId#{1}: Reference# <a href="#Form/Process MR Payment/{0}">{0}</a>'.format(l.parent, idx, l.person_name, l.employee)
                        frappe.throw(_("{0}").format(msg), title="Duplicate Record Found")                        
                
	#Populate Budget Accounts with Expense and Fixed Asset Accounts
	def load_employee(self):
		if self.employee_type == "Operator":
			query = "select 'Operator' as employee_type, name as employee, person_name, id_card, rate_per_day as daily_rate, rate_per_hour as hourly_rate from `tabOperator` where	status = 'Active'"
		
		elif self.employee_type == "DFG":
			query = "select 'DFG' as employee_type, name as employee, person_name, id_card, rate_per_day as daily_rate, rate_per_hour as hourly_rate from `tabDFG` where status = 'Active'"

		elif self.employee_type == "Open Air Prisoner":
                        query = "select 'Open Air Prisoner' as employee_type, name as employee, person_name, id_card, rate_per_day as daily_rate, rate_per_hour as hourly_rate, gratuity_fund as graduity from `tabOpen Air Prisoner` where status = 'Active'"

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

	def validate_duplicate_entry(self):
		data = []
		for a in self.items:
			if a.employee not in data:
				data.append(a.employee)
			else:
				frappe.throw("Duplicate Employee entry {} at #Row. {}".format(a.employee, a.idx))

	def post_journal_entry(self):
		expense_bank_account, ot_account, wage_account, gratuity_account = self.prepare_gls()

		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1 
		je.title = "Payment for " + self.employee_type  + " (" + self.branch + ")" + "(" + self.month + ")"
		je.voucher_type = 'Bank Entry'
		je.naming_series = 'Bank Payment Voucher'
		je.remark = 'Payment against : ' + self.name;
		je.posting_date = self.posting_date
		je.branch = self.branch
		total_amount = self.total_overall_amount
		wages_amount = self.wages_amount

		if self.gratuity_amount and self.employee_type == "Open Air Prisoner":
			total_amount = self.total_overall_amount -  flt(self.gratuity_amount)
			wages_amount = self.wages_amount - flt(self.gratuity_amount)			

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
			je.append("accounts", {
					"account": wage_account,
					"reference_type": "Process MR Payment",
					"reference_name": self.name,
					"cost_center": self.cost_center,
					"debit_in_account_currency": flt(wages_amount),
					"debit": flt(wages_amount),
				})

		je.insert()
		self.db_set("payment_jv", je.name)

		
		if self.gratuity_amount and self.employee_type == "Open Air Prisoner":
			hjv = frappe.new_doc("Journal Entry")
			hjv.flags.ignore_permissions = 1 
			hjv.title = "Gratuity Fund for" + " " + self.employee_type  + " (" + self.branch + ")" + "(" + self.month + ")"
			hjv.voucher_type = 'Bank Entry'
			hjv.naming_series = 'Bank Payment Voucher'
			hjv.remark = 'Gratuity Fund Release against : ' + self.name;
			hjv.posting_date = self.posting_date
			hjv.branch = self.branch


			hjv.append("accounts", {
                                        "account": expense_bank_account,
                                        "cost_center": self.cost_center,
                                        "credit_in_account_currency": flt(self.gratuity_amount),
                                        "credit": flt(self.gratuity_amount),
                                })


			hjv.append("accounts", {
					"account": gratuity_account,
					"reference_type": "Process MR Payment",
					"reference_name": self.name,
					"cost_center": self.cost_center,
					"debit_in_account_currency": flt(self.gratuity_amount),
					"debit": flt(self.gratuity_amount),
				})

			hjv.insert()
			

	def prepare_gls(self):
		gratuity_account = None
                expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
                if not expense_bank_account:
                        frappe.throw("Setup Default Expense Bank Account for your Branch")

                if self.employee_type == "Muster Roll Employee":
                        ot_account = frappe.db.get_single_value("Projects Accounts Settings", "mr_overtime_account")
                        if not ot_account:
                                frappe.throw("Setup MR Overtime Account in Projects Accounts Settings")
                        wage_account = frappe.db.get_single_value("Projects Accounts Settings", "mr_wages_account")
                        if not wage_account:
                                frappe.throw("Setup MR Wages Account in Projects Accounts Settings")

		elif self.employee_type =="DFG":
			ot_account = frappe.db.get_single_value("Projects Accounts Settings", "dfg_overtime_account")
			if not ot_account:
				frappe.throw("Setup Overtime Account for DFG in Projects Accounts Settings")
			wage_account = frappe.db.get_single_value("Projects Accounts Settings", "dfg_wage_account")
			if not wage_account:
				frappe.throw("Setup DFG Wage account in Projects Accounts Setting")                

		elif self.employee_type == "Operator":
                        ot_account = frappe.db.get_single_value("Projects Accounts Settings", "operator_overtime_account")
                        if not ot_account:
                                frappe.throw("Setup Operator Overtime Account in Projects Accounts Settings")
                        wage_account = frappe.db.get_single_value("Projects Accounts Settings", "operator_allowance_account")
			if not wage_account:
                                frappe.throw("Setup Operator Allowance Account in Projects Accounts Settings")

                elif self.employee_type == "Open Air Prisoner":
                        ot_account = frappe.db.get_single_value("Projects Accounts Settings", "oap_overtime_account")
                        if not ot_account:
                                frappe.throw("Setup OAP Overtime Account in Projects Accounts Settings")
                        wage_account = frappe.db.get_single_value("Projects Accounts Settings", "oap_wage_account")
                        if not wage_account:
                                frappe.throw("Setup OAP Wage Account in Projects Accounts Settings")
                        gratuity_account = frappe.db.get_single_value("Projects Accounts Settings", "oap_gratuity_account")
                        if not gratuity_account:
                                frappe.throw("Setup OAP Gratuity Account in Projects Accounts Settings")
                else:
                        frappe.throw("Invalid Employee Type")

                return expense_bank_account, ot_account, wage_account, gratuity_account
	

def update_mr_rates(employee_type, employee, cost_center, from_date, to_date):
	# Updating wage rate
	rates = frappe.db.sql("""
		select
                        greatest(ifnull(from_date,'{from_date}'),'{from_date}') as from_date, 
			least(ifnull(to_date,'{to_date}'),'{to_date}') as to_date, 
			rate_per_day,
			rate_per_hour
		from `tabMusterroll`
		where parent = '{employee}'
		and '{year_month}' between date_format(ifnull(from_date,'{from_date}'),'%Y%m') and date_format(ifnull(to_date,'{to_date}'),'%Y%m')
	""".format(
		employee=employee,
		year_month=str(to_date)[:4]+str(to_date)[5:7],
		from_date=from_date,
		to_date=to_date
	),
	as_dict=True)
#	frappe.msgprint('{0}'.format(rates))
	for r in rates:
		frappe.db.sql("""
			update `tabAttendance Others`
			set rate_per_day = {rate_per_day}
			where employee_type = '{employee_type}'
			and employee = '{employee}'
			and `date` between '{from_date}' and '{to_date}'
			and status in ('Present', 'Half Day')
			and docstatus = 1 
		""".format(
			rate_per_day=r.rate_per_day,
			employee_type=employee_type,
			employee=employee,
			from_date=r.from_date,
			to_date=r.to_date
		))

		frappe.db.sql("""
			update `tabOvertime Entry`
			set rate_per_hour = {rate_per_hour}
			where employee_type = '{employee_type}'
			and number = '{employee}'
			and `date` between '{from_date}' and '{to_date}'
			and docstatus = 1 
		""".format(
			rate_per_hour=r.rate_per_hour,
			employee_type=employee_type,
			employee=employee,
			from_date=r.from_date,
			to_date=r.to_date
		))

	frappe.db.commit()

@frappe.whitelist()
def get_records(employee_type, fiscal_year, fiscal_month, from_date, to_date, cost_center, branch, dn):
	month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(fiscal_month) + 1
        month = str(month) if cint(month) > 9 else str("0" + str(month))

        total_days = monthrange(cint(fiscal_year), cint(month))[1]
        from_date = str(fiscal_year) + '-' + str(month) + '-' + str('01')
        to_date   = str(fiscal_year) + '-' + str(month) + '-' + str(total_days)

        data    = []
        master  = frappe._dict()
	
        emp_list = frappe.db.sql("""
                                select
                                        name,
                                        person_name,
                                        id_card,
                                        rate_per_day,
                                        rate_per_hour,
					status,
					designation,
					bank,
					account_no,
                                        salary
                                from `tab{employee_type}` as e
                                where not exists(
                                        select 1
                                        from `tabMR Payment Item` i, `tabProcess MR Payment` m
                                        where m.fiscal_year = '{fiscal_year}'
					and m.month = '{fiscal_month}'
					and m.docstatus < 2
					and m.cost_center = '{cost_center}'
					and m.name != '{dn}'
					and i.parent = m.name
					and i.employee = e.name
					and i.employee_type = '{employee_type}'
                                )
				and (
					exists(
					select 1
					from `tabAttendance Others`
                    			where employee_type = '{employee_type}'
					and employee = e.name
                                        and date between '{from_date}' and '{to_date}'
                                        and cost_center = '{cost_center}'
                                        and status in ('Present', 'Half Day')
                                        and docstatus = 1
					)
					or
					exists(
					select 1
					from `tabOvertime Entry`
                                        where employee_type = '{employee_type}'
					and number = e.name
                                        and date between '{from_date}' and '{to_date}'
                                        and cost_center = '{cost_center}'
                                        and docstatus = 1
					)

				)
        """.format(
        		employee_type=employee_type,
        		fiscal_year=fiscal_year,
        		fiscal_month=fiscal_month,
        		dn=dn,
        		cost_center=frappe.db.escape(cost_center),
			from_date = from_date,
			to_date = to_date
        ),as_dict=True)
	for e in emp_list:
                master.setdefault(e.name, frappe._dict({
                        "type": employee_type,
                        "employee": e.name,
                        "person_name": e.person_name,
                        "id_card": e.id_card,
                        "rate_per_day": e.rate_per_day,
                        "rate_per_hour": e.rate_per_hour,
			"designation" : e.designation,
			"account_no" : e.account_no,
			"bank" : e.bank,
                        "salary": e.salary
                }))
		if employee_type == "Muster Roll Employee":
	        	update_mr_rates(employee_type, e.name, cost_center, from_date, to_date);
		if employee_type in ('Operator', 'Open Air Prisoner', 'DFG'):
		
			frappe.db.sql("""
                        update `tabAttendance Others`
                        set rate_per_day = {rate_per_day}
                        where employee_type = '{employee_type}'
                        and employee = '{employee}'
                        and status in ('Present', 'Half Day')
                        and docstatus = 1 
                """.format(
                        rate_per_day=flt(e.rate_per_day),
                        employee_type=employee_type,
                        employee=e.name,
                ))

	                frappe.db.sql("""
                        update `tabOvertime Entry`
                        set rate_per_hour = {rate_per_hour}
                        where employee_type = '{employee_type}'
                        and number = '{employee}'
                        and docstatus = 1 
                """.format(
                        rate_per_hour=flt(e.rate_per_hour),
                        employee_type=employee_type,
                        employee=e.name,
                ))

        	frappe.db.commit()     
			
        rest_list = frappe.db.sql("""
                                select employee,
                                        sum(number_of_days)     as number_of_days,
                                        sum(number_of_hours)    as number_of_hours,
                                        sum(total_wage)         as total_wage,
                                        sum(total_ot)           as total_ot,
                                        {4} as noof_days_in_month
                                from (
                                        select distinct
                                                employee,
						date,
                                                1                       as number_of_days,
                                                0                       as number_of_hours,
                                                ifnull(rate_per_day,0)  as total_wage,
                                                0                       as total_ot
                                        from `tabAttendance Others`
                                        where employee_type = '{0}'
                                        and date between '{1}' and '{2}'
                                        and cost_center = '{3}'
                                        and status = 'Present'
                                        and docstatus = 1
                                        UNION ALL
					select distinct
                                                employee,
                                                date,
                                                .5                     as number_of_days,
                                                0                       as number_of_hours,
                                                ifnull(rate_per_day,0)  as total_wage,
                                                0                       as total_ot
                                        from `tabAttendance Others`
                                        where employee_type = '{0}'
                                        and date between '{1}' and '{2}'
                                        and cost_center = '{3}'
                                        and status = 'Half Day'
                                        and docstatus = 1
					UNION ALL
                                        select distinct
                                                number                  as employee,
						date,
                                                0                       as number_of_days,
                                                ifnull(number_of_hours,0) as number_of_hours,
                                                0                       as total_wage,
                                                ifnull(number_of_hours,0)*ifnull(rate_per_hour,0) as total_ot
                                        from `tabOvertime Entry`
                                        where employee_type = '{0}'
                                        and date between '{1}' and '{2}'
                                        and cost_center = '{3}'
                                        and docstatus = 1
                                ) as abc
                                group by employee
        """.format(employee_type, from_date, to_date, frappe.db.escape(cost_center), total_days), as_dict=True)


        for r in rest_list:
		gratuity = 0.0
                gratuity_percent = frappe.db.get_single_value("HR Settings", "gratuity_percent")
		if master.get(r.employee) and (flt(r.total_wage)+flt(r.total_ot)):
			r.employee_type = r.type
			r.gratuity = flt(gratuity_percent)/100 * flt(r.total_wage)
			master[r.employee].update(r)
			data.append(master[r.employee])
                   
	if data:
		return data
	else:
		frappe.throw(_("No data found!"),title="No Data Found!")
