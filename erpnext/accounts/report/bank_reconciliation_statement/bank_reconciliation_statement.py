# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, nowdate
from frappe import _

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()

	if not filters.get("account"): return columns, []
	
	account_currency = frappe.db.get_value("Account", filters.account, "account_currency")

	data = get_entries(filters)
	
	from erpnext.accounts.utils import get_balance_on
	balance_as_per_system = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0,0
	for d in data:
		total_debit += flt(d.debit)
		total_credit += flt(d.credit)
		
	amounts_not_reflected_in_system = get_amounts_not_reflected_in_system(filters)

	bank_bal = flt(balance_as_per_system) - flt(total_debit) + flt(total_credit) \
		+ amounts_not_reflected_in_system

	data += [
		get_balance_row(_("Balance as per Cash Book"), balance_as_per_system, account_currency),
		{},
		{
			"payment_entry": _("Cheques issued but not encashed"),
			"debit": 0,
			"credit": total_credit,
			"account_currency": account_currency
		},
		{
			"payment_entry": _("Cheques deposited but not cleared"),
			"debit": total_debit,
			"credit": 0,
			"account_currency": account_currency
		},
		#get_balance_row(_("Cheques desposited but not cleared"), amounts_not_reflected_in_system, 
		#	account_currency),
		{},
		get_balance_row(_("Balance as per Bank Statement"), bank_bal, account_currency)
	]

	return columns, data

