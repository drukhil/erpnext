# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate, money_in_words, getdate, date_diff, today, add_days, get_first_day, get_last_day
from erpnext.accounts.utils import get_account_currency, get_fiscal_year
import collections
from erpnext.hr.doctype.travel_authorization.travel_authorization import get_exchange_rate
from erpnext.custom_utils import check_budget_available, get_branch_cc
from erpnext.custom_workflow import verify_workflow_tc

class TravelClaim(Document):
	def get_status(self):
                if self.workflow_state =="Verified By Supervisor":
                        self.supervisor_approval = 1
			self.supervisor_approved_on = nowdate()
                elif self.workflow_state == "Approved":
                        self.hr_approval =1
			self.hr_approved_on = nowdate()
                elif self.workflow_state == "Rejected":
                        self.hr_approval =0
                        self.supervisor_approval =0
                        self.seupervisor_approved_on = None
			self.hr_approved_on = None
                else:
                        self.hr_approval =0
                        self.supervisor_approval =0
                        self.supervisor_approved_on = None
			self.hr_approved_on = None

	def validate(self):
		self.get_status()
		hr_role = frappe.db.get_value("UserRole", {"parent": frappe.session.user, "role": "HR User"}, "role")
		if frappe.session.user == self.supervisor and not self.supervisor_approval:
			self.db_set("supervisor_approved_on", '')
			self.supervisor_approved_on = ''
		#if self.supervisor_approved_on and not hr_role:
		#	frappe.throw("Cannot change records after approval by supervisor")
		#self.check_return_date()
		self.validate_dates()
		#self.check_approval()
		self.validate_dsa_ceiling()
		employee = frappe.db.get_value("Employee", self.employee, "user_id")
		self.update_travel_authorization()
		self.update_amounts()
		
		if frappe.session.user == self.owner or frappe.session.user == employee:
			self.db_set("claim_status", "")
			self.sendmail(frappe.db.get_value("Employee", {"user_id": self.supervisor}, "name"), "Travel Claim Submitted", str(self.employee_name) + " has requested you to verify and sign a " + str(frappe.get_desk_link("Travel Claim", self.name)))
		elif self.claim_status == "Rejected by Supervisor":
			self.sendmail(self.employee, "Travel Claim Rejected by Supervisor" + str(self.name), "Following remarks has been added by the supervisor: \n" + str(self.reason))
		elif self.claim_status == "Rejected by HR":
			self.sendmail(self.employee, "Travel Claim Rejected by HR" + str(self.name), "Following remarks has been added from HR: \n" + str(self.reason))

		if frappe.session.user == self.supervisor and self.supervisor_approval:
			self.db_set("supervisor_approved_on", nowdate())
		if self.get_db_value('workflow_state') == 'Waiting Approval' and self.workflow_state == "Verified By Supervisor":
                        if frappe.session.user == self.owner or frappe.session.user == employee:
                                self.supervisor_approval = 0
				self.db_set("workflow_state", 'Waiting Approval')
                                frappe.throw("You cannot approve your own claim.")
		
		if self.workflow_state not in ('Cancelled', 'Approved'):
			self.db_set("docstatus", 0)
		verify_workflow_tc(self)

	def on_update(self):
		self.check_double_dates()

	def on_submit(self):
		self.get_status()
		self.validate_submitter()
		#self.check_status()
		self.post_journal_entry()
		self.update_travel_authorization()
		#self.check_budget()
		if self.supervisor_approval and self.hr_approval:
			self.db_set("hr_approved_on", nowdate())
		
		self.sendmail(self.employee, "Travel Claim Approved" + str(self.name), "Your " + str(frappe.get_desk_link("Travel Claim", self.name)) + " has been approved and sent to Accounts Section. Kindly follow up.")

	def before_cancel(self):
		cl_status = frappe.db.get_value("Journal Entry", self.claim_journal, "docstatus")
		if cl_status and cl_status != 2:
			frappe.throw("You need to cancel the claim journal entry first!")
		
		ta = frappe.get_doc("Travel Authorization", self.ta)
		ta.db_set("travel_claim", "")

	def on_cancel(self):
		self.sendmail(self.employee, "Travel Claim Cancelled by HR" + str(self.name), "Your travel claim " + str(self.name) + " has been cancelled by the user")

        def get_monthly_count(self, items):
                counts = {}
                for i in items:
                        i.till_date     = i.date if not i.till_date else i.till_date
                        from_month      = str(i.date)[5:7]
                        to_month        = str(i.till_date)[5:7]
                        from_year       = str(i.date)[:4]
                        to_year         = str(i.till_date)[:4]
                        from_monthyear  = str(from_year)+str(from_month)
                        to_monthyear    = str(to_year)+str(to_month)

                        if int(to_monthyear) >= int(from_monthyear):
                                for y in range(int(from_year), int(to_year)+1):
                                        m_start = from_month if str(y) == str(from_year) else '01'
                                        m_end   = to_month if str(y) == str(to_year) else '12'
                                                        
                                        for m in range(int(m_start), int(m_end)+1):
                                                key          = str(y)+str(m).rjust(2,str('0'))
                                                m_start_date = key[:4]+'-'+key[4:]+'-01'
                                                m_start_date = i.date if str(y)+str(m).rjust(2,str('0')) == str(from_year)+str(from_month) else m_start_date
                                                m_end_date   = i.till_date if str(y)+str(m).rjust(2,str('0')) == str(to_year)+str(to_month) else get_last_day(m_start_date)
                                                if counts.has_key(key):
                                                        counts[key] += date_diff(m_end_date, m_start_date)+1
                                                else:
                                                        counts[key] = date_diff(m_end_date, m_start_date)+1
                        else:
                                frappe.throw(_("Row#{0} : Till Date cannot be before from date.").format(i.idx), title="Invalid Data")
                return collections.OrderedDict(sorted(counts.items()))
        
        def validate_dsa_ceiling(self):
		total_count = 0
                lastday_dsa_percent = frappe.db.get_single_value("HR Settings", "return_day_dsa")
                for i in self.get("items"):
                        i.remarks        = ""
                        i.days_allocated = 0
                        if i.last_day and not lastday_dsa_percent:
                                i.days_allocated = 0
                                i.half_dsa_days = 0
                                continue
			if not i.halt:
				i.quarantine = 0
                        from_date = i.date
                        to_date     = i.date if not i.till_date else i.till_date
                       	i.no_days = date_diff(to_date, from_date) + 1
                        '''if i.no_days and not i.quarantine:
                                total_count += i.no_days'''
			if not i.quarantine:
				total_count += i.no_days
                        counted = total_count - flt(i.no_days)
                        # if counted >= 30:
                        #       counted = 30 
                        # frappe.msgprint("Testing count {0}, amount {1}, counted {2}".format(total_count, i.amount, counted))
			if flt(total_count) <= 30:
                                i.days_allocated = i.no_days
                                i.half_dsa_days = 0

                        if flt(total_count) > 30:
                                i.half_dsa_days = flt(total_count) - 30
                                if flt(counted) > 30:
                                        i.half_dsa_days = flt(total_count) - flt(counted)
                                i.days_allocated = i.no_days - i.half_dsa_days

                        # if flt(total_count) > 30:
                        #         #lapse = flt(total_count) - flt(counted) - 30
                        #         lapse = flt(total_count) - 30
                        #         if flt(counted) > 30:
                        #                 lapse = flt(total_count) - flt(counted)
                        #         eligible = flt(i.no_days) - flt(lapse)
                        #         if flt(eligible) > 15:
                        #                 i.days_allocated = 15 - flt(counted)
                        #                 i.half_dsa_days = flt(eligible) - i.days_allocated
                        #         elif 0 < flt(eligible) <= 15:
                        #                 i.days_allocated = 0.0
                        #                 i.half_dsa_days =  flt(eligible)

                        #         else:
                        #                 i.days_allocated = 0.0
                        #                 i.half_dsa_days = 0.0

			if i.last_day and lastday_dsa_percent:
                                i.days_allocated = i.no_days
                                i.half_dsa_days = 0

			if i.quarantine:
                                i.days_allocated = 0
                                i.half_dsa_days = 0

        def update_amounts(self):
                #dsa_per_day         = flt(frappe.db.get_value("Employee Grade", self.grade, "dsa"))
                lastday_dsa_percent = frappe.db.get_single_value("HR Settings", "return_day_dsa")
                total_claim_amount  = 0
                exchange_rate       = 0
                company_currency    = "BTN"
                
                for i in self.get("items"):
                        exchange_rate      = 1 if i.currency == company_currency else get_exchange_rate(i.currency, company_currency)
                        #i.dsa             = flt(dsa_per_day)
			i.dsa              = flt(i.dsa) 
                        i.dsa_percent      = lastday_dsa_percent if i.last_day else i.dsa_percent
			if i.quarantine:
				i.dsa = 0.0
				i.dsa_percent = 0.0
        		i.amount           = (flt(i.days_allocated)*(flt(i.dsa)*flt(i.dsa_percent)/100)) + (flt(i.mileage_rate) * flt(i.distance)) + flt(i.half_dsa_days * i.dsa * 0.5)                
			i.actual_amount    = flt(i.amount) * flt(exchange_rate)
                        if not i.quarantine:
				total_claim_amount = flt(total_claim_amount) +  flt(i.actual_amount)

                self.total_claim_amount = flt(total_claim_amount)
                self.total_claim_amount = flt(self.claim_amount) + flt(self.extra_claim_amount)
                self.balance_amount     = flt(self.total_claim_amount) - flt(self.advance_amount)

