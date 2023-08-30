# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
	comma_or, get_fullname, nowdate, money_in_words, today
from frappe import msgprint, _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from erpnext.custom_autoname import get_auto_name
from datetime import *
from erpnext.hr.doctype.salary_structure.salary_structure import get_salary_tax
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
#from dateutil.relativedelta import *
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on

class OverlapError(frappe.ValidationError): pass
class InsufficientError(frappe.ValidationError): pass

class LeaveEncashment(Document):
        def autoname(self):
                today = datetime.today()
                #self.name = make_autoname(get_auto_name(self) + "/.#####")
                monthyear = str(today.year)
                if len(str(today.month)) < 2:
                        monthyear += "0"+str(today.month)

                self.name = make_autoname(self.employee+"/LE/"+monthyear+"/.#####")
        
        def validate(self):
		#self.branch = frappe.db.get_value("Employee", self.employee, "branch")         #Commented by SHIV on 2018/10/15
                self.validate_leave_application()
                self.get_leave_balance()                                                        #Added by SHIV on 2018/10/15
                self.validate_balances()                                                        #Commented by SHIV on 2018/10/12

		#Employees on Deputation are not eligible for Leave Encashment
		if self.employment_type == "Deputation" and self.workflow_state == "Waiting Approval":
			frappe.throw("<b> You are not allowed to apply Leave Encashment </b>")
                
        def on_submit(self):
		self.adjust_leave()
		if self.employment_type != 'Deputation':
			self.post_accounts_entry()

		if self.employment_type == 'Deputation':
			frappe.msgprint("Your Leave Encashment Will Be Processed from Parent Organization, Kindly Contact HR Manager for more info")
	def before_cancel(self):
		self.check_gl_entry()

	def on_cancel(self):
                self.adjust_leave(True)	

	def get_leave_credits(self):
                pass

	def adjust_leave(self, cancel=False):
                leave_allocation = frappe.db.sql("""
                        select name, from_date, to_date, total_leaves_allocated
                        from `tabLeave Allocation`
                        where employee=%s and leave_type=%s and docstatus=1 
                        order by to_date desc limit 1
                """, (self.employee, self.leave_type), as_dict=1)
                if leave_allocation:
                        doc = frappe.get_doc("Leave Allocation", leave_allocation[0].name)
                        if cancel:
                                new_total = (flt(doc.total_leaves_allocated) + flt(self.encashed_days))
                                days = flt(self.encashed_days)
                                self.db_set("leave_adjusted", 0)
                        else:
                                new_total = (flt(doc.total_leaves_allocated) - flt(self.encashed_days))
                                days = 0 - flt(self.encashed_days)
                                self.db_set("leave_adjusted", 1)
                        doc.db_set("total_leaves_allocated", new_total)
                        doc.db_set("leave_encashment", self.name)
                        doc.db_set("encashed_days", days)
	
	def check_gl_entry(self):
		if self.encash_journal:
			docstat = frappe.db.get_value("Journal Entry", self.encash_journal, "docstatus")
			if docstat != 2:
				frappe.throw("You cannot cancel this document without cancelling the journal entry")


        def validate_leave_application(self):
                from_date, to_date = self.get_current_year_dates()
                ref_docs = ''
                
                encashed_list = frappe.db.sql("""
                        select name from `tabLeave Encashment`
                        where employee = %s and leave_type = %s and docstatus = 1
                        and application_date between %s and %s
                        """,(self.employee, self.leave_type, from_date, to_date), as_dict=1)

                for row in encashed_list:
                        ref_docs += '<br /><a style="color: green" href="#Form/Leave Encashment/{0}">{0}</a>'.format(row.name)
               
                if ref_docs:
                        ref_docs = "<br /><br />Reference: {0}".format(ref_docs)
                        #frappe.throw(_("Employee has already encashed for the current year.{0}").format(ref_docs), OverlapError)
                        frappe.throw(_("Employee has already encashed for the current year.{0}").format(ref_docs))

        def validate_balances(self):
                msg = ''
                #le = get_le_settings()                                                                         # Line commented by SHIV on 2018/10/15
                le = frappe.get_doc("Employee Group",frappe.db.get_value("Employee",self.employee,"employee_group")) # Line added by SHIV on 2018/10/15
                if flt(self.balance_before) < flt(le.encashment_min):
                        msg = "Minimum leave balance {0} required to encash.".format(le.encashment_min)

                if flt(self.balance_after) < 0:
                        msg = "Insufficient leave balance"

                if msg:
                      frappe.throw(_("{0}").format(msg), InsufficientError)

        def get_current_year_dates(self):
                from_date = date(date.today().year,1,1).strftime('%Y-%m-%d')
                to_date = date(date.today().year,12,31).strftime('%Y-%m-%d')
                return from_date, to_date

        def get_salary_structure(self):
                salary_struc_list = frappe.db.sql("""
                        select name from `tabSalary Structure`
                        where employee = %s
                        and is_active = 'Yes'
                        and now() between ifnull(from_date,'0000-00-00') and ifnull(to_date,'2050-12-31')
                        order by ifnull(from_date,'0000-00-00') desc limit 1
                """,(self.employee))

                if salary_struc_list:
                        return salary_struc_list[0][0]
                else:
                        frappe.throw(_("No Active Salary Structure found for the employee."))
                        
                return salary_struc_list[0][0]

        # Following method created by SHIV on 2018/10/12
        def update_employee_details(self):
                self.encashed_days      = 0
                self.balance_before     = 0
                self.balance_after      = 0

                if self.employee:                
                        doc = frappe.get_doc("Employee", self.employee)
                        self.employee_name      = doc.employee_name
                        self.employment_type    = doc.employment_type
                        self.employee_group     = doc.employee_group
                        self.employee_subgroup  = doc.employee_subgroup
                        self.branch             = doc.branch
                        self.cost_center        = doc.cost_center
                        self.department         = doc.department
                        self.division           = doc.division
                        self.section            = doc.section
                                
        # Following method created by SHIV on 2018/10/12
        def get_leave_balance(self):
                self.update_employee_details()
                if self.employee:
                        group_doc = frappe.get_doc("Employee Group", self.employee_group)
                        self.encashed_days  = group_doc.encashment_days
                        self.balance_before = get_leave_balance_on(self.employee, self.leave_type, today())
                        self.balance_after  = flt(self.balance_before) - flt(self.encashed_days)
        
        def post_accounts_entry(self):
                employee = frappe.get_doc("Employee", self.employee)

		cost_center = employee.cost_center
		if not cost_center:
			frappe.throw("Setup Cost Center for employee in Employee Information")

		expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		if not expense_bank_account:
			frappe.throw("Setup Default Expense Bank Account for your Branch")

		expense_account = frappe.db.get_single_value("HR Accounts Settings", "leave_encashment_account")
		if not expense_account:
			frappe.throw("Setup Leave Encashment Accounts in HR Accounts Settings")

		tax_account = frappe.db.get_single_value("HR Accounts Settings", "salary_tax_account")
		if not tax_account:
			frappe.throw("Setup Leave Tax Accounts in HR Accounts Settings")

                sal_struc_name = self.get_salary_structure()
                if sal_struc_name:
                        sal_struc= frappe.get_doc("Salary Structure",sal_struc_name)
                        for d in sal_struc.earnings:
                                if d.salary_component == 'Basic Pay':
                                        basic_pay = flt(d.amount)
                else:
                        frappe.throw(_("No Active salary structure found."))
                        
                if basic_pay:
                        salary_tax = get_salary_tax(basic_pay)

                salary_tax = flt(salary_tax) if salary_tax else 0.00                
                
                je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1 
		je.title = 'Leave Encashment for '+str(employee.employee_name) + ' - ' + str(employee.employee)
                je.voucher_type = 'Bank Entry'
                je.naming_series = 'Bank Payment Voucher'
                je.company = employee.company
		je.branch = self.branch
                je.remark = 'Payment against Leave Encashment: ' + self.name + ' for ' + employee.employee;
                je.user_remark = 'Payment against Leave Encashment: ' + self.name + ' for ' + employee.employee;
                je.posting_date = self.application_date
                je.total_amount_in_words =  money_in_words(flt(basic_pay)-flt(salary_tax))

                je.append("accounts", {
                        "account": expense_account,
                        "debit_in_account_currency": flt(basic_pay),
                        "debit": flt(basic_pay),
                        "reference_type": "Leave Encashment",
                        "reference_name": self.name,
                        "cost_center": cost_center,
                })

                je.append("accounts", {
                        "account": tax_account,
                        "credit_in_account_currency": flt(salary_tax),
                        "credit": flt(salary_tax),
                        "reference_type": "Leave Encashment",
                        "reference_name": self.name,
                        "cost_center": cost_center,
                })

                je.append("accounts", {
                        "account": expense_bank_account,
                        "credit_in_account_currency": (flt(basic_pay)-flt(salary_tax)),
                        "credit": (flt(basic_pay)-flt(salary_tax)),
                        "reference_type": "Leave Encashment",
                        "reference_name": self.name,
                        "cost_center": cost_center
                })
                je.insert()

		self.db_set("encash_journal", je.name)
		self.db_set("encashment_amount", flt(basic_pay))
		self.db_set("tax_amount", flt(salary_tax))

# Following code commented by SHIV on 2018/10/12
'''
@frappe.whitelist()
def get_employee_cost_center(emp):
        cost_center = frappe.db.get_value("Employee", emp, "cost_center")
	if not cost_center:
		frappe.throw("No Cost Center has been assigned to the Employee")
	return cost_center

@frappe.whitelist()                        
def get_le_settings(*arg, **kwargs):
        le = frappe.db.get_value("Leave Encashment Settings", filters = None, \
                        fieldname = ["encashment_days","encashment_min","encashment_lapse"], as_dict = True)
        
        return le

'''
