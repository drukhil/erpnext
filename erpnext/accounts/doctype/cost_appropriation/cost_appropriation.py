# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.accounts.general_ledger import make_gl_entries
from frappe import _
from erpnext.controllers.accounts_controller import AccountsController

class CostAppropriation(AccountsController):
	def validate(self):
		self.validate__accounts()
		if self.items:
			total = 0
			for d in self.items:
				total += flt(d.amount)
				self.total_amount= total
		# self.set_user(self)

	def validate__accounts(self):
		if self.cost_type == 'Hire Charge':
			self.account = frappe.db.get_single_value ("Accounts Settings", "hire_charge")
		if self.cost_type == 'HSD':
			self.hsd = frappe.db.get_single_value ("Accounts Settings", "hsd")
		
		if self.cost_type == 'Lubricant':
			self.account = frappe.db.get_single_value ("Accounts Settings", "lubricant")
		if self.cost_type == 'GCE':
			self.account = frappe.db.get_single_value ("Accounts Settings", "gce")
		if self.cost_type == 'Overtime Payment':
			self.hsd = frappe.db.get_single_value ("Accounts Settings", "overtime_payment")
		
		if self.cost_type == 'Muster Roll Employee':
			self.account = frappe.db.get_single_value ("Accounts Settings", "muster_roll_employee")
        	if self.cost_type =='Operator Allowance':
            		self.account = frappe.db.get_single_value ("Accounts Settings", "operator_allowance")
		if self.cost_type == 'OAP Salary':
            		self.account = frappe.db.get_single_value ("Accounts Settings", "oap_salary")
				

	def on_submit(self):
		self.post_gl_entry()

	def on_cancel(self):
		self.post_gl_entry()

	def get_details(self):
		query = """ select ea.posting_date, eai.activity as cost_center, eai.equipment, eai.amount, ea.name as reference_no from 
                                `tabExpense Allocation` ea, `tabExpense Allocation Item` eai  where ea.name = eai.parent  
                                and ea.posting_date >= '{0}' and ea.posting_date <= '{1}' 
                                and ea.docstatus = 1 and ea.branch = '{2}' and ea.cost_type = '{3}'
                                and not exists (
                                        select 1 from `tabCost Appropriation Item` i
                                        inner join `tabCost Appropriation` a
                                        on i.parent = a.name
                                        where i.reference_no = ea.name
                                        and a.docstatus = 1
                                )""".format(self.from_date, self.to_date, self.branch, self.cost_type)	
		

		entries = frappe.db.sql(query, as_dict=True)
		if not entries:
			frappe.msgprint("No Record Found")

		self.set('items', [])

		for d in entries:
			row = self.append('items', {})
			row.update(d)
	
	def post_gl_entry(self):
		gl_entries   = []
        	if self.total_amount > 0:
			data = frappe.db.sql("""select round(sum(amount),2) as amount, cost_center from `tabCost Appropriation Item` where parent = '{}' group by cost_center""".format(self.name), as_dict = 1)
			for a in data:
				gl_entries.append(
					self.get_gl_dict({
							"account": self.account,
                        				"debit": round(flt(a.amount) ,2),
                   					"debit_in_account_currency": round(flt(a.amount) ,2),
                    					"voucher_no": self.name,
                        				"voucher_type": self.doctype,
                       					"cost_center": a.cost_center,
                       					"business_activity": 'Common'
                                               }))
                                
			gl_entries.append(
				self.get_gl_dict({
               				"account": self.account,
                        		"credit": self.total_amount,
                       			"credit_in_account_currency": self.total_amount,
                      			"voucher_no": self.name,
                       			"voucher_type": self.doctype,
                        		"cost_center": self.cost_center,
                      			"business_activity": 'Common'
                                               }))
			make_gl_entries(gl_entries, cancel=(self.docstatus == 2),update_outstanding="No", merge_entries=False)
		else:
                        frappe.throw("Total Amount is Zero")
        

