# -*- coding: utf-8 -*-
# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0		  SSK		                   17/08/2016         Cost Center is added for Asset Scrapping
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, today, getdate
from erpnext.accounts.accounts_custom_functions import update_jv

def post_depreciation_entries(date=None):
	if not date:
		date = today()
	for asset in get_depreciable_assets(date):
		make_depreciation_entry(asset, date)
		frappe.db.commit()

def get_depreciable_assets(date):
	return frappe.db.sql_list("""select a.name
		from tabAsset a, `tabDepreciation Schedule` ds
		where a.name = ds.parent and a.docstatus=1 and ds.schedule_date<=%s
			and a.disable_depreciation = 0 
			and ifnull(ds.journal_entry, '')=''""", date)

@frappe.whitelist()
def make_depreciation_entry(asset_name, date=None):
	frappe.has_permission('Journal Entry', throw=True)
	
	if not date:
		date = today()

	asset = frappe.get_doc("Asset", asset_name)
	
	if asset.disable_depreciation:
		frappe.throw("Depreciation disabled for this asset")


	fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account = \
		get_depreciation_accounts(asset)

	#depreciation_cost_center = frappe.db.get_value("Company", asset.company, "depreciation_cost_center")
	depreciation_cost_center = asset.cost_center
	
	value_after_dep = 0
	for d in asset.get("schedules"):
		if not d.journal_entry and getdate(d.schedule_date) <= getdate(date):
			je = frappe.new_doc("Journal Entry")
			je.voucher_type = "Depreciation Entry"
			je.posting_date = d.schedule_date
			je.company = asset.company
			je.branch = asset.branch
			je.remark = "Depreciation Entry against {0} worth {1}".format(asset_name, d.depreciation_amount)

			je.append("accounts", {
				"account": accumulated_depreciation_account,
				"credit_in_account_currency": d.depreciation_amount,
				"reference_type": "Asset",
				"reference_name": asset.name,
				"cost_center": depreciation_cost_center
			})

			je.append("accounts", {
				"account": depreciation_expense_account,
				"debit_in_account_currency": d.depreciation_amount,
				"reference_type": "Asset",
				"reference_name": asset.name,
				"cost_center": depreciation_cost_center
			})

			je.flags.ignore_permissions = True
			je.submit()

			d.db_set("journal_entry", je.name)
			value_after_dep = flt(asset.gross_purchase_amount) - flt(d.accumulated_depreciation_amount) - flt(asset.residual_value)

	asset.db_set("value_after_depreciation", value_after_dep)
	asset.set_status()

	return asset

def get_depreciation_accounts(asset):
	fixed_asset_account = accumulated_depreciation_account = depreciation_expense_account = None
	
	accounts = frappe.db.get_value("Asset Category Account",
		filters={'parent': asset.asset_category, 'company_name': asset.company},
		fieldname = ['fixed_asset_account', 'accumulated_depreciation_account',
			'depreciation_expense_account'], as_dict=1)

	if accounts:	
		fixed_asset_account = accounts.fixed_asset_account
		accumulated_depreciation_account = accounts.accumulated_depreciation_account
		depreciation_expense_account = accounts.depreciation_expense_account
		
	if not accumulated_depreciation_account or not depreciation_expense_account:
		accounts = frappe.db.get_value("Company", asset.company,
			["accumulated_depreciation_account", "depreciation_expense_account"])
		
		if not accumulated_depreciation_account:
			accumulated_depreciation_account = accounts[0]
		if not depreciation_expense_account:
			depreciation_expense_account = accounts[1]

	if not fixed_asset_account or not accumulated_depreciation_account or not depreciation_expense_account:
		frappe.throw(_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}")
			.format(asset.asset_category, asset.company))

	return fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account

