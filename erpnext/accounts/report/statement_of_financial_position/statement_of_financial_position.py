# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint
from erpnext.accounts.report.financial_statements_emines import (get_period_list, get_columns, get_data)

def execute(filters=None):
	if filters.show_zero_values:
		show_zero = 1
	else:
		show_zero = 0
	period_list = get_period_list(filters.fiscal_year, filters.periodicity)

	asset = get_data(filters.cost_center, filters.company, "Asset", "Debit", period_list, only_current_fiscal_year=False, show_zero_values=show_zero)
	liability = get_data(filters.cost_center,filters.company, "Liability", "Credit", period_list, only_current_fiscal_year=False, show_zero_values=show_zero)
	equity = get_data(filters.cost_center,filters.company, "Equity", "Credit", period_list, only_current_fiscal_year=False, show_zero_values=show_zero)

	provisional_profit_loss = get_provisional_profit_loss(asset, liability, equity,
		period_list, filters.company)

	provisional_profit_loss1 = get_provisional_profit_loss1(asset, liability, equity,
		period_list, filters.company)

	provisional_profit_loss2 = get_provisional_profit_loss2(asset, liability, equity,
		period_list, filters.company)

	message = check_opening_balance(asset, liability, equity)

	data = []
	data.extend(asset or [])
	
	if provisional_profit_loss:
		data.append(provisional_profit_loss)
	data.append("")
	if provisional_profit_loss2:
		data.append(provisional_profit_loss2)
	data.append("")
	data.extend(liability or [])
	data.extend(equity or [])
	if provisional_profit_loss1:
		data.append(provisional_profit_loss1)

	

	columns = get_columns(filters.periodicity, period_list, company=filters.company)

	chart = get_chart_data(columns, asset, liability, equity)

	return columns, data, message, chart

def get_provisional_profit_loss(asset, liability, equity, period_list, company):
	if asset and (liability or equity):
		total=0
		provisional_profit_loss = {
			"account_name": "'" + _("Capital Work-In-Progress (CWIP)") + "'",
			"account": None,
			"warn_if_negative": True,
			"currency": frappe.db.get_value("Company", company, "default_currency")
		}

		has_value = False

		for period in period_list:
			effective_liability = 0.0
			if liability:
				effective_liability += flt(liability[-2].get(period.key))
			if equity:
				effective_liability += flt(equity[-2].get(period.key))

			provisional_profit_loss[period.key] = -(flt(asset[-2].get(period.key)) - effective_liability)

			if provisional_profit_loss[period.key]:
				has_value = True

			total += flt(provisional_profit_loss[period.key])
			provisional_profit_loss["total"] = total

		if has_value:
			return provisional_profit_loss

def get_provisional_profit_loss2(asset, liability, equity, period_list, company):
	if asset and (liability or equity):
		total=0
		provisional_profit_loss2 = {
			"account_name": "'" + _("Total Asset and CWIP") + "'",
			"account": None,
			"warn_if_negative": True,
			"currency": frappe.db.get_value("Company", company, "default_currency")
		}

		has_value = False

		for period in period_list:
			effective_liability = 0.0
			if liability:
				effective_liability += flt(liability[-2].get(period.key))
			if equity:
				effective_liability += flt(equity[-2].get(period.key))

			provisional_profit_loss2[period.key] = -(flt(asset[-2].get(period.key)) - effective_liability) + flt(asset[-2].get(period.key))

			if provisional_profit_loss2[period.key]:
				has_value = True

			total += flt(provisional_profit_loss2[period.key])
			provisional_profit_loss2["total"] = total

		if has_value:
			return provisional_profit_loss2			

def get_provisional_profit_loss1(asset, liability, equity, period_list, company):
	if asset and (liability or equity):
		total=0
		provisional_profit_loss1 = {
			"account_name": "'" + _("Total Liability and Equity") + "'",
			"account": None,
			"warn_if_negative": True,
			"currency": frappe.db.get_value("Company", company, "default_currency")
		}

		has_value = False

		for period in period_list:
			effective_liability = 0.0
			if liability:
				effective_liability += flt(liability[-2].get(period.key))
			if equity:
				effective_liability += flt(equity[-2].get(period.key))

			provisional_profit_loss1[period.key] = (effective_liability)

			if provisional_profit_loss1[period.key]:
				has_value = True

			total += flt(provisional_profit_loss1[period.key])
			provisional_profit_loss1["total"] = total

		if has_value:
			return provisional_profit_loss1

def check_opening_balance(asset, liability, equity):
	# Check if previous year balance sheet closed
	opening_balance = 0
	if asset:
		opening_balance = flt(asset[0].get("opening_balance", 0), 2)
	if liability:
		opening_balance -= flt(liability[0].get("opening_balance", 0), 2)
	if equity:
		opening_balance -= flt(equity[0].get("opening_balance", 0), 2)

	if cint(opening_balance):
		return _("Previous Financial Year is not closed")


def get_chart_data(columns, asset, liability, equity):
	x_intervals = ['x'] + [d.get("label") for d in columns[2:]]

	asset_data, liability_data, equity_data = [], [], []
	for p in columns[2:]:
		if asset:
			asset_data.append(asset[-2].get(p.get("fieldname")))
		if liability:
			liability_data.append(liability[-2].get(p.get("fieldname")))
		if equity:
			equity_data.append(equity[-2].get(p.get("fieldname")))

	columns = [x_intervals]
	if asset_data:
		columns.append(["Assets"] + asset_data)
	if liability_data:
		columns.append(["Liabilities"] + liability_data)
	if equity_data:
		columns.append(["Equity"] + equity_data)

	return {
		"data": {
			'x': 'x',
			'columns': columns
		}
	}