#		self.balance_amount     = flt(self.total_claim_amount) + flt(self.extra_claim_amount) - flt(self.advance_amount)

                
                #if flt(self.balance_amount) < 0:
                #        frappe.throw(_("Balance Amount cannot be a negative value."), title="Invalid Amount")
                
	def check_return_date(self):
                pass
                """
		dsa_percent = frappe.db.get_single_value("HR Settings", "return_day_dsa")
                percent = flt(flt(dsa_percent) / 100.0)
		total_claim_amount = 0
		for a in self.items:
			if a.last_day:
				a.dsa_percent = dsa_percent
				a.amount = flt(a.amount) * percent
				a.actual_amount = flt(a.amount) * flt(a.exchange_rate)
			total_claim_amount = total_claim_amount + a.actual_amount
		self.total_claim_amount = total_claim_amount
		self.balance_amount = flt(self.total_claim_amount) + flt(self.extra_claim_amount) - flt(self.advance_amount)
		"""

	def check_double_dates(self):
		if self.items:
			start_date = self.items[0].date
			end_date = self.items[len(self.items) - 1].till_date
			if not end_date:
				end_date = self.items[len(self.items) - 1].date

			tas = frappe.db.sql("select a.name from `tabTravel Claim` a, `tabTravel Claim Item` b where a.employee = %s and a.docstatus = 1 and a.name = b.parent and (b.date between %s and %s or %s between b.date and b.till_date or %s between b.date and b.till_date) and a.name != %s", (str(self.employee), str(start_date), str(end_date), str(start_date), str(end_date), str(self.name)), as_dict=True)
			if tas:
				frappe.throw("The dates in your current Travel Claim has already been claimed in " + str(tas[0].name))
	
	def check_budget(self):
                cc = get_branch_cc(self.branch)
                if self.travel_type == 'Travel' and self.place_type == 'In-Country':
                        account = frappe.db.get_single_value ("HR Accounts Settings",  "travel_incountry_account")
                if self.travel_type == "Travel" and self.place_type == "Out-Country":
                        account = frappe.db.get_single_value ("HR Accounts Settings", "travel_outcountry_account")
                if self.travel_type == "Training" and self.place_type =="In-Country":
                        account = frappe.db.get_single_value ("HR Accounts Settings",  "training_incountry_account")
                if self.travel_type == "Training" and self.place_type == "Out-Country":
                        account = frappe.db.get_single_value ("HR Accounts Settings", "training_outcountry_account")
                if self.travel_type == "Meeting and Seminars" and self.place_type =="In-Country":
                        account = frappe.db.get_single_value ("HR Accounts Settings",  "meeting_and_seminars_in_account")
                if self.travel_type == "Meeting and Seminars" and self.place_type == "Out-Country":
                        account = frappe.db.get_single_value ("HR Accounts Settings", "meeting_and_seminars_out_account")

                check_budget_available(cc, account, self.posting_date, self.total_claim_amount, throw_error=True)

	##
	# make necessary journal entry
	##
	def post_journal_entry(self):
		cost_center = frappe.db.get_value("Employee", self.employee, "cost_center")
		if not cost_center:
			frappe.throw("Setup Cost Center for employee in Employee Information")
		expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		if not expense_bank_account:
			frappe.throw("Setup Default Expense Bank Account for your Branch")
		
		gl_account = ""	
		if self.travel_type == "Travel":
			if self.place_type == "In-Country":
				gl_account =  "travel_incountry_account"
			else:
				gl_account = "travel_outcountry_account"
		elif self.travel_type == "Training":
			if self.place_type == "In-Country":
				gl_account = "training_incountry_account"
			else:
				gl_account = "training_outcountry_account"
		else:
			if self.place_type == "In-Country":
				gl_account = "meeting_and_seminars_in_account"
			else:
				gl_account = "meeting_and_seminars_out_account"
		
		expense_account = frappe.db.get_single_value("HR Accounts Settings", gl_account)
		if not expense_account:
			frappe.throw("Setup Travel/Training Accounts in HR Accounts Settings")

		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1 
		je.title = "Travel Claim (" + self.employee + " - " + self.employee_name + ")"
		je.voucher_type = 'Bank Entry'
		je.naming_series = 'Bank Payment Voucher'
		je.remark = 'Claim payment for ' + self.employee + "(" + self.employee_name + ")" + " through TC " + self.name;
		je.user_remark = 'Claim payment for ' + self.employee + "(" + self.employee_name + ")" + " through TC " + self.name;
		je.posting_date = self.posting_date
		je.branch = self.branch

		total_amt = flt(self.claim_amount) + flt(self.extra_claim_amount)
	
		je.append("accounts", {
				"account": expense_account,
				"reference_type": "Travel Claim",
				"reference_name": self.name,
				"cost_center": cost_center,
				"debit_in_account_currency": flt(total_amt),
				"debit": flt(total_amt),
			})
		
		advance_amt = flt(self.advance_amount)
		bank_amt = flt(self.balance_amount)

		if (self.advance_amount) > 0:
			advance_account = frappe.db.get_single_value("HR Accounts Settings", "employee_advance_travel")
			if not advance_account:
				frappe.throw("Setup Advance to Employee (Travel) in HR Accounts Settings")
			if flt(self.balance_amount) <= 0:
				advance_amt = total_amt

			je.append("accounts", {
				"account": advance_account,
				"party_type": "Employee",
				"party": self.employee,
				"reference_type": "Travel Claim",
				"reference_name": self.name,
				"cost_center": cost_center,
				"credit_in_account_currency": advance_amt,
				"credit": advance_amt,
			})


		if flt(self.balance_amount) > 0:
			je.append("accounts", {
					"account": expense_bank_account,
					"reference_type": "Travel Claim",
					"reference_name": self.name,
					"cost_center": cost_center,
					"credit_in_account_currency": bank_amt,
					"credit": bank_amt,
				})

		je.insert()
	
		#Set a reference to the claim journal entry
		self.db_set("claim_journal", je.name)
	
	##
	# Update the claim reference on travel authorization
	##
	def update_travel_authorization(self):
		ta = frappe.get_doc("Travel Authorization", self.ta)
		if ta.travel_claim and ta.travel_claim <> self.name:
			frappe.throw("A travel claim <b>" + str(ta.travel_claim) + "</b> has already been created for the authorization")
		ta.db_set("travel_claim", self.name)

	##
	# Allow only approved authorizations to be submitted
	##
	def check_status(self):
		if self.supervisor_approval == 1 and self.hr_approval == 1:
			pass
		else:
			frappe.throw("Both Supervisor and HR has to approve to submit the travel claim")
	
	##
	# Allow only approved authorizations to be submitted
	##
	def check_approval(self):
		if self.supervisor_approval == 0 and self.hr_approval == 1:
			frappe.throw("Supervisor has to approve the claim before HR")
	
	##
	#Ensure the dates are consistent
	##
	def validate_dates(self):
		if self.ta_date > self.posting_date:
			frappe.throw("The Travel Claim Date cannot be earlier than Travel Authorization Date")

	##
	# Allow only the approver to submit the document
	##
	def validate_submitter(self):
		hr_role = frappe.db.get_value("UserRole", {"parent": frappe.session.user, "role": "HR User"}, "role")
		if not hr_role:
			frappe.throw("Only a HR User can submit this document")

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


