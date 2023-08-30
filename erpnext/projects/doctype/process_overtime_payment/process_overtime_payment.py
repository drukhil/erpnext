# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.custom_utils import check_budget_available, get_branch_cc
from frappe.utils import flt, nowdate, getdate
from frappe.model.document import Document
from erpnext.hr.hr_custom_functions import get_month_details
from erpnext.custom_utils import prepare_gl, check_future_date
from erpnext.custom_workflow import set_user

class ProcessOvertimePayment(Document):
	def validate(self):
		if not self.fiscal_year or not self.month:
			frappe.throw("Fiscal Year/ Month is Required")
	
		if not self.cost_center:
			frappe.throw("Cost Center is not Selected")
	
		if not self.branch:
			frappe.throw(" Branch is Mandiatory")
	
		#set up expense bank account	
		expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		self.expense_bank_account = expense_bank_account
		if not self.expense_bank_account:
			frappe.throw("Expense Bank Account is Missing!. Refresh Cost Center Field")

		#set up Expense Account
                ot_account = frappe.db.get_single_value("HR Accounts Settings", "overtime_account")
                self.ot_account = ot_account
                if not self.ot_account:
                        frappe.throw("Expense Account Not Found, Kindly set up Overtime Account in HR Accounts Settings")

		self.check_duplicate_entries()
		set_user(self)


	def check_duplicate_entries(self):
                not_found = []
                found = []
                for a in self.items:
                        if a.employee not in  found:
                                not_found.append(a.employee)
                        else:
                                found.append(a.employee)
                		frappe.throw("Double Entry is not allowed for {0}".format(found))

	def on_submit(self):
		self.post_general_ledger()
		#self.update_ot()
		# if self.get("items"):
		# 	processed = []
		# 	for a in self.get("items"):
		# 		doc = frappe.get_doc("Overtime Application", a.reference_doc).payment_jv
		# 		if doc.payment_jv:
		# 			processed.append(a.reference_doc)
		# 	frappe.throw("Payment Already Processed for Following OT {0}".format(processed))

	def on_cancel(self):
		if self.clearance_date:
                        frappe.throw("Already done bank reconciliation.")

		frappe.db.sql(""" update `tabOvertime Application` set payment_jv = '' where payment_jv = '{0}'""".format(self.name))
		frappe.db.sql(""" delete from `tabGL Entry` where voucher_type = '{0}' and voucher_no = '{1}'""".format(self.doctype, self.name))
	def get_ot_details(self):
		m = get_month_details(self.fiscal_year, self.month)
                from_date = m['month_start_date']
                to_date = m['month_end_date']
		query = """select name as reference_doc, employee, employee_name, rate as hourly_rate, total_hours, 
			total_amount as total_ot_amount
			from `tabOvertime Application` where docstatus = 1 and workflow_state = 'Approved' 
			and ifnull(payment_jv, '') = '' and  
			bank_name = '{3}' and 
			cost_center in (select name from `tabCost Center` where parent_cost_center = '{2}') order by employee desc
		""".format(from_date, to_date, self.cost_center, self.bank_name)
	
		entries = frappe.db.sql(query, as_dict=True)
                if not entries:
                        frappe.msgprint("OT Payment is already processed or there is no Approved OT to process")

                self.set('items', [])

                for d in entries:
                        doc = frappe.get_doc("Employee", d.employee)
			row = self.append('items', {})
                        row.bank_name = doc.bank_name
			row.bank_account = doc.bank_ac_no
			row.designation = doc.designation
			row.grade = doc.employee_subgroup
			row.cost_center = doc.cost_center	
			row.update(d)

		total = 0.0
                for a in self.get('items'):
                        total += a.total_ot_amount
                self.total_amount = total

	
	def post_general_ledger(self):
		gl_entries = []
		ot_account = frappe.db.get_single_value("HR Accounts Settings", "overtime_account")
                expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
                if not self.cost_center:
                        frappe.throw("Cost Center Is Required")
                if not expense_bank_account:
                        frappe.throw("Setup Default Expense Bank Account for your Branch")
                if not ot_account:
                        frappe.throw("Setup Default Overtime Account in HR Account Setting")
	
		query = """
                        select cost_center, sum(total_ot_amount) as total_ot_amount 
                        from `tabOvertime Payment Item` where docstatus = 1 and parent = '{0}'  
			group by cost_center
                """.format(self.name)
                for d in frappe.db.sql(query, as_dict = True):
			check_budget_available(d.cost_center, ot_account, self.posting_date, d.total_ot_amount, throw_error=True)
			gl_entries.append(
				prepare_gl(self, {"account": expense_bank_account,
					 "credit": flt(d.total_ot_amount),
					 "credit_in_account_currency": flt(d.total_ot_amount),
					 "voucher_no": self.name,
                                         "voucher_type": self.doctype,
					 "cost_center": d.cost_center,
					 "company": self.company
					})
			)

			gl_entries.append(
				prepare_gl(self, {"account": ot_account,
						"debit": flt(d.total_ot_amount),
						"debit_in_account_currency": flt(d.toatl_ot_amount),
						"voucher_no": self.name,
                                         	"voucher_type": self.doctype,
                                         	"cost_center": d.cost_center,
                                         	"company": self.company
						})
				)
		from erpnext.accounts.general_ledger import make_gl_entries
		make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=False)
		self.update_ot()


	def update_ot(self):
                for d in self.get('items'):
                        doc = frappe.get_doc("Overtime Application", d.reference_doc)
                        doc.db_set("payment_jv", self.name)	
