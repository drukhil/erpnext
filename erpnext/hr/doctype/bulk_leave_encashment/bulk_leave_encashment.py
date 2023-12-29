# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, flt, today, money_in_words, cint
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on
from erpnext.hr.doctype.salary_structure.salary_structure import get_basic_and_gross_pay
from erpnext.hr.doctype.leave_encashment.leave_encashment import get_salary_structure
from erpnext.hr.hr_custom_functions import get_salary_tax
from datetime import *

class BulkLeaveEncashment(Document):
	def validate(self):
		# self.validate_workflow_state()
		if not self.encashment_date:
			self.encashment_date = getdate(nowdate())
		self.get_leave_details_for_encashment()
		self.calculate_amount()
		# notify_workflow_states(self)

	def on_submit(self):
		# self.update_encashed_in_leave_allocation()
		self.adjust_leave()
		self.post_accounts_entry()
		# notify_workflow_states(self)

	def on_cancel(self):
		# self.update_encashed_in_leave_allocation(cancel=1)
		self.adjust_leave(cancel=True)
		# notify_workflow_states(self)
	
	def calculate_amount(self):
		total_encashment_amount = net_payable = 0
		for d in self.items:
			total_encashment_amount += d.encashment_amount
			net_payable += d.payable_amount
		
		self.total_encashment_amount = flt(total_encashment_amount,2)
		self.net_payable_amount = flt(net_payable,2)
	
	def update_encashed_in_leave_allocation(self, cancel=0):
		if cint(cancel) == 0:
			for d in self.items:
				frappe.db.set_value("Leave Allocation", d.leave_allocation, "total_leaves_encashed",
					frappe.db.get_value('Leave Allocation', d.leave_allocation, 'total_leaves_encashed') + d.encashable_days)
		else:
			for d in self.items:
				frappe.db.set_value("Leave Allocation", d.leave_allocation, "total_leaves_encashed",
					frappe.db.get_value('Leave Allocation', d.leave_allocation, 'total_leaves_encashed') - d.encashable_days)

	def create_leave_ledger_entry(self, submit=True):
		for d in self.items:
			args = frappe._dict(
				employee=d.employee,
				employee_name=d.employee_name,
				leaves=d.encashable_days * -1,
				from_date=self.encashment_date,
				to_date=self.encashment_date,
				is_carry_forward=0
			)
			create_leave_ledger_entry(self, args, submit)

	def adjust_leave(self, cancel=False):
		for d in self.items:
			leave_allocation = frappe.db.sql("""
					select name, from_date, to_date, total_leaves_allocated
					from `tabLeave Allocation`
					where employee=%s and leave_type=%s and docstatus=1 
					order by to_date desc limit 1
			""", (d.employee, self.leave_type), as_dict=1)
			if leave_allocation:
					doc = frappe.get_doc("Leave Allocation", leave_allocation[0].name)
					if cancel:
							new_total = (flt(doc.total_leaves_allocated) + flt(d.encashable_days))
							days = flt(self.encashable_days)
							self.db_set("leave_adjusted", 0)
					else:
							new_total = (flt(doc.total_leaves_allocated) - flt(d.encashable_days))
							days = 0 - flt(d.encashalbe_days)
							self.db_set("leave_adjusted", 1)
					doc.db_set("total_leaves_allocated", new_total)
					doc.db_set("leave_encashment", self.name)
					doc.db_set("encashed_days", days)
	def get_leave_details_for_encashment(self):
		# if not frappe.db.get_value("Leave Type", self.leave_type, 'allow_encashment'):
		# 	frappe.throw(_("Leave Type {0} is not encashable").format(self.leave_type))

		for emp in self.items:
			allocation = self.get_leave_allocation(emp.employee)

			if not allocation:
				frappe.throw(_("No Leaves Allocated to Employee: {0} for Leave Type: {1}").format(emp.employee, self.leave_type))

			# emp.leave_balance = get_leave_balance_on(emp.employee, today(), self.leave_type, consider_all_leaves_in_the_allocation_period=True)

			# if not emp.employee_group:
			# 	emp.employee_group = frappe.db.get_value("Employee", emp.employee, "employee_group")
			
			# emp.encashable_days = 30 if emp.leave_balance >= 30 else emp.leave_balance

			# if emp.encashable_days > emp.leave_balance:
			# 	frappe.throw("Encashable Days  cannot be more than Leave Balance")
			sal_struc_name = get_salary_structure()
			if sal_struc_name:
				sal_struc= frappe.get_doc("Salary Structure",sal_struc_name)
				for d in sal_struc.earnings:
					if d.salary_component == 'Basic Pay':
						basic_pay = flt(d.amount)
			else:
				frappe.throw(_("No Active salary structure found for employee {}.".format(emp.employee)))
			if basic_pay > 0:
				emp.current_basic_pay = basic_pay
				emp.encashment_amount = flt((basic_pay/30) * flt(emp.encashable_days),2)
				emp.salary_structure = sal_struc_name
				emp.encashment_tax = get_salary_tax(emp.encashment_amount)
				emp.payable_amount = flt((emp.encashment_amount) - flt(emp.encashment_tax),2)

			emp.leave_allocation = allocation.name
		return True
	
	def get_leave_allocation(self, employee=None):
		leave_allocation = frappe.db.sql("""
                        select name, from_date, to_date, total_leaves_allocated
                        from `tabLeave Allocation`
                        where employee='{}' and leave_type='{}' and docstatus=1 
                        order by to_date desc limit 1""".format(employee, self.leave_type), as_dict=1)
		return leave_allocation[0] if leave_allocation else None
	@frappe.whitelist()
	def get_employees(self):
		# if not self.leave_period or not self.leave_type:
		# 	frappe.throw("Either Leave Type/Leave Period is missing")
		
		self.set('items', [])
		query = """
				select name as employee, employee_name, branch, designation, employment_type, employee_subgroup as grade,
				employee_group, bank_name, bank_ac_no
				from `tabEmployee` where status = 'Active'
		"""
		
		entries = frappe.db.sql(query, as_dict=True)
		self.set('items', entries)
	
	def post_accounts_entry(self):
		if not self.cost_center:
			frappe.throw("Setup Cost Center for employee in Employee Information")

		expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		if not expense_bank_account:
			frappe.throw("Setup Default Expense Bank Account for your Branch")

		expense_account = frappe.db.get_single_value("HR Accounts Settings", "leave_encashment_account")
		if not expense_account:
			frappe.throw("Setup Leave Encashment Account in HR Accounts Settings")

		tax_account = frappe.db.get_single_value("HR Accounts Settings", "salary_tax_account")
		if not tax_account:
			frappe.throw("Setup Tax Account in HR Accounts Settings")
		
		# default_bank_account = get_bank_account(self.branch)
		# default_payable_account = frappe.db.get_single_value("HR Accounts Settings", "salary_payable_account")
		company_cc			  = frappe.db.get_value("Company", self.company,"company_cost_center")

		cc = {}
		encashment_tax = net_payable = 0 
		for det in self.items:
			encashment_tax += det.encashment_tax
			net_payable += det.payable_amount
			cost_center = frappe.db.get_value("Branch", det.branch, "cost_center")
			if cost_center not in cc:
				cc.update({
					cost_center: {
			   			"payable_amount": det.payable_amount,
			   			"encashment_amount": det.encashment_amount,
			   			"encashment_tax": det.encashment_tax,
					}
		   		})
			else:
				cc[cost_center]['payable_amount'] += det.payable_amount
				cc[cost_center]['encashment_amount'] += det.encashment_amount
				cc[cost_center]['encashment_tax'] += det.encashment_tax
		
		#Payables Journal Entry -----------------------------------------------
		payables_je = frappe.new_doc("Journal Entry")
		payables_je.voucher_type= "Journal Entry"
		payables_je.naming_series = "Journal Voucher"
		payables_je.title = "Bulk Leave Encashment "+str(self.fiscal_year)
		payables_je.remark =  "Bulk Leave Encashment "+str(self.fiscal_year)
		payables_je.posting_date = self.encashment_date			   
		payables_je.company = self.company
		payables_je.branch = self.branch
		payables_je.reference_type = self.doctype
		payables_je.reference_name =  self.name
		total = total_allowance = 0
		for rec in cc:
			payables_je.append("accounts", {
					"account": expense_account,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": rec,
					"business_activity": self.business_activity,
					"debit_in_account_currency": flt(cc[rec]['encashment_amount'],2),
					"debit": flt(cc[rec]['encashment_amount'],2),
				})
		#Salary Tax
		if encashment_tax > 0:
			payables_je.append("accounts", {
					"account": tax_account,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": company_cc,
					"business_activity": self.business_activity,
					"credit_in_account_currency": flt(encashment_tax,2),
					"party_check": 0,
					"credit": flt(encashment_tax,2),
				})
		#To Bank Account
		payables_je.append("accounts", {
				"account": expense_bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": self.business_activity,
				"credit_in_account_currency": flt(net_payable,2),
				"credit": flt(net_payable,2),
			})

		payables_je.flags.ignore_permissions = 1
		payables_je.insert()
		# payables_je.submit()
		self.db_set("journal_entries_created", 1)
		frappe.db.commit()
