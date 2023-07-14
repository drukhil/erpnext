# -*- coding: utf-8 -*-
# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.data import get_first_day, get_last_day, add_days
from frappe.utils import flt, add_months, cint, nowdate, getdate, get_last_day
from frappe.model.document import Document
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import get_fixed_asset_account
from erpnext.assets.doctype.asset.depreciation \
	import get_disposal_account_and_cost_center, get_depreciation_accounts
from erpnext.accounts.accounts_custom_functions import get_number_of_days, calculate_depreciation_date
from frappe.model.naming import make_autoname

class Asset(Document):

	def autoname(self):
		self.name = make_autoname('ASSET.YY.MM.#####')

	def validate(self):
		self.check_asset_values()
		self.status = self.get_status()
		self.validate_item()
		self.set_missing_values()
		self.validate_asset_values()
		self.make_depreciation_schedule()
		self.validate_expected_value_after_useful_life()
		# Validate depreciation related accounts
		get_depreciation_accounts(self)

	def check_asset_values(self):
                if (flt(self.residual_value) + flt(self.opening_accumulated_depreciation) + flt(self.expected_value_after_useful_life)) > flt(self.gross_purchase_amount):
                        frappe.throw("Gross Amount should be >= (Opening + Useful Life + Residual)")

	def on_submit(self):
		self.make_asset_gl_entry()
		self.make_opening_accumulated_gl_entry()
		self.set_status()

	def on_cancel(self):
		self.check_equipment_link()
		self.validate_cancellation()
		self.delete_asset_gl_entries()
		self.delete_depreciation_entries()
		self.set_status()

	def on_update_after_submit(self):
		self.set_status()	
		self.update_parent_cc()

	def update_parent_cc(self):
		if not frappe.get_value("Cost Center", self.cost_center, "is_group"):
			self.parent_cost_center = frappe.get_value("Cost Center", self.cost_center, "parent_cost_center")

	def validate_item(self):
		item = frappe.db.get_value("Item", self.item_code,
			["is_fixed_asset", "is_stock_item", "disabled"], as_dict=1)
		if not item:
			frappe.throw(_("Item {0} does not exist").format(self.item_code))
		elif item.disabled:
			frappe.throw(_("Item {0} has been disabled").format(self.item_code))
		elif not item.is_fixed_asset:
			frappe.throw(_("Item {0} must be a Fixed Asset Item").format(self.item_code))
		elif item.is_stock_item:
			frappe.throw(_("Item {0} must be a non-stock item").format(self.item_code))

	def set_missing_values(self):
		if self.item_code:
			item_details = get_item_details(self.item_code)
			for field, value in item_details.items():
				if not self.get(field):
					self.set(field, value)

		self.value_after_depreciation = (flt(self.gross_purchase_amount) -
			flt(self.opening_accumulated_depreciation)) - flt(self.residual_value)

	def validate_asset_values(self):
		if flt(self.expected_value_after_useful_life) >= flt(self.gross_purchase_amount):
			frappe.throw(_("Expected Value After Useful Life must be less than Gross Purchase Amount"))

		if not flt(self.gross_purchase_amount):
			frappe.throw(_("Gross Purchase Amount is mandatory"), frappe.MandatoryError)

		if not self.is_existing_asset:
			self.opening_accumulated_depreciation = 0
			self.number_of_depreciations_booked = 0
			if not self.next_depreciation_date:
				frappe.throw(_("Next Depreciation Date is mandatory for new asset"))
		else:
			depreciable_amount = flt(self.gross_purchase_amount) - flt(self.expected_value_after_useful_life)
			if flt(self.opening_accumulated_depreciation) > depreciable_amount:
					frappe.throw(_("Opening Accumulated Depreciation must be less than equal to {0}")
						.format(depreciable_amount))

			if self.opening_accumulated_depreciation:
				if not self.number_of_depreciations_booked:
					frappe.throw(_("Please set Number of Depreciations Booked"))
			else:
				self.number_of_depreciations_booked = 0

			if cint(self.number_of_depreciations_booked) > cint(self.total_number_of_depreciations):
				frappe.throw(_("Number of Depreciations Booked cannot be greater than Total Number of Depreciations"))

		#if self.next_depreciation_date and getdate(self.next_depreciation_date) < getdate(nowdate()):
		#	frappe.throw(_("Next Depreciation Date must be on or after today"))

		if (flt(self.value_after_depreciation) > flt(self.expected_value_after_useful_life)
			and not self.next_depreciation_date):
				frappe.throw(_("Please set Next Depreciation Date"))

	def make_depreciation_schedule(self):
		self.schedules = []
		dep_done = 0
		if not self.get("schedules") and self.next_depreciation_date:
			accumulated_depreciation = flt(self.opening_accumulated_depreciation)
			income_accumulated_depreciation = flt(self.income_tax_opening_depreciation_amount)
			value_after_depreciation = flt(self.value_after_depreciation)
			current_value_income_tax = flt(self.value_after_depreciation) - flt(self.expected_value_after_useful_life)

			number_of_pending_depreciations = cint(self.total_number_of_depreciations) - \
				cint(self.number_of_depreciations_booked)
			current_value = flt(self.gross_purchase_amount) - (flt(self.opening_accumulated_depreciation) + flt(self.expected_value_after_useful_life))
			if number_of_pending_depreciations and current_value > 0:
				for n in xrange(number_of_pending_depreciations):
					#frappe.throw("THHH " + str(self.number_of_depreciations_booked))
					schedule_date = get_last_day(add_months(self.next_depreciation_date,
						n * cint(self.frequency_of_depreciation)))

					#last_schedule_date = add_months(self.next_depreciation_date,
					#	(n - 1) * cint(self.frequency_of_depreciation))

					last_schedule_date = get_last_day(add_days(schedule_date, -40))
					if n == 0:
						num_of_days = get_number_of_days(self.purchase_date, schedule_date) + 1
					else:
						num_of_days = get_number_of_days(last_schedule_date, schedule_date) 

					depreciation_amount = self.get_depreciation_amount(value_after_depreciation, num_of_days)
					income_tax_amount = self.get_income_tax_depreciation_amount(income_accumulated_depreciation, flt(self.asset_depreciation_percent), num_of_days)

					accumulated_depreciation += flt(depreciation_amount)
					value_after_depreciation -= flt(depreciation_amount)
					income_accumulated_depreciation += income_tax_amount
				
					val = flt(self.residual_value) + flt(accumulated_depreciation) + flt(self.expected_value_after_useful_life)
	
					if val < self.gross_purchase_amount:
						self.append("schedules", {
							"schedule_date": schedule_date,
							"depreciation_amount": depreciation_amount,
							"depreciation_income_tax": income_tax_amount,
							"accumulated_depreciation_amount": accumulated_depreciation,
							"accumulated_depreciation_income_tax": income_accumulated_depreciation
						})
					else:
						if dep_done == 0:
							self.append("schedules", {
								"schedule_date": schedule_date,
								"depreciation_amount": flt(self.gross_purchase_amount) - flt(val) + flt(depreciation_amount),
								"depreciation_income_tax": income_tax_amount,
								"accumulated_depreciation_amount": flt(self.gross_purchase_amount) - flt(self.residual_value) - flt(self.expected_value_after_useful_life),
								"accumulated_depreciation_income_tax": income_accumulated_depreciation
							})
							dep_done = 1
			
						if dep_done == 1 and income_tax_amount == 0:
							break
						else:
							self.append("schedules", {
								"schedule_date": schedule_date,
								"depreciation_amount": 0,
								"depreciation_income_tax": income_tax_amount,
								"accumulated_depreciation_amount": flt(self.gross_purchase_amount)  - flt(self.residual_value) - flt(self.expected_value_after_useful_life),
								"accumulated_depreciation_income_tax": income_accumulated_depreciation
							})
					

	def get_depreciation_amount(self, depreciable_value, num_days=1):
		if self.depreciation_method == "Straight Line":
			depreciation_amount = ((flt(self.gross_purchase_amount) - flt(self.residual_value)) * 12 * flt(num_days))/(flt(self.total_number_of_depreciations) * 365.25)
		else:
			depreciation_amount = 0.0

		return flt(depreciation_amount, 2)

	def validate_expected_value_after_useful_life(self):
		if self.depreciation_method == "Double Declining Balance":
			accumulated_depreciation_after_full_schedule = \
				max([d.accumulated_depreciation_amount for d in self.get("schedules")])

			asset_value_after_full_schedule = (flt(self.gross_purchase_amount) -
				flt(accumulated_depreciation_after_full_schedule))

			if self.expected_value_after_useful_life < asset_value_after_full_schedule:
				frappe.throw(_("Expected value after useful life must be greater than or equal to {0}")
					.format(asset_value_after_full_schedule))

	def validate_cancellation(self):
		if self.status not in ("Submitted", "Partially Depreciated", "Fully Depreciated"):
			frappe.throw(_("Asset cannot be cancelled, as it is already {0}").format(self.status))

		if self.purchase_invoice:
			frappe.throw(_("Please cancel Purchase Invoice {0} first").format(self.purchase_invoice))

	def delete_depreciation_entries(self):
		for d in self.get("schedules"):
			if d.journal_entry:
				je = frappe.get_doc("Journal Entry", d.journal_entry)
                                if je.docstatus == 1:
                                        je.cancel()
                                d.db_set("journal_entry", None)

		self.db_set("value_after_depreciation",
			(flt(self.gross_purchase_amount) - flt(self.opening_accumulated_depreciation)))

	def set_status(self, status=None):
		'''Get and update status'''
		if not status:
			status = self.get_status()
		disable_depreciation = 0
		if status not in ["Submitted", "Partially Depreciated"]:
			disable_depreciation = 1
		if self.asset_status in ["Auctioned", "Marked for Auction"]:
			disable_depreciation = 1
		self.db_set("status", status)
		self.db_set("disable_depreciation", disable_depreciation)

	def get_status(self):
		'''Returns status based on whether it is draft, submitted, scrapped or depreciated'''
		if self.docstatus == 0:
			status = "Draft"
		elif self.docstatus == 1:
			status = "Submitted"
			if self.journal_entry_for_scrap:
				status = "Scrapped"
			elif flt(self.value_after_depreciation) <= flt(self.expected_value_after_useful_life):
				status = "Fully Depreciated"
			elif flt(self.value_after_depreciation) < flt(self.gross_purchase_amount):
				status = 'Partially Depreciated'
		elif self.docstatus == 2:
			status = "Cancelled"

		return status

	def get_income_tax_depreciation_amount(self, depreciable_value, percent, num_days=1):
		cel = flt(self.gross_purchase_amount) - flt(self.expected_value_after_useful_life)
		if flt(depreciable_value) < flt(cel):
			value = ((flt(self.gross_purchase_amount) - flt(self.residual_value))/(100.00 * 365.25)) * flt(percent) * flt(num_days)
			if flt(depreciable_value) + flt(value) > flt(cel):
				value = flt(cel) - flt(depreciable_value)
			return flt(value)
		else:
			return 0

	def make_asset_gl_entry(self):
		if self.gross_purchase_amount:
			je = frappe.new_doc("Journal Entry")
			je.flags.ignore_permissions = 1 
			je.update({
				"voucher_type": "Journal Entry",
				"company": self.company,
				"remark": self.name + " (" + self.asset_name + ") Asset Issued",
				"user_remark": self.name + " (" + self.asset_name + ") Asset Issued",
				#"posting_date": self.purchase_date,
				"posting_date": self.purchase_date,
				"branch": self.branch
				})

			#credit account update
			je.append("accounts", {
				"account": self.credit_account,
				"credit_in_account_currency": self.gross_purchase_amount,
				"reference_type": "Asset",
				"reference_name": self.name,
				"cost_center": self.cost_center
				})

			#debit account update
			je.append("accounts", {
				"account": self.asset_account,
				"debit_in_account_currency": self.gross_purchase_amount,
				"reference_type": "Asset",
				"reference_name": self.name,
				"cost_center": self.cost_center
				})
			je.submit();

        def make_opening_accumulated_gl_entry(self):
                """
                        1. There is a mistake in getting the account by using the method below. 
                        2. Method and variable Names has to be descriptive
                """
                accumulated_account = frappe.db.get_all("Asset Category Account","accumulated_depreciation_account",{"parent":self.asset_category},order_by="idx", as_list=1)
                accumulated_account = accumulated_account[0][0] if accumulated_account else None 
                #frappe.msgprint(_("{0}").format(accumulated_account))
                if self.opening_accumulated_depreciation:
                        je = frappe.new_doc("Journal Entry")
                        je.flags.ignore_permissions = 1
                        je.update({
                                "voucher_type": "Journal Entry",
                                "company": self.company,
                                "remark": self.name + " (" + self.asset_name + " ) Asset Issued",
                                "user_remark": self.name + "(" + self.asset_name + ") Asset Issued",
                                "posting_date": self.purchase_date,
                                "branch": self.branch
                                })
                        #credit
                        je.append("accounts", {
                                "account" : accumulated_account,
                                "credit_in_account_currency": self.opening_accumulated_depreciation,
                                "reference_type": "Asset",
                                "reference_name": self.name,
                                "cost_center": self.cost_center
                                })
                        #debit account update
                        je.append("accounts", {
                                "account": self.credit_account,
                                "debit_in_account_currency": self.opening_accumulated_depreciation,
                                "reference_type": "Asset",
                                "reference_name": self.name,
                                "cost_center": self.cost_center
                                })
                        je.submit();
		
	def delete_asset_gl_entries(self):
		gl_list = frappe.db.sql(""" select distinct je.name as journal_entry from `tabJournal Entry Account` as jea, `tabJournal Entry` as je where je.voucher_type = 'Journal Entry' and je.name = jea.parent and jea.reference_name = %s and je.docstatus = 1""", self.name, as_dict=True)
		if gl_list:
			for gl in gl_list:
				frappe.get_doc("Journal Entry", gl.journal_entry).cancel()

	def check_equipment_link(self):
		eqp = frappe.db.sql("select name from tabEquipment where asset_code = %s", self.name, as_dict=True)
		if eqp:
			frappe.throw("Unlink the Asset from Equipment <b>" + str(eqp[0].name) + "</b>")

