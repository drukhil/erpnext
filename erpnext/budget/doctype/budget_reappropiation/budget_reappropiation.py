# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import nowdate, flt
from erpnext.custom_utils import check_budget_available

class BudgetReappropiation(Document):
	
	def validate(self):
     	
		others = 'select distinct(account_type) from `tabAccount` where account_type is not null and account_type!="Fixed Asset"'
		other_asset = frappe.db.sql(others,as_dict=True)
		other_assets  = [item['account_type'] for item in other_asset]
		frappe.errprint(other_assets)
		
		
		for a in self.items:
			to_account = frappe.db.get_values('Account',a.to_account, 'account_type')
			from_account = frappe.db.get_values('Account', a.from_account, 'account_type')
			frappe.errprint(from_account)
			frappe.errprint(to_account)

				
			if not flt(a.amount) > 0:
				frappe.throw("Amount should be greater than 0 on row " + str(a.idx))
			if self.from_cost_center == self.to_cost_center and a.from_account == a.to_account:
				frappe.throw("From and To Account cannot be same")
			if from_account not in other_assets and to_account != from_account :
				frappe.throw("to_account type must be "+ str(from_account[0][0]))
			if from_account in other_assets and to_account != from_account:
				frappe.throw("to_account type must be "+ str(from_account[0][0]))
				
    
			# if from_account  not in   other_assets and to_account  in other_assets:
			# 	frappe.throw("to_account mus be " + str(from_account))
			# if to_account not in other_assets and from_account in other_assets:
			# 	frappe.throw("to_account must be " + str(from_account))
    
			# if from_account  in  other_assets and to_account in other_assets:
			# 	frappe.throw("to_account must be" + str(from_account))
					
			# if from_account == 'Fixed Asset' and to_account != 'Fixed Asset':
			# 	frappe.throw('to_Account should be '+ str(from_account))
			
			# for type in other_assets:
			# 	# frappe.errprint(type)
			# 	if from_account not in  type and to_account in type:
			# 		frappe.throw("to_account must be" + str(from_account))
					
			# if from_account== 'Fixed Asset' and to_account != 'Fixed Asset':
			# 	frappe.throw('to_Account should be '+ str(from_account))
    
			# check = """ 
			# 			SELECT  account_type, name from `tabAccount` 
            #         """.format( as_dict =True)
			# query = frappe.db.sql(check)
			
			# frappe.errprint(str(query))
		
		self.budget_check()
		self.update_users()

	def update_users(self):
		if not frappe.db.exists("Budget Reappropiation", self.name):
			self.created_by = frappe.session.user
			self.creator_name = frappe.db.get_value("Employee", {"user_id":self.created_by},"employee_name")
		
		if self.workflow_state=="Waiting For Verification" and not self.applied_by:
			self.applied_by = frappe.session.user 
			self.applied_name = frappe.db.get_value("Employee", {"user_id":self.applied_by},"employee_name")
		
		if self.workflow_state=="Waiting Approval":
			if not self.verified_by:
				self.verified_by = frappe.session.user
				self.verified_name = frappe.db.get_value("Employee", {"user_id":self.verified_by},"employee_name")
		
		if self.workflow_state=="Waiting for Submitting":
			if not self.approved_by:
				self.approved_by = frappe.session.user
				self.approver_name = frappe.db.get_value("Employee", {"user_id":self.approved_by},"employee_name")

		if self.workflow_state=="Submitted":
			if not self.submitted_by:
				self.submitted_by = frappe.session.user
				self.submitter_name = frappe.db.get_value("Employee", {"user_id":self.submitted_by},"employee_name")

		if self.workflow_state=="Rejected":
			self.applied_by = None
			self.verified_by = None
			self.approved_by = None	
			self.submitted_by = None

	def on_submit(self):
		for a in self.items:
			self.reappropriate(a.from_account, a.to_account, a.amount, False)

	def on_cancel(self):
		for a in self.items:
			self.reappropriate(a.from_account, a.to_account, a.amount, True)

	##
	# Check the budget amount in the from cost center and account
	##
	def budget_check(self):
		#Get cost center & target details
		'''
		budgets = frappe.db.sql("select from_account, sum(amount) as amount from `tabBudget Reappropiation Detail` where parent = %s group by from_account", self.name, as_dict=True)
		for a in budgets:
			check_budget_available(self.from_cost_center, a.from_account, str(self.fiscal_year) + "-01-01", a.amount)
		'''
		bgt_dtl=[]
		for b in self.get("items"):
			if b.from_account not in bgt_dtl:
				bgt_dtl.append(b.from_account)

		for c in bgt_dtl:
			reappropiation_amt = 0.00
			for d in self.get("items"):
				if c == d.from_account:
					reappropiation_amt += d.amount
			check_budget_available(self.from_cost_center, c, str(self.fiscal_year) + "-01-01", reappropiation_amt)


	##
	# Get budget details from CC and Account
	##
	def get_cc_acc_budget(self, cc, acc, fiscal_year):
		if frappe.db.get_value("Fiscal Year", fiscal_year, "closed"):
			frappe.throw("Fiscal Year " + fiscal_year + " has already been closed")
		else:
			return frappe.db.sql("""select ba.name, ba.parent, ba.budget_amount
					from `tabBudget` b, `tabBudget Account` ba
					where b.name=ba.parent and b.fiscal_year=%s and b.cost_center = %s and ba.account = %s and b.docstatus = 1
					""", (fiscal_year, cc, acc), as_dict=True)

	##
	# Method call from client to perform reappropriation
	##
	def reappropriate(self, from_acc=None, to_acc=None, amount=None, cancel=None):
		from_cc = self.from_cost_center
		to_cc = self.to_cost_center
		fiscal_year = self.fiscal_year
		

		to_account = self.get_cc_acc_budget(to_cc, to_acc, fiscal_year)
		from_account = self.get_cc_acc_budget(from_cc, from_acc, fiscal_year)

		if to_account and from_account:
			#Deduct in the From Account and Cost Center
			from_budget_account = frappe.get_doc("Budget Account", from_account[0].name)
			sent = flt(from_budget_account.budget_sent) + flt(amount)
			total = flt(from_budget_account.budget_amount) - flt(amount)
			if cancel:
				sent = flt(from_budget_account.budget_sent) - flt(amount)
				total = flt(from_budget_account.budget_amount) + flt(amount)
			from_budget_account.db_set("budget_sent", sent)
			from_budget_account.db_set("budget_amount", total)
			
			#Add in the To Account and Cost Center

			to_budget_account = frappe.get_doc("Budget Account", to_account[0].name)
			#frappe.msgprint("budget received {} and amount {}".format(to_budget_account.budget_amount, amount))
			received = flt(to_budget_account.budget_received) + flt(amount)
			total = flt(to_budget_account.budget_amount) + flt(amount)
			#frappe.throw("{} and {}".format(received, total))
			if cancel:
				received = flt(to_budget_account.budget_received) - flt(amount)
				total = flt(to_budget_account.budget_amount) - flt(amount)
			to_budget_account.db_set("budget_received", received)
			to_budget_account.db_set("budget_amount", total)
		
			#Add the reappropriation details for record
			if cancel:
				frappe.db.sql("delete from `tabReappropriation Details` where ref_doc=%s", self.name)
			else:
				app_details = frappe.new_doc("Reappropriation Details")
				app_details.flags.ignore_permissions = 1
				app_details.from_cost_center = from_cc
				app_details.to_cost_center = to_cc
				app_details.from_account = from_acc
				app_details.to_account = to_acc
				app_details.amount = amount
				app_details.appropriation_on = nowdate()
				app_details.ref_doc = self.name
				app_details.submit()
			
			return "DONE"

		elif not to_account:
			frappe.throw("Check your TO Cost Center and Account and try again")
			
		elif not from_account:
			frappe.throw("Check your From Cost Center and Account and try again")
		else:
			frappe.throw("Sorry, something happened. Please try again")

# select b.name,a.name,a.budget_received, a.budget_amount from `tabBudget Account` a, `tabBudget` b where a.parent = b.name and b.cost_center ='Construction of water supply and wastewater system for JSW School of law Pangbisa, Paro - CDCL' and a.account ='Building & Structure (10 years) - CDCL' and fiscal_year='2021' and b.docstatus=1;
