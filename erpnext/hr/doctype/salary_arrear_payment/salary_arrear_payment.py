# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, flt, nowdate
from erpnext.hr.hr_custom_functions import get_month_details, get_payroll_settings, get_salary_tax
from frappe.model.document import Document
import math

class SalaryArrearPayment(Document):
	def validate(self):
		self.total_net_arrear_payable = 0
		for a in self.items:
			self.total_net_arrear_payable += a.net_payable_arrear

	# Populate Arrear details 
	def get_arrear_employees(self):
		if not self.from_month:
			frappe.throw("Please set Effective From Month")
		if not self.fiscal_year:
			frappe.throw(_("<b>Fiscal Year</b> is Mandatory"))

		month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(self.from_month) + 1
		month = str(month) if cint(month) > 9 else str("0" + str(month))

		query = """
			SELECT
				e.name AS employee, e.employee_name, e.branch, e.bank_name, e.bank_ac_no,
				ssi.salary_structure AS salary_struct, ssi.total_days_in_month AS total_days, ssi.working_days,
				eg.employee_pf AS pf_per, eg.employer_pf AS employer_pf_per, eg.health_contribution AS health_con_per,
				sd_pf.amount AS previous_employer_pf, sd_pf.amount AS previous_pf, sd_basic.amount AS prev_basic_pay,
				COALESCE(sd_officiating.amount, 0) AS prev_officiating,
				COALESCE(sd_contract.amount, 0) AS prev_contract,
				COALESCE(sd_corporate.amount, 0) AS prev_corporate,
				COALESCE(sd_project.amount, 0) AS previous_project_allowance,
				COALESCE(sd_pf.amount, 0) AS previous_pf,
				COALESCE(sd_salary_tax.amount, 0) AS previous_salary_tax,
				COALESCE(sd_hc.amount, 0) AS prev_hc
			FROM tabEmployee e
			INNER JOIN `tabSalary Slip` ss ON ss.employee = e.name
			LEFT JOIN `tabSalary Slip Item` ssi ON ssi.parent = ss.name
			LEFT JOIN `tabEmployee Group` eg ON eg.name = e.employee_group
			LEFT JOIN `tabSalary Detail` sd_pf ON sd_pf.parent = ss.name AND sd_pf.salary_component = 'PF'
			LEFT JOIN `tabSalary Detail` sd_basic ON sd_basic.parent = ss.name AND sd_basic.salary_component = 'Basic Pay'
			LEFT JOIN `tabSalary Detail` sd_officiating ON sd_officiating.parent = ss.name AND sd_officiating.salary_component = 'Officiating Allowance'
			LEFT JOIN `tabSalary Detail` sd_contract ON sd_contract.parent = ss.name AND sd_contract.salary_component = 'Contract Allowance'
			LEFT JOIN `tabSalary Detail` sd_corporate ON sd_corporate.parent = ss.name AND sd_corporate.salary_component = 'Corporate Allowance'
			LEFT JOIN `tabSalary Detail` sd_project ON sd_project.parent = ss.name AND sd_project.salary_component = 'Project Allowance'
			LEFT JOIN `tabSalary Detail` sd_salary_tax ON sd_salary_tax.parent = ss.name AND sd_salary_tax.salary_component = 'Salary Tax'
			LEFT JOIN `tabSalary Detail` sd_hc ON sd_hc.parent = ss.name AND sd_hc.salary_component = 'Health Contribution'
			WHERE NOT EXISTS (
				SELECT 1
				FROM `tabSalary Arrear Payment Item` sapi
				INNER JOIN `tabSalary Arrear Payment` sap ON sapi.parent = sap.name
				WHERE sap.fiscal_year = %s
				AND sap.name != %s
				AND sapi.employee = e.employee
				AND sap.docstatus != 2
			)
			AND ss.month = %s
			AND ss.fiscal_year = %s
			AND ss.docstatus = 1
			ORDER BY e.name
		"""

		params = (self.fiscal_year, self.name, month, self.fiscal_year)
		entries = frappe.db.sql(query, params, as_dict=True)
		self.set('items', [])
		for d in entries:
			emp_doc = frappe.get_doc("Employee", d.employee)
			sal_struct = frappe.get_doc("Salary Structure", d.salary_struct)

			min_basic_pay, fixed_allowance = frappe.db.get_value("Employee Grade", emp_doc.employee_subgroup, ["minimum", "fixed_allowance"])
			d.new_minimum_basic_pay = min_basic_pay or 0
			d.fixed_allowance = flt(fixed_allowance * (flt(d.working_days) / flt(d.total_days)), 0)
			
			row = self.append('items', {})
			d.contract_allowance = d.corporate_allowance = d.officiating_allowance = d.project_allowance = 0
			
			# if emp_doc.employment_type in ("Contract", "Chief Executive Officer"):
			# 	basic_pay_increment = 0.02 if emp_doc.employee_subgroup in ("M7", "M7 ( Contract )", "O7", "F7", "M6", "M6 (Contract)", "M5", "M4", "M4 Contract", "E3", "E4", "E3 ( Contract )", "E4 ( Contract )", "E2", "CEO") else 0.05
			# else:
			basic_pay_increment = 0.02 if emp_doc.employee_subgroup in ("M7", "M7 ( Contract )", "O7", "F7", "M6", "M6 (Contract)", "M5", "M4", "M4 Contract", "E3", "E4", "E3 ( Contract )", "E4 ( Contract )", "E2", "CEO") else 0.05
			
			d.basic_pay = flt(d.prev_basic_pay + d.prev_basic_pay * basic_pay_increment)
			d.basic_pay = math.ceil(d.basic_pay)

			last_digit = int(str(d.basic_pay)[-1])
			if 0 < last_digit <= 5:
				d.basic_pay = flt(str(d.basic_pay)[:-1] + "5")
			elif 5 < last_digit <= 9:
				d.basic_pay += 10 - last_digit
			
			if emp_doc.employment_type in ("Contract", "Chief Executive Officer"):
				if sal_struct.contract_allowance_method == "Percent":
					d.contract_allowance = flt(d.basic_pay * (sal_struct.contract_allowance * 0.01), 0)
				elif sal_struct.contract_allowance_method == "Lumpsum":
					d.contract_allowance = flt(sal_struct.contract_allowance)
			else:
				if sal_struct.ca_method == "Percent":
					d.corporate_allowance = flt(d.basic_pay * (sal_struct.ca * 0.01), 0)
				elif sal_struct.ca_method == "Lumpsum":
					d.corporate_allowance = flt(sal_struct.ca)
			
			if d.prev_officiating > 0:
				if sal_struct.officiating_allowance_method == "Percent":
					d.officiating_allowance = flt(d.basic_pay*(sal_struct.officiating_allowance*0.01),0)
				elif sal_struct.officiating_allowance_method == "Lumpsum":
					d.officiating_allowance = flt(sal_struct.officiating_allowance)
			if d.previous_project_allowance > 0:
				if sal_struct.project_allowance_method == "Percent":
					d.project_allowance = flt(d.basic_pay*(sal_struct.project_allowance*0.01),0)
				elif sal_struct.project_allowance_method == "Lumpsum":
					d.project_allowance = flt(sal_struct.project_allowance)

			d.pf = flt(d.basic_pay * (d.pf_per * 0.01),0)
			d.employer_pf = flt(d.basic_pay * (d.employer_pf_per * 0.01),0)
			d.arrear_basic_pay = d.basic_pay - d.prev_basic_pay
			d.arrear_corporate_allowance = d.corporate_allowance - d.prev_corporate
			d.arrear_contract_allowance = d.contract_allowance - d.prev_contract
			d.arrear_project_allowance = d.project_allowance - d.previous_project_allowance
			d.arrear_officiating_allowance = d.officiating_allowance - d.prev_officiating
			d.salary_tax = get_salary_tax((d.basic_pay+d.corporate_allowance+d.contract_allowance+d.fixed_allowance + d.project_allowance-d.pf))
			frappe.msgprint(str(d.employee))
			frappe.msgprint(str(d.salary_tax))
			d.health_contribution = flt((d.basic_pay+d.corporate_allowance+d.contract_allowance+d.fixed_allowance+ d.project_allowance) * (d.health_con_per * 0.01),0)
			# frappe.msgprint(str(d.health_contribution))
			d.arrear_pf = flt(d.pf-d.previous_pf)
			frappe.msgprint(str(d.arrear_pf))
			d.arrear_employer_pf = flt(d.employer_pf-d.previous_employer_pf) if d.employer_pf and d.previous_employer_pf else 0
			# frappe.msgprint(str(d.arrear_employer_pf))
			d.new_gross_pay = flt(d.arrear_basic_pay + d.arrear_corporate_allowance + d.arrear_contract_allowance + d.arrear_officiating_allowance + d.fixed_allowance + d.arrear_project_allowance)
			d.arrear_salary_tax = get_salary_tax(d.new_gross_pay-d.arrear_pf)
			d.arrear_hc = flt(d.new_gross_pay*(d.health_con_per*0.01),0)
			# frappe.msgprint(str(d.arrear_hc))
			d.total_deduction = flt(d.arrear_hc+d.arrear_pf+d.arrear_salary_tax)
			d.net_payable_arrear = d.new_gross_pay - d.total_deduction

			row.update(d)
		self.total_net_arrear_payable = 0
		for a in self.items:
			self.total_net_arrear_payable += a.net_payable_arrear

	def make_accounting_entry(self):
		if frappe.db.exists("Journal Entry Account", {"reference_type": self.doctype, "reference_name": self.name}):
			frappe.msgprint(_("Accounting Entries already posted"))
			return
		month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(self.from_month) + 1
		month = str(month) if cint(month) > 9 else str("0" + str(month))

		# Default Accounts
		default_bank_account = frappe.db.get_value("Branch", self.processing_branch,"expense_bank_account")
		default_payable_account = frappe.db.get_single_value("HR Accounts Settings", "salary_payable_account")
		company_cc              = frappe.db.get_value("Company", self.company,"company_cost_center")
		default_gpf_account     = frappe.db.get_single_value("HR Accounts Settings", "employee_contribution_pf")

		if not default_bank_account:
			frappe.throw("Default Bank Account is mandatory")
		elif not default_payable_account:
			frappe.throw("Default Payable Account is mandatory")
		elif not company_cc:
			frappe.throw("Default Company Cost Center is missing")
		elif not default_gpf_account:
			frappe.throw("Default GPF account is mandatory")

		# Salary Details
		cc = {}
		health_contribution = employee_pf = salary_tax = net_payable = 0
		for det in self.items:
			health_contribution += det.arrear_hc
			employee_pf += det.arrear_pf
			salary_tax += det.arrear_salary_tax
			net_payable += det.net_payable_arrear
			cost_center = frappe.db.get_value("Cost Center", {"branch": det.branch}, "name")
			if cost_center not in cc:
				cc.update({
        			cost_center: {
               			"basic_pay": det.arrear_basic_pay,
                  		"corporate_allowance": det.arrear_corporate_allowance,
						"contract_allowance": det.arrear_contract_allowance,
						"officiating_allowance": det.arrear_officiating_allowance,
						"project_allowance": det.arrear_project_allowance,
						"fixed_allowance": det.fixed_allowance,
						"employer_pf": det.arrear_employer_pf
                    }
           		})
			else:
				cc[cost_center]['basic_pay'] += det.arrear_basic_pay
				cc[cost_center]['corporate_allowance'] += det.arrear_corporate_allowance
				cc[cost_center]['contract_allowance'] += det.arrear_contract_allowance
				cc[cost_center]['officiating_allowance'] += det.arrear_officiating_allowance
				cc[cost_center]['project_allowance'] += det.arrear_project_allowance
				cc[cost_center]['fixed_allowance'] += det.fixed_allowance
				cc[cost_center]['employer_pf'] += det.arrear_employer_pf

		#Payables Journal Entry -----------------------------------------------
		payables_je = frappe.new_doc("Journal Entry")
		payables_je.voucher_type= "Journal Entry"
		payables_je.naming_series = "Journal Voucher"
		payables_je.title = "Salary Arrear "+str(self.fiscal_year)+str(month)+" - To Payables"
		payables_je.remark =  "Salary Arrear "+str(self.fiscal_year)+str(month)+" - To Payables"
		payables_je.posting_date = nowdate()               
		payables_je.company = self.company
		payables_je.branch = self.processing_branch
		payables_je.reference_name =  self.name
		total_basic_pay = total_allowance = 0
		for rec in cc:
			payables_je.append("accounts", {
					"account": frappe.db.get_value("Salary Component", "Basic Pay", "gl_head"),
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": rec,
					"debit_in_account_currency": flt(cc[rec]['basic_pay'],2),
					"debit": flt(cc[rec]['basic_pay'],2),
				})
			total_basic_pay += flt(cc[rec]['basic_pay'],2)
			#Corporate Allowance
			payables_je.append("accounts", {
					"account": frappe.db.get_value("Salary Component", "Corporate Allowance", "gl_head"),
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": rec,
					"debit_in_account_currency": flt(cc[rec]['corporate_allowance'],2),
					"debit": flt(cc[rec]['corporate_allowance'],2),
				})
			#Contract Allowance
			payables_je.append("accounts", {
					"account": frappe.db.get_value("Salary Component", "Contract Allowance", "gl_head"),
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": rec,
					"debit_in_account_currency": flt(cc[rec]['contract_allowance'],2),
					"debit": flt(cc[rec]['contract_allowance'],2),
				})
			#Project Allowance
			if flt(cc[rec]['project_allowance'],2) > 0:
				payables_je.append("accounts", {
						"account": frappe.db.get_value("Salary Component", "Project Allowance", "gl_head"),
						"reference_type": self.doctype,
						"reference_name": self.name,
						"cost_center": rec,
						"debit_in_account_currency": flt(cc[rec]['project_allowance'],2),
						"debit": flt(cc[rec]['project_allowance'],2),
					})
			#Fixed Allowance
			payables_je.append("accounts", {
					"account": frappe.db.get_value("Salary Component", "Fixed Allowance", "gl_head"),
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": rec,
					"debit_in_account_currency": flt(cc[rec]['fixed_allowance'],2),
					"debit": flt(cc[rec]['fixed_allowance'],2),
				})
			#Total Allowance
			total_allowance += flt(cc[rec]['corporate_allowance'],2)+flt(cc[rec]['contract_allowance'],2)+flt(cc[rec]['project_allowance'],2)+flt(cc[rec]['fixed_allowance'],2)
		#Health Contribution
		payables_je.append("accounts", {
				"account": frappe.db.get_value("Salary Component", "Health Contribution", "gl_head"),
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"credit_in_account_currency": flt(health_contribution,2),
				"credit": flt(health_contribution,2),
				"party_check": 0
			})
		#PF
		payables_je.append("accounts", {
				"account": frappe.db.get_value("Salary Component", "PF", "gl_head"),
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"credit_in_account_currency": flt(employee_pf,2),
				"credit": flt(employee_pf,2),
				"party_check": 0
			})
		#Salary Tax
		if salary_tax > 0:
			payables_je.append("accounts", {
					"account": frappe.db.get_value("Salary Component", "Salary Tax", "gl_head"),
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": company_cc,
					"credit_in_account_currency": flt(salary_tax,2),
					"party_check": 0,
					"credit": flt(salary_tax,2),
				})
		#Salary Payble
		payables_je.append("accounts", {
				"account": default_payable_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"credit_in_account_currency": flt(net_payable,2),
				"credit": flt(net_payable,2),
				"party_check": 0
			})
		payables_je.flags.ignore_permissions = 1
		payables_je.insert()
		payables_je.submit()

		#Payables JE End -----------------------------------------------------
		#Salary Tax and HC Bank Entry -----------------------------------------------
		sthc_je = frappe.new_doc("Journal Entry")
		sthc_je.voucher_type= "Bank Entry"
		sthc_je.naming_series = "Bank Payment Voucher"
		sthc_je.title = "Arrear Salary Tax and HC for "+self.from_month
		sthc_je.remark =  "Arrear Salary Tax and HC for "+self.from_month
		sthc_je.posting_date = nowdate()               
		sthc_je.company = self.company
		sthc_je.branch = self.processing_branch
		sthc_je.reference_name =  self.name
		#Health Contribution
		sthc_je.append("accounts", {
				"account": frappe.db.get_value("Salary Component", "Health Contribution", "gl_head"),
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"debit_in_account_currency": flt(health_contribution,2),
				"debit": flt(health_contribution,2),
				"party_check": 0
			})
		#Salary Tax
		if salary_tax > 0:
			sthc_je.append("accounts", {
					"account": frappe.db.get_value("Salary Component", "Salary Tax", "gl_head"),
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": company_cc,
					"debit_in_account_currency": flt(salary_tax,2),
					"debit": flt(salary_tax,2),
					"party_check": 0
				})
		#To Bank Account
		sthc_je.append("accounts", {
				"account": default_bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"credit_in_account_currency": flt(salary_tax,2)+flt(health_contribution,2),
				"credit": flt(salary_tax,2)+flt(health_contribution,2),
			})

		sthc_je.flags.ignore_permissions = 1 
		sthc_je.insert()
		#Salary Tax and HC Bank Entry End -----------------------------------------------

		#PF Bank Entry -----------------------------------------------
		pf_je = frappe.new_doc("Journal Entry")
		pf_je.voucher_type= "Bank Entry"
		pf_je.naming_series = "Bank Payment Voucher"
		pf_je.title = "Arrear PF contribution of TTPL staff for the month of "+self.from_month
		pf_je.remark =  "Arrear PF contribution of TTPL staff for the month of "+self.from_month
		pf_je.posting_date = nowdate()               
		pf_je.company = self.company
		pf_je.branch = self.processing_branch
		pf_je.reference_name =  self.name
		#Employer PF Expense
		total_employer_pf = 0
		for p in cc:
			pf_je.append("accounts", {
					"account": default_gpf_account,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": p,
					"debit_in_account_currency": flt(cc[p]['employer_pf'],2),
					"debit": flt(cc[p]['employer_pf'],2),
				})
			total_employer_pf += flt(cc[p]['employer_pf'],2)
		#Employee PF
		pf_je.append("accounts", {
				"account": frappe.db.get_value("Salary Component", "PF", "gl_head"),
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"debit_in_account_currency": flt(employee_pf,2),
				"debit": flt(employee_pf,2),
				"party_check": 0
			})
		#To Bank Account
		pf_je.append("accounts", {
				"account": default_bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"credit_in_account_currency": flt(employee_pf,2)+flt(total_employer_pf,2),
				"credit": flt(employee_pf,2)+flt(total_employer_pf,2),
			})

		pf_je.flags.ignore_permissions = 1 
		pf_je.insert()
		#PF Bank Entry End -----------------------------------------------

		#Payables to Bank Entry -----------------------------------------------
		pb_je = frappe.new_doc("Journal Entry")
		pb_je.voucher_type= "Bank Entry"
		pb_je.naming_series = "Bank Payment Voucher"
		pb_je.title = "Salary Arrear paid for the month of "+self.from_month
		pb_je.remark =  "Salary Arrear paid for the month of "+self.from_month
		pb_je.posting_date = nowdate()               
		pb_je.company = self.company
		pb_je.branch = self.processing_branch
		pb_je.reference_name =  self.name
		#Salary Payable
		pb_je.append("accounts", {
				"account": default_payable_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"debit_in_account_currency": flt(net_payable,2),
				"debit": flt(net_payable,2),
				"party_check": 0
			})
		#To Bank Account
		pb_je.append("accounts", {
				"account": default_bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"credit_in_account_currency": flt(net_payable,2),
				"credit": flt(net_payable,2),
			})

		pb_je.flags.ignore_permissions = 1 
		pb_je.insert()
		#Salary Tax and HC Bank Entry End -----------------------------------------------
		self.db_set("journal_entries_created", 1)
		frappe.db.commit()

@frappe.whitelist()
def arrear_payment_has_bank_entries(name):
	response = {}
	bank_entries = get_arrear_payment_bank_entries(name)
	response['submitted'] = 1 if bank_entries else 0

	return response

def get_arrear_payment_bank_entries(arrear_payment_name):
	journal_entries = frappe.db.sql(
		'select name from `tabJournal Entry Account` '
		'where reference_type="Salary Arrear Payment" '
		'and reference_name=%s and docstatus=1',
		arrear_payment_name,
		as_dict=1
	)

	return journal_entries

