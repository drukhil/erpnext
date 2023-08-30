# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, get_last_day, fmt_money
from frappe.model.naming import make_autoname
from frappe.model.document import Document
from erpnext.custom_utils import check_budget_available

class BudgetError(frappe.ValidationError): pass
class DuplicateBudgetError(frappe.ValidationError): pass

class Budget(Document):
	def autoname(self):
		self.name = make_autoname(self.cost_center + "/" + self.fiscal_year + "/.###")

	def validate(self):
		self.validate_duplicate()
		self.validate_accounts()
		self.calculate_budget()
		self.calculate_total()


	def validate_duplicate(self):
		existing_budget = frappe.db.get_value("Budget", {"cost_center": self.cost_center,
			"company": self.company,
			"name": ["!=", self.name], "docstatus": ["!=", 2]})
		if existing_budget:
			frappe.throw(_("Another Budget record {0} already exists against {1} for fiscal year {2}")
				.format(existing_budget, self.cost_center, self.fiscal_year), DuplicateBudgetError)

	def validate_accounts(self):
		account_list = []
		for d in self.get('accounts'):
			if d.account:
				account_details = frappe.db.get_value("Account", d.account,
					["is_group", "company", "report_type"], as_dict=1)

				if account_details:
					if account_details.is_group:
						frappe.throw(_("Budget cannot be assigned against Group Account {0}").format(d.account))
					elif account_details.company != self.company:
						frappe.throw(_("Account {0} does not belongs to company {1}")
							.format(d.account, self.company))
					elif account_details.report_type != "Profit and Loss" and account_details.report_type != "Balance Sheet":
						frappe.throw(_("Budget cannot be assigned against {0}, as it's not an Income or Expense account")
							.format(d.account))

					if d.account in account_list:
						frappe.throw(_("Account {0} has been entered multiple times").format(d.account))
					else:
						account_list.append(d.account)
				else:
					frappe.msgprint("Account <b>" + str(d.account) + "</b> not found on system")
	#Populate Budget Accounts with Expense and Fixed Asset Accounts
	def get_accounts(self):
		query = "select name as account, account_code from tabAccount where account_type in (\'Expense Account\',\'Fixed Asset\') and is_group = 0 and company = \'" + str(self.company) + "\' and (freeze_account is null or freeze_account != 'Yes') order by account_code ASC"
		entries = frappe.db.sql(query, as_dict=True)
		self.set('accounts', [])

		for d in entries:
			d.initial_budget = 0
			row = self.append('accounts', {})
			row.update(d)

	#calculate budgets
	def calculate_budget(self):
		if self.accounts:
			for acc in self.accounts:
				acc.budget_amount = flt(acc.initial_budget) + flt(acc.supplementary_budget) + flt(acc.budget_received) - flt(acc.budget_sent)
				acc.db_set("budget_amount", acc.budget_amount)


	def calculate_total(self):
        	init_amount = 0.0;
        	actual_amount = 0.0;
        	sup_amount = 0.0;
        	for a in self.get("accounts"):
                        init_amount += flt(a.initial_budget)
                        actual_amount += flt(a.budget_amount)
                        sup_amount += flt(a.supplementary_budget)
		self.initial_total = flt(init_amount)
		self.actual_total = flt(actual_amount)
		self.supp_total = flt(sup_amount)