@frappe.whitelist()
def scrap_asset(asset_name, scrap_date):
	asset = frappe.get_doc("Asset", asset_name)

	if asset.docstatus != 1:
		frappe.throw(_("Asset {0} must be submitted").format(asset.name))
	elif asset.status in ("Cancelled", "Sold", "Scrapped"):
		frappe.throw(_("Asset {0} cannot be scrapped, as it is already {1}").format(asset.name, asset.status))

	#Update already depreciated entries to zero
	schedules = frappe.db.sql("select name, journal_entry, depreciation_amount from `tabDepreciation Schedule` where parent = %s and schedule_date between %s and %s",( asset_name, scrap_date, today()), as_dict=True)
	total_amount = 0.00;
	for i in schedules:
		total_amount += flt(i.depreciation_amount)
		update_jv(i.journal_entry, 0.00)
		frappe.db.set_value("Depreciation Schedule", i.name, "journal_entry", "")

	asset.value_after_depreciation = flt(asset.value_after_depreciation) + flt(total_amount)
	frappe.db.set_value("Asset", asset_name, "value_after_depreciation", asset.value_after_depreciation)
	
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.posting_date = scrap_date 
	je.company = asset.company
	je.branch = asset.branch
	je.remark = "Scrap Entry for asset {0}".format(asset_name)

	for entry in get_gl_entries_on_asset_disposal(asset):
		entry.update({
			"reference_type": "Asset",
			"reference_name": asset_name
		})
		je.append("accounts", entry)

	je.flags.ignore_permissions = True
	je.insert()
	
	frappe.db.set_value("Asset", asset_name, "disposal_date", scrap_date)
	frappe.db.set_value("Asset", asset_name, "journal_entry_for_scrap", je.name)
	asset.set_status("Scrapped")

	frappe.msgprint(_("Asset scrapped via Journal Entry {0}").format(je.name))

@frappe.whitelist()
def restore_asset(asset_name):
	asset = frappe.get_doc("Asset", asset_name)

	je = asset.journal_entry_for_scrap
	
	asset.db_set("disposal_date", None)
	asset.db_set("journal_entry_for_scrap", None)
	
	frappe.get_doc("Journal Entry", je).cancel()

	asset.set_status()

@frappe.whitelist()
def get_gl_entries_on_asset_disposal(asset, selling_amount=0):
	fixed_asset_account, accumulated_depr_account, depr_expense_account = get_depreciation_accounts(asset)
	asset_gain_account, asset_loss_account, depreciation_cost_center = get_disposal_account_and_cost_center(asset.company)
	accumulated_depr_amount = flt(asset.gross_purchase_amount) - flt(asset.value_after_depreciation)

        # Ver 1.0 Begins by SSK, cost_center is added in the following block 
	gl_entries = [
		{
			"account": fixed_asset_account,
			"credit_in_account_currency": asset.gross_purchase_amount,
			"credit": asset.gross_purchase_amount,
                        "cost_center": asset.cost_center
		},
		{
			"account": accumulated_depr_account,
			"debit_in_account_currency": accumulated_depr_amount,
			"debit": accumulated_depr_amount,
                        "cost_center": asset.cost_center
		}
	]
        # Ver 1.0 Ends

	profit_amount = flt(selling_amount) - flt(asset.value_after_depreciation)
	disposal_account = asset_loss_account if profit_amount < 0 else asset_gain_account
	if flt(asset.value_after_depreciation) and profit_amount:
		debit_or_credit = "debit" if profit_amount < 0 else "credit"
		gl_entries.append({
			"account": disposal_account,
			"cost_center": asset.cost_center, 
			debit_or_credit: abs(profit_amount),
			debit_or_credit + "_in_account_currency": abs(profit_amount)
		})

	return gl_entries

@frappe.whitelist()
def get_disposal_account_and_cost_center(company):
	disposal_account, loss_disposal_account, depreciation_cost_center = frappe.db.get_value("Company", company,
		["disposal_account", "loss_disposal_account", "depreciation_cost_center"])

	if not disposal_account:
		frappe.throw(_("Please set 'Gain Account on Asset Disposal' in Company {0}").format(company))
	if not loss_disposal_account:
		frappe.throw(_("Please set 'Loss Account on Asset Disposal' in Company {0}").format(company))
	if not depreciation_cost_center:
		frappe.throw(_("Please set 'Asset Depreciation Cost Center' in Company {0}").format(company))

	return disposal_account, loss_disposal_account, depreciation_cost_center
