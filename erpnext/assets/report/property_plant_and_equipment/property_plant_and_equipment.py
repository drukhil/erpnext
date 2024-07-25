# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr, rounded
from erpnext.accounts.report.financial_statements_emines \
	import filter_accounts, set_gl_entries_by_account, filter_out_zero_value_rows

def execute(filters=None):
	columns = get_columns()
	data = get_accounts(filters)
	return columns, data

def get_accounts(filters):
	data = []
	for a in frappe.db.sql("SELECT a.name, b.fixed_asset_account as fa, b.accumulated_depreciation_account as acc, b.depreciation_expense_account as dep from `tabAsset Category` a, `tabAsset Category Account` b where a.name = b.parent", as_dict=True):
		gross_opening = get_values(a.fa, filters.to_date, filters.from_date, filters.cost_center, opening=True)[0]
		gross = get_values(a.fa, filters.to_date, filters.from_date, filters.cost_center)[0]
		dep_opening = get_values(a.acc, filters.to_date, filters.from_date, filters.cost_center, opening=True)[0]
		acc_dep = get_values(a.acc, filters.to_date, filters.from_date, filters.cost_center)[0]
		dep = get_values(a.dep, filters.to_date, filters.from_date, filters.cost_center)[0]
		adj = get_values(a.acc, filters.to_date, filters.from_date, filters.cost_center, adjustment=True)[0]		

		g_open = flt(gross_opening.debit) - flt(gross_opening.credit)
		g_addition = flt(gross.debit)
		g_adjustment = flt(gross.credit)
		g_total = g_open + g_addition - g_adjustment 
		d_open = -1 * (flt(dep_opening.debit) - flt(dep_opening.credit))
		dep_adjust = flt(acc_dep.debit)
		adj_adjust = flt(adj.credit)
		dep_addition = flt(acc_dep.credit) - flt(adj.credit)
		dep_add = flt(acc_dep.credit)
		d_total = d_open + dep_add  - flt(dep_adjust)

		row = [ 
			a.name,
			g_open,
			g_addition,
			g_adjustment,
			g_total,
			d_open,
			dep_addition,
			dep_adjust,
			adj_adjust,
			d_total,
			flt(g_total) - flt(d_total) 
		]	
		data.append(row)

	#FOr CWIP Account
	cwip_acc = []
	cwip_account = frappe.db.get_single_value("Accounts Settings", "cwip_account")
	cwip_accounts_gl = frappe.db.sql("select name from tabAccount where parent_account = %s", cwip_account, as_dict=True)
	for account in cwip_accounts_gl:
		cwip_acc.append(str(account.name))
	cwip_accounts = tuple(cwip_acc)

	cwip_open = get_values(cwip_accounts, filters.to_date, filters.from_date, filters.cost_center, opening=True, cwip=True)
	cwip = get_values(cwip_accounts, filters.to_date, filters.from_date, filters.cost_center, cwip=True)

	cwip_open = cwip_open[0]
	cwip = cwip[0]

	c_open = flt(cwip_open.debit) - flt(cwip_open.credit)
	c_total = c_open + flt(cwip.debit) - flt(cwip.credit)

	row = [
		"Capital Work in Progress",
		c_open,
		cwip.debit,
		cwip.credit,
		c_total,
		0,
		0,
		0,
		0,
		0,
		c_total 
	]	
	data.append(row)
	return data

def get_values(account, to_date, from_date, cost_center=None, opening=False, cwip=False, adjustment=False):
	query = "select sum(debit) as debit, sum(credit) as credit from `tabGL Entry` where account = \'" + str(account) + "\' and docstatus = 1 and posting_date between \'" + from_date + "\' and \'" + to_date + "\'" 
	if cwip:
		query = "select sum(debit) as debit, sum(credit) as credit from `tabGL Entry` where account in %(account)s and docstatus = 1 and posting_date between \'" + from_date + "\' and \'" + to_date + "\'" 
	elif adjustment:
		query = "select sum(debit) as debit, sum(credit) as credit from `tabGL Entry` where account = \'" + str(account) + "\' and docstatus = 1 and is_depreciation_adjustment = 'Yes' and posting_date between \'" + from_date + "\' and \'" + to_date + "\'" 
	else:
		query = "select sum(debit) as debit, sum(credit) as credit from `tabGL Entry` where account = \'" + str(account) + "\' and docstatus = 1 and posting_date between \'" + from_date + "\' and \'" + to_date + "\'" 
	# if not opening:
	# 	query += " and posting_date between \'" + str(from_date) + "\' and \'" + str(to_date) + "\'"
	# else:
	# 	query += " and posting_date < \'" + str(from_date) + "\'"
	if cost_center:
		query += " and cost_center = \'" + str(cost_center) + "\'"

	# query += " and voucher_type not in ('Period Closing Voucher', 'Asset Movement', 'Bulk Asset Transfer')"
	#query += " and voucher_type not in ('Period Closing Voucher')"
	value = frappe.db.sql(query,{"account":account}, as_dict=True)

	return value


def get_columns():
	return [
		{
			"fieldname": "asset_category",
			"label": _("Asset Category"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "gross_opening",
			"label": _("Gross Opening"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "gross_addition",
			"label": _("Gross Addition"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "gross_adjustment",
			"label": _("Gross Adjustment"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "gross_total",
			"label": _("Gross Total"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "dep_opening",
			"label": _("Acc. Dep. Opening"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "dep_addition",
			"label": _("Dep. Addition"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "dep_adjustment",
			"label": _("Dep. Adjustment"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
                        "fieldname": "adjustment",
                        "label": _("Adjustment"),
                        "fieldtype": "Currency",
                        "width": 150
                },
		{
			"fieldname": "dep_total",
			"label": _("Dep. Total"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "net_block",
			"label": _("Net Block"),
			"fieldtype": "Currency",
			"width": 150
		}
]