@frappe.whitelist()
def make_purchase_invoice(asset, item_code, gross_purchase_amount, company, posting_date, branch):
	pi = frappe.new_doc("Purchase Invoice")
	pi.company = company
	pi.currency = frappe.db.get_value("Company", company, "default_currency")
	pi.posting_date = posting_date
	pi.branch = branch
	pi.append("items", {
		"item_code": item_code,
		"is_fixed_asset": 1,
		"asset": asset,
		"expense_account": get_fixed_asset_account(asset),
		"qty": 1,
		"price_list_rate": gross_purchase_amount,
		"rate": gross_purchase_amount
	})
	pi.set_missing_values()
	return pi

@frappe.whitelist()
def make_sales_invoice(asset, item_code, company, branch):
	si = frappe.new_doc("Sales Invoice")
	si.company = company
	si.currency = frappe.db.get_value("Company", company, "default_currency")
	disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(company)
	si.branch = branch
	si.title = "Sale of Asset " + str(asset)
	si.naming_series = 'Fixed Asset'
	si.selling_price_list = "Standard Selling"
	si.append("items", {
		"item_code": item_code,
		"is_fixed_asset": 1,
		"asset": asset,
		"income_account": disposal_account,
		"cost_center": depreciation_cost_center,
		"qty": 1
	})
	si.set_missing_values()
	return si