def validate_expense_against_budget(args):
	args = frappe._dict(args)
	if args.against_voucher_type == 'Asset':
		pass
	elif frappe.db.get_value("Account", {"name": args.account, "root_type": "Expense"}) or frappe.db.get_value("Account", {"name": args.account, "root_type": "Asset", "account_type": "Fixed Asset"}):
		if args.debit_in_account_currency:
                        return check_budget_available(args.cost_center, args.account, args.posting_date, flt(args.debit_in_account_currency), False)
	else:
		pass

		"""if args.account in ['Normal Loss - SMCL', 'Abnormal Loss - SMCL', 'Cost of Goods Manufacture - CDCL', 'Expenses Included In Valuation - CDCL', 'Increase or Decrease in Stock - CDCL', 'Stock Adjustment - CDCL', 'Discount alllowed - CDCL', 'Gain or Loss on Sale of Asset - CDCL', 'Gain or Loss on Sale of Inventory - CDCL', 'Gain or Loss on Foreign Exchange - CDCL']:
			pass
		elif str(frappe.db.get_value("Account", args.account, "parent_account")) == "Depreciation & Amortisation - SMCL":
			pass
		else:
			budget_amount = frappe.db.sql("select ba.budget_amount from `tabBudget` b, `tabBudget Account` ba where b.docstatus = 1 and ba.parent = b.name and ba.account=%s and b.cost_center=%s and b.fiscal_year = %s", (args.account, args.cost_center, args.fiscal_year), as_dict=True)
			if budget_amount:
				consumed = frappe.db.sql("select SUM(cb.amount) as total from `tabCommitted Budget` cb where cb.docstatus = 1 and cb.cost_center=%s and cb.account=%s and cb.po_date between %s and %s", (args.cost_center, args.account, args.fiscal_year+ "-01-01", args.fiscal_year + "-12-31"), as_dict=True)
				amount = flt(args.debit) - flt(args.credit)
				if consumed:
					amount = flt(amount) + flt(consumed[0].total)
				if flt(budget_amount[0].budget_amount) < amount:
					frappe.throw("Not enough budget in " + str(args.account) + " under " + str(args.cost_center) + ". Budget exceeded by " + str((amount - flt(budget_amount[0].budget_amount))))
			else:
				if flt(args.debit):
					frappe.throw("There is no budget in <b>" + str(args.account) + "</b> under <b>" + str(args.cost_center) + "</b>")
			"""

def compare_expense_with_budget(args, cost_center, budget_amount, action_for, action):
	actual_expense = get_actual_expense(args, cost_center)
	if actual_expense > budget_amount:
		diff = actual_expense - budget_amount
		currency = frappe.db.get_value('Company', frappe.db.get_value('Cost Center',
			cost_center, 'company'), 'default_currency')

		msg = _("{0} Budget for Account {1} against Cost Center {2} is {3}. It will exceed by {4}").format(_(action_for),
			frappe.bold(args.account), frappe.bold(cost_center),
			frappe.bold(fmt_money(budget_amount, currency=currency)), frappe.bold(fmt_money(diff, currency=currency)))

		if action=="Stop":
			frappe.throw(msg, BudgetError)
		else:
			frappe.msgprint(msg, indicator='orange')

def get_accumulated_monthly_budget(monthly_distribution, posting_date, fiscal_year, annual_budget):
	distribution = {}
	if monthly_distribution:
		for d in frappe.db.sql("""select mdp.month, mdp.percentage_allocation
			from `tabMonthly Distribution Percentage` mdp, `tabMonthly Distribution` md
			where mdp.parent=md.name and md.fiscal_year=%s""", fiscal_year, as_dict=1):
				distribution.setdefault(d.month, d.percentage_allocation)

	dt = frappe.db.get_value("Fiscal Year", fiscal_year, "year_start_date")
	accumulated_percentage = 0.0

	while(dt <= getdate(posting_date)):
		if monthly_distribution:
			accumulated_percentage += distribution.get(getdate(dt).strftime("%B"), 0)
		else:
			accumulated_percentage += 100.0/12

		dt = add_months(dt, 1)

	return annual_budget * accumulated_percentage / 100

def get_actual_expense(args, cost_center):
	lft_rgt = frappe.db.get_value("Cost Center", cost_center, ["lft", "rgt"], as_dict=1)
	args.update(lft_rgt)

	condition = " and gle.posting_date <= %(month_end_date)s" if args.get("month_end_date") else ""

	return flt(frappe.db.sql("""
		select sum(gle.debit) - sum(gle.credit)
		from `tabGL Entry` gle
		where gle.account=%(account)s
			and exists(select name from `tabCost Center`
				where lft>=%(lft)s and rgt<=%(rgt)s and name=gle.cost_center)
			and gle.fiscal_year=%(fiscal_year)s
			and gle.company=%(company)s
			and gle.docstatus=1
			and gle.is_opening != 'Yes'
			{condition}
	""".format(condition=condition), (args))[0][0])



