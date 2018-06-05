# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate, money_in_words, getdate
from erpnext.accounts.utils import get_account_currency, get_fiscal_year
from frappe.utils.data import add_days, date_diff
from frappe.model.mapper import get_mapped_doc
from datetime import timedelta

class TravelAuthorization(Document):

	def validate(self):
		if not self.branch:
			frappe.throw("Setup Branch in Emplpoyee Information and try again")

		self.validate_travel_dates()
                self.check_double_dates()
		self.assign_end_date()

	def on_update(self):
		self.set_dsa_rate()
		self.check_double_dates()
		if frappe.session.user != self.supervisor:
			if self.document_status == "Rejected":
				self.db_set("document_status", "")
			self.sendmail(frappe.db.get_value("Employee", {"user_id": self.supervisor}, "name"), "Travel Authorization Requested", str(self.employee_name) + " has requested you to verify and sign a travel authorization")
		elif self.document_status == "Rejected":
			self.sendmail(self.employee, "Travel Authorization Rejected" + str(self.name), "Following remarks has been added by the supervisor: \n" + str(self.reason))

	def on_submit(self):
		#self.check_double_dates()
		self.validate_submitter()
		self.validate_travel_dates()
		self.check_status()
		self.check_advance()
		self.create_attendance()
		self.sendmail(self.employee, "Travel Authorization Approved" + str(self.name), "Your travel authorization has been approved by the supervisor")

	def before_cancel(self):
		if self.advance_journal:
			jv_status = frappe.db.get_value("Journal Entry", self.advance_journal, "docstatus")
			if jv_status and jv_status != 2:
				frappe.throw("You need to cancel the advance journal entry first!")
	
	def on_cancel(self):
		if self.travel_claim:
			frappe.throw("Cancel the Travel Claim before cancelling Authorization")
		if not self.cancellation_reason:
			frappe.throw("Cancellation Reason is Mandatory when Cancelling Travel Authorization")
		self.cancel_attendance()	

	def create_attendance(self):
		d = getdate(self.items[0].date)
		if self.items[len(self.items) - 1].halt and self.items[len(self.items) - 1].till_date:
			e = getdate(self.items[len(self.items) - 1].till_date)
		else:
			e = getdate(self.items[len(self.items) - 1].date)
		days = date_diff(e, d) + 1
		for a in (d + timedelta(n) for n in range(days)):
			al = frappe.db.sql("select name from tabAttendance where docstatus = 1 and employee = %s and att_date = %s", (self.employee, a), as_dict=True)
			if al:
				doc = frappe.get_doc("Attendance", al[0].name)
				doc.cancel()
			#create attendance
			attendance = frappe.new_doc("Attendance")
			attendance.flags.ignore_permissions = 1
			attendance.employee = self.employee
			attendance.employee_name = self.employee_name 
			attendance.att_date = a
			attendance.status = "Tour"
			attendance.branch = self.branch
			attendance.company = frappe.db.get_value("Employee", self.employee, "company")
			attendance.reference_name = self.name
			attendance.submit()

	def cancel_attendance(self):
		frappe.db.sql("update tabAttendance set docstatus = 2 where reference_name = %s", (self.name))
	
	def assign_end_date(self):
		if self.items:
			self.end_date_auth = self.items[len(self.items) - 1].date 

	##
	# check advance and make necessary journal entry
	##
	def check_advance(self):
		if self.need_advance:
			if self.currency and flt(self.advance_amount_nu) > 0:
				cost_center = frappe.db.get_value("Employee", self.employee, "cost_center")
				advance_account = frappe.db.get_single_value("HR Accounts Settings", "employee_advance_travel")
				expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
				if not cost_center:
					frappe.throw("Setup Cost Center for employee in Employee Information")
				if not expense_bank_account:
					frappe.throw("Setup Default Expense Bank Account for your Branch")
				if not advance_account:
					frappe.throw("Setup Advance to Employee (Travel) in HR Accounts Settings")

				je = frappe.new_doc("Journal Entry")
				je.flags.ignore_permissions = 1 
				je.title = "TA Advance (" + self.employee_name + "  " + self.name + ")"
				je.voucher_type = 'Bank Entry'
				je.naming_series = 'Bank Payment Voucher'
				je.remark = 'Advance Payment against Travel Authorization: ' + self.name;
				je.posting_date = self.posting_date
				je.branch = self.branch
	
				je.append("accounts", {
					"account": advance_account,
					"party_type": "Employee",
					"party": self.employee,
					"reference_type": "Travel Authorization",
					"reference_name": self.name,
					"cost_center": cost_center,
					"debit_in_account_currency": flt(self.advance_amount_nu),
					"debit": flt(self.advance_amount_nu),
					"is_advance": "Yes"
				})

				je.append("accounts", {
					"account": expense_bank_account,
					"cost_center": cost_center,
					"credit_in_account_currency": flt(self.advance_amount_nu),
					"credit": flt(self.advance_amount_nu),
				})
				
				je.insert()
				
				#Set a reference to the advance journal entry
				self.db_set("advance_journal", je.name)
	
	##
	# Allow only approved authorizations to be submitted
	##
	def check_status(self):
		if self.document_status == "Rejected":
			frappe.throw("Rejected Documents cannot be submitted")
		if not self.document_status == "Approved":
			frappe.throw("Only Approved Documents can be submitted")
			
	##
	#Ensure the dates are consistent
	##
	def validate_travel_dates(self):
		date = None
		line = 0
		for item in self.get("items"):
			line = line + 1
			if item.halt == 1 and not item.till_date:
				frappe.throw("Till Date is Mandatory for Halt Days on line " + str(line))
			if date is None:
				if item.halt == 1:
					date = item.till_date
				else:
					date = item.date
			else:
				if item.date != add_days(date, 1):
					frappe.throw(str(item.date) + " on line " + str(line) + " might be wrongly typed. It should have been " + str(add_days(date, 1)) + ". Kindly check and submit again")
				else:
					if item.halt == 1:
						date = item.till_date
					else:
						date = item.date


	##
	# Allow only the approver to submit the document
	##
	def validate_submitter(self):
		if self.supervisor != frappe.session.user:
			frappe.throw("Only the selected supervisor can submit this document")


	##
	# Send notification to the supervisor / employee
	##
	def sendmail(self, to_email, subject, message):
		email = frappe.db.get_value("Employee", to_email, "user_id")
		if email:
			try:
				frappe.sendmail(recipients=email, sender=None, subject=subject, message=message)
			except:
				pass

	def set_dsa_rate(self):
		if self.grade:
			self.db_set("dsa_per_day", frappe.db.get_value("Employee Grade", self.grade, "dsa"))

	def check_double_dates(self):
		if self.items:
			start_date = self.items[0].date
			end_date = self.items[len(self.items) - 1].till_date
			if not end_date:
				end_date = self.items[len(self.items) - 1].date

			tas = frappe.db.sql("select a.name from `tabTravel Authorization` a, `tabTravel Authorization Item` b where a.employee = %s and a.name != %s and a.docstatus = 1 and a.name = b.parent and (b.date between %s and %s or %s between b.date and b.till_date or %s between b.date and b.till_date)", (str(self.employee), str(self.name), str(start_date), str(end_date), str(start_date), str(end_date)), as_dict=True)
			if tas:
				frappe.throw("The dates in your current Travel Authorization has already been claimed in " + str(tas[0].name))
			las = frappe.db.sql("select name from `tabLeave Application` where docstatus = 1 and employee = %s and (from_date between %s and %s or to_date between %s and %s)", (str(self.employee), str(start_date), str(end_date), str(start_date), str(end_date)), as_dict=True)					
			if las:
				frappe.throw("The dates in your current travel authorization has been used in leave application " + str(las[0].name))