def get_columns():
	return [
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 90
		},
		{
			"fieldname": "payment_entry",
			"label": _("Payment Entry"),
			"fieldtype": "Dynamic Link",
			"options": "payment_document",
			"width": 220
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120
		},
		{
			"fieldname": "against_account",
			"label": _("Against Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 200
		},
		{
			"fieldname": "reference_no",
			"label": _("Reference"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "ref_date",
			"label": _("Ref Date"),
			"fieldtype": "Date",
			"width": 110
		},
		{
			"fieldname": "clearance_date",
			"label": _("Clearance Date"),
			"fieldtype": "Date",
			"width": 110
		},		
		{
			"fieldname": "account_currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 100
		}
	]

def get_entries(filters):
	journal_entries = frappe.db.sql("""
		select "Journal Entry" as payment_document, jv.posting_date, 
			jv.name as payment_entry, jvd.debit_in_account_currency as debit, 
			jvd.credit_in_account_currency as credit, jvd.against_account, 
			jv.cheque_no as reference_no, jv.cheque_date as ref_date, jv.clearance_date, jvd.account_currency
		from
			`tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1
			and jvd.account = %(account)s and jv.posting_date <= %(report_date)s
			and ifnull(jv.clearance_date, '4000-01-01') > %(report_date)s
			and ifnull(jv.is_opening, 'No') = 'No'""", filters, as_dict=1)
			
	payment_entries = frappe.db.sql("""
		select 
			"Payment Entry" as payment_document, name as payment_entry, 
			reference_no, reference_date as ref_date, 
			if(paid_to=%(account)s, received_amount + loss_and_gain, 0) as debit, 
			if(paid_from=%(account)s, paid_amount + loss_and_gain, 0) as credit, 
			posting_date, party as against_account, clearance_date,
			if(paid_to=%(account)s, paid_to_account_currency, paid_from_account_currency) as account_currency
		from `tabPayment Entry`
		where
			(paid_from=%(account)s or paid_to=%(account)s) and docstatus=1
			and posting_date <= %(report_date)s
			and ifnull(clearance_date, '4000-01-01') > %(report_date)s
	""", filters, as_dict=1)

        direct_payment_entries = frappe.db.sql("""
                        select
                                "Direct Payment" as payment_document, name as payment_entry,
                                cheque_no as reference_no, cheque_date as ref_date,
                                net_amount as credit, 0 as debit,
                                posting_date, branch as against_account, clearance_date
                        from `tabDirect Payment`
                        where %(account)s IN (credit_account, debit_account)
                        and docstatus = 1
                        and posting_date <= %(report_date)s
                        and ifnull(clearance_date, '4000-01-01') > %(report_date)s
                """, filters, as_dict=1)

	hsd_entries = frappe.db.sql("""
		select
			"HSD Payment" as payment_document, name as payment_entry,
			amount as credit, 0 as debit,
			cheque__no as reference_no, cheque_date as ref_date,
			posting_date, supplier as against_account, clearance_date, 'BTN' as account_currency
		from `tabHSD Payment`
		where bank_account = %(account)s
		and docstatus = 1
		and posting_date <= %(report_date)s 
		and ifnull(clearance_date, '4000-01-01') > %(report_date)s
	""", filters, as_dict=1)

	imprest_entries = frappe.db.sql("""
		select
			"Imprest Recoup" as payment_document, name as payment_entry,
			cheque_no as reference_no, cheque_date as ref_date,
			purchase_amount as credit, 0 as debit,
			posting_date, branch as against_account, clearance_date, 'BTN' as account_currency
		from `tabImprest Recoup`
		where revenue_bank_account = %(account)s
		and docstatus = 1
		and posting_date <= %(report_date)s 
		and ifnull(clearance_date, '4000-01-01') > %(report_date)s
	""", filters, as_dict=1)

	mechanical_entries = frappe.db.sql("""
		select
			"Mechanical Payment" as payment_document, name as payment_entry,
			cheque_no as reference_no, cheque_date as ref_date,
			net_amount as debit, 0 as credit,
			posting_date, customer as against_account, clearance_date, 'BTN' as account_currency
		from `tabMechanical Payment`
		where income_account = %(account)s
		and docstatus = 1
		and posting_date <= %(report_date)s 
		and ifnull(clearance_date, '4000-01-01') > %(report_date)s
	""", filters, as_dict=1)

	project_entries = frappe.db.sql("""
		select
			"Project Payment" as payment_document, name as payment_entry,
			cheque_no as reference_no, cheque_date as ref_date,
			paid_amount as debit, 0 as credit,
			posting_date, party as against_account, clearance_date, 'BTN' as account_currency
		from `tabProject Payment`
		where revenue_bank_account = %(account)s
		and docstatus = 1
		and posting_date <= %(report_date)s 
		and ifnull(clearance_date, '4000-01-01') > %(report_date)s
	""", filters, as_dict=1)

	tds_remittance_entries = frappe.db.sql ("""
                        select
                                "TDS Remittance" as payment_document, name as payment_entry,
                                cheque_no as reference_no, cheque_date as ref_date,
                                total_tds as credit, 0 as debit,
                                posting_date, branch as against_account, clearance_date
                        from `tabTDS Remittance`
                        where account = %(account)s
                        and docstatus =1
                        and posting_date <= %(report_date)s
                        and ifnull(clearance_date, '4000-01-01') > %(report_date)s
                """,filters, as_dict=1)



	ot_payment = frappe.db.sql("""
                        select
                                "Process Overtime Payment" as payment_document, name as payment_entry,
                                cheque_no as reference_no, cheque_date as ref_date,
                                total_amount as credit, 0 as debit,
                                posting_date, branch as against_account, clearance_date, 'BTN' as account_currency
                        from `tabProcess Overtime Payment`
                        where expense_bank_account = %(account)s
                        and docstatus = 1
                        and posting_date <= %(report_date)s and ifnull(clearance_date, '4000-01-01') > %(report_date)s
                """, filters, as_dict=1)

	sales_payment = frappe.db.sql("""
                        select
                                "Sales Payment" as payment_document, name as payment_entry,
                                cheque_no as reference_no, cheque_date as ref_date,
                                total_amount as debit, 0 as credit,
                                posting_date, branch as against_account, clearance_date, 'BTN' as account_currency
                        from `tabSales Payment`
                        where revenue_bank_account = %(account)s
                        and docstatus = 1
                        and posting_date <= %(report_date)s and ifnull(clearance_date, '4000-01-01') > %(report_date)s
                """, filters, as_dict=1)
	
	return sorted(list(payment_entries)+list(journal_entries)+list(hsd_entries)+list(imprest_entries)+list(mechanical_entries)+list(project_entries)+list(direct_payment_entries)+list(tds_remittance_entries)+list(ot_payment) +list(sales_payment), 
		key=lambda k: k['posting_date'] or getdate(nowdate()))

		
def get_amounts_not_reflected_in_system(filters):
	je_amount = frappe.db.sql("""
		select sum(jvd.debit_in_account_currency - jvd.credit_in_account_currency)
		from `tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1 and jvd.account=%(account)s
		and jv.posting_date > %(report_date)s and jv.clearance_date <= %(report_date)s 
		and ifnull(jv.is_opening, 'No') = 'No' """, filters)

	je_amount = flt(je_amount[0][0]) if je_amount else 0.0
	
	pe_amount = frappe.db.sql("""
		select sum(if(paid_from=%(account)s, paid_amount, received_amount))
		from `tabPayment Entry`
		where (paid_from=%(account)s or paid_to=%(account)s) and docstatus=1 
		and posting_date > %(report_date)s and clearance_date <= %(report_date)s""", filters)

	pe_amount = flt(pe_amount[0][0]) if pe_amount else 0.0
	
	return je_amount + pe_amount

def get_balance_row(label, amount, account_currency):
	if amount > 0:
		return {
			"payment_entry": label,
			"debit": amount,
			"credit": 0,
			"account_currency": account_currency
		}
	else:
		return {
			"payment_entry": label,
			"debit": 0,
			"credit": abs(amount),
			"account_currency": account_currency
		}