@frappe.whitelist()
def transfer_asset(args):
	import json
	args = json.loads(args)
	if not args.get("target_warehouse") and not args.get("target_custodian"):
		frappe.msgprint("Fill either a target custodian or a warehouse")
	else:
		movement_entry = frappe.new_doc("Asset Movement")
		movement_entry.update(args)
		movement_entry.insert()
		movement_entry.submit()

		frappe.db.commit()

		frappe.msgprint(_("Asset Movement record {0} created").format("<a href='#Form/Asset Movement/{0}'>{0}</a>".format(movement_entry.name)))

@frappe.whitelist()
def get_item_details(item_code):
	asset_category = frappe.db.get_value("Item", item_code, "asset_category")

	if not asset_category:
		frappe.throw(_("Please enter Asset Category in Item {0}").format(item_code))

	ret = frappe.db.get_value("Asset Category", asset_category,
		["depreciation_method", "total_number_of_depreciations", "frequency_of_depreciation"], as_dict=1)

	ret.update({
		"asset_category": asset_category
	})

	return ret

@frappe.whitelist()
def get_next_depreciation_date():
	return calculate_depreciation_date()

def sync_cc_branch():
	objs = frappe.db.sql("select a.name as asset, c.branch as branch  from tabAsset a, `tabCost Center` c where a.cost_center = c.name and a.branch != c.branch", as_dict=True)
	for a in objs:
		frappe.db.sql("update tabAsset set branch = %s where name = %s", (a.branch, a.asset))