@frappe.whitelist()
def make_travel_claim(source_name, target_doc=None): 
	def update_date(obj, target, source_parent):
		target.posting_date = nowdate()
	
	def transfer_currency(obj, target, source_parent):
		if obj.halt:
			target.from_place = ""
			target.to_place = ""
		else:
			target.no_days = 1
			target.halt_at = ""
		target.currency = source_parent.currency
		target.dsa = source_parent.dsa_per_day
		target.actual_amount = target.dsa
		if target.halt:
			target.actual_amount = flt(target.dsa) * flt(target.no_days)
		target.amount = target.actual_amount

	def adjust_last_date(source, target):
		target.items[len(target.items) - 1].dsa_percent = 0 
		target.items[len(target.items) - 1].actual_amount = 0 #target.items[len(target.items) - 1].actual_amount / 2
		target.items[len(target.items) - 1].amount = 0 #target.items[len(target.items) - 1].amount / 2
		target.items[len(target.items) - 1].last_day = 1 #target.items[len(target.items) - 1].amount / 2

	doc = get_mapped_doc("Travel Authorization", source_name, {
			"Travel Authorization": {
				"doctype": "Travel Claim",
				"field_map": {
					"name": "ta",
					"posting_date": "ta_date",
					"advance_amount_nu": "advance_amount"
				},
				"postprocess": update_date,
				"validation": {"docstatus": ["=", 1]}
			},
			"Travel Authorization Item": {
				"doctype": "Travel Claim Item",
				"postprocess": transfer_currency
			},
		}, target_doc, adjust_last_date)
	return doc

@frappe.whitelist()
def get_exchange_rate(from_currency, to_currency):
	ex_rate = frappe.db.get_value("Currency Exchange", {"from_currency": from_currency, "to_currency": to_currency}, "exchange_rate")
	if not ex_rate:
		frappe.throw("No Exchange Rate defined in Currency Exchange! Kindly contact your accounts section")
	else:
		return ex_rate


