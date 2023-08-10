# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate, time_diff_in_hours
from erpnext.custom_utils import check_budget_available, get_branch_cc
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from datetime import datetime, timedelta
class OvertimeApplication(Document):
    def validate(self):
        self.validate_dates()
        self.validate_submitter()
        self.set_approver()
        self.calculate_item_values()
        self.calculate_totals()
        self.final_amount()

    #added by cety to check for holiday and double the rate by 50% on 31/07/2022
    def calculate_item_values(self):
        no_of_holiday = 0
        for item in self.items:
            if item.is_holiday:
                item.is_late_night_ot = 0
            item.rate = self.rate
            if item.is_late_night_ot or item.is_holiday:
                item.number_of_hours    = flt(time_diff_in_hours(item.to_time, item.from_time),2)
                item.amount             = flt(item.number_of_hours) * flt(flt(item.rate) * 1.5)
            else:
                item.number_of_hours    = flt(time_diff_in_hours(item.to_time, item.from_time),2)
                item.amount             = flt(item.number_of_hours) * flt(item.rate)
                
    def final_amount(self):
        final_amount = 0
        for amt in self.items:
            final_amount += amt.amount
        self.actual_amount = flt(final_amount)   
    #end
           
    def on_submit(self):
        #self.check_budget()
        self.post_journal_entry()

    def on_cancel(self):
        self.check_journal()
    
    def check_budget(self):
        cc = get_branch_cc(self.branch)
        account = frappe.db.get_single_value ("HR Accounts Settings", "overtime_account")
        check_budget_available(cc, account, self.posting_date, self.actual_amount, throw_error=True)
  
    def set_approver(self):
        if self.workflow_state ==  "Verified By Supervisor":
            if self.approver:
                #employee = frappe.get_value("Employee", {"user_id": self.approver}, "name")
                employee = frappe.db.get_value("Employee", {"user_id": self.approver, 'status': 'Active'}, ["name"])
                approver = frappe.get_value("Employee", employee, "reports_to")
                approver_id, approver_name = frappe.get_value("Employee", approver, ["user_id","employee_name"])
                self.approver = approver_id
                self.approver_name = approver_name
        elif self.workflow_state in ("Draft","Waiting Approval","Rejected"):	
            if self.employee:
                approver = frappe.get_value("Employee", self.employee, "reports_to")
                approver_id, approver_name = frappe.get_value("Employee", approver, ["user_id","employee_name"])
                self.approver = approver_id
                self.approver_name = approver_name
            

    def calculate_totals(self):
        total_hours  = 0
        for i in self.items:
            total_hours += flt(i.number_of_hours)

        self.total_hours  = flt(total_hours)
        self.total_amount = flt(total_hours)*flt(self.rate)

        if flt(self.total_hours) <= 0:
            frappe.throw(_("Total number of hours cannot be nil."),title="Incomplete information")
    ##
    # Dont allow duplicate dates
    ##
    def validate_dates(self):
        self.posting_date = nowdate()
                  
        for a in self.items:
            if not a.date:
                frappe.throw(_("Row#{0} : Date cannot be blank").format(a.idx),title="Invalid Date")

            if str(a.date) > str(nowdate()):
                frappe.throw(_("Row#{0} : Future dates are not accepted").format(a.idx), title="Invalid Date")

            #Validate if time interval falls between another time interval for the same date   
            for b in self.items:
                if a.date == b.date and a.idx != b.idx:
                    time_format = "%H:%M:%S"
                    start1 = datetime.strptime(a.from_time, time_format)
                    end1 = datetime.strptime(a.to_time, time_format)
                    start2 = datetime.strptime(b.from_time, time_format)
                    end2 = datetime.strptime(b.to_time, time_format)
                    #frappe.throw("{}, {}, {} and {},{},{}".format(start2,start1,end2,start2,end1,end2))
                    if start2 <= start1 <= end2 or start2 <= end1 <= end2:
                        frappe.throw("Duplicate Dates in row " + str(a.idx) + " and " + str(b.idx))
    ##
    # Allow only the approver to submit the document
    ##
    def validate_submitter(self):
        if self.approver != frappe.session.user and self.workflow_state not in ("Draft","Waiting Approval"):
            frappe.throw("Only <b>{}, ({})</b> can Verify or Approve this document".format(self.approver_name, self.approver))

    ##
    # Post journal entry
    ##
    def post_journal_entry(self):	
        cost_center = frappe.db.get_value("Employee", self.employee, "cost_center")
        ot_account = frappe.db.get_single_value("HR Accounts Settings", "overtime_account")
        expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
        if not cost_center:
            frappe.throw("Setup Cost Center for employee in Employee Information")
        if not expense_bank_account:
            frappe.throw("Setup Default Expense Bank Account for your Branch")
        if not ot_account:
            frappe.throw("Setup Default Overtime Account in HR Account Setting")

        je = frappe.new_doc("Journal Entry")
        je.flags.ignore_permissions = 1 
        je.title = "Overtime payment for " + self.employee_name + "(" + self.employee + ")"
        je.voucher_type = 'Bank Entry'
        je.naming_series = 'Bank Payment Voucher'
        je.remark = 'Payment Paid against : ' + self.name + " for " + self.employee
        je.user_remark = 'Payment Paid against : ' + self.name + " for " + self.employee
        je.posting_date = self.posting_date
        total_amount = self.actual_amount
        je.branch = self.branch

        je.append("accounts", {
                "account": expense_bank_account,
                "cost_center": cost_center,
                "credit_in_account_currency": flt(total_amount),
                "credit": flt(total_amount),
            })
        
        je.append("accounts", {
                "account": ot_account,
                "cost_center": cost_center,
                "debit_in_account_currency": flt(total_amount),
                "debit": flt(total_amount),
                "reference_type": self.doctype,
                "reference_name": self.name
            })

        je.insert()

        self.db_set("payment_jv", je.name)
        frappe.msgprint("Bill processed to accounts through journal voucher " + je.name)
    ##
    # Check journal entry status (allow to cancel only if the JV is cancelled too)
    ##
    def check_journal(self):
        cl_status = frappe.db.get_value("Journal Entry", self.payment_jv, "docstatus")
        if cl_status and cl_status != 2:
            frappe.throw("You need to cancel the journal entry " + str(self.payment_jv) + " first!")
        
        self.db_set("payment_jv", None)

#added by cety to check for holiday and double the rate by 50% on 31/07/2022
@frappe.whitelist()
def get_holidays(employee, date):
    holiday_list = get_holiday_list_for_employee(employee)
    return frappe.db.exists('Holiday',{'parent':holiday_list,'holiday_date':date})