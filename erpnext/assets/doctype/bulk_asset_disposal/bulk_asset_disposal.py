# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.assets.doctype.asset.depreciation import scrap_asset
from erpnext.assets.doctype.asset.depreciation import get_disposal_account_and_cost_center

class BulkAssetDisposal(Document):
	def validate(self): 
		# self.scrap_date = date.today()
		if self.scrap == "Sale Asset":
			self.valdiate_asset_category()

	def valdiate_asset_category(self):
		if not self.asset_category:
			return
			
		if self.item:
			for data in self.item:
				category = frappe.db.get_value("Asset", data.asset, "asset_category")
				if category != self.asset_category:
					frappe.throw("{} is under <b>{}</b> category. You can only sell from {} category!".format(data.asset, category, self.asset_category))

	def on_submit(self):
		if self.scrap == "Scrap Asset":
			self.scrap_asset()
		# else: 
		# 	self.sale_asset()
	
	def scrap_asset(self):
		for data in self.item: 
			scrap_asset(data.asset, self.scrap_date)

@frappe.whitelist()
def sale_asset(branch, name, scrap_date, customer):
	item = frappe.db.sql("""select a.item_code, a.item_name, a.asset 
						from `tabBulk Asset Disposal Item` as a, `tabBulk Asset Disposal` as b 
						where a.parent = b.name 
						and b.name='{name}' 
						and a.docstatus = 1 
						and b.scrap_date = '{date}' 
						and b.scrap='Sale Asset'
						""".format(name=name, date=scrap_date),as_dict=1)
	si = frappe.new_doc("Sales Invoice")
	si.branch = branch
	# si.business_activity = business_activity
	si.company = frappe.defaults.get_user_default("company")
	si.customer = customer
	company = frappe.defaults.get_user_default("company")
	si.currency = frappe.db.get_value("Company", company, "default_currency")
	si.naming_series = 'Fixed Asset'
	si.selling_price_list = "Standard Selling"
	# disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(company)
	asset_gain_account, asset_loss_account, depreciation_cost_center = get_disposal_account_and_cost_center(company)
	si.bulk_asset_disposal = name
	for data in item:
		si.append("items", {
			"item_code": data.item_code,
			"item_name":data.item_name,
			"is_fixed_asset": 1,
			"asset": data.asset,
			"income_account": asset_gain_account,
			# "serial_no": serial_no,
			"cost_center": depreciation_cost_center,
			"qty": 1,
			"rate": 0
		})
	return si
		
