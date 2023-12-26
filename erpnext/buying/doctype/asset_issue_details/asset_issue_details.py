# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class AssetIssueDetails(Document):
	def validate(self):
		self.validate_balance()

	def validate_balance(self):
		received = frappe.db.sql(""" 
				select sum(ifnull(re.qty, 0)) qty from `tabAsset Received Entries` re 
				where re.docstatus = 1 and re.item_code = '{0}' and re.ref_doc = '{1}'
			""".format(self.item_code, self.purchase_receipt), as_dict =1)


		issue = frappe.db.sql(""" 
				select sum(ifnull(ie.qty, 0)) qty from `tabAsset Issue Details` ie 
				where ie.docstatus = 1 and ie.item_code = '{0}' and ie.purchase_receipt = '{1}' and ie.name != '{2}'
					and ie.branch = '{3}'
			""".format(self.item_code, self.purchase_receipt, self.name, self.branch), as_dict =1)

		if flt(received[0].qty) < flt(issue[0].qty) + flt(self.qty):
			diff = flt(received[0].qty) - flt(issue[0].qty)
			uom = frappe.get_doc("Item", self.item_code).stock_uom
			frappe.throw("Asset Issue Cannot Exceed the Received qty, </br> \
						Can Issue Only <b> {0} {2} </b> of Item <b> {1} </b> \
				".format(diff, self.item_code, uom), title="Insufficient Balance")

	def on_submit(self):
		parent_cost_center = frappe.db.get_value("Cost Center", {'name': self.cost_center}, "parent_cost_center")
		item_doc = frappe.get_doc("Item",self.item_code)
		if item_doc.asset_category:
			asset_category = frappe.db.get_value("Asset Category", item_doc.asset_category, "name")
			fixed_asset_account, credit_account=frappe.db.get_value("Asset Category Account", {'parent':asset_category}, ['fixed_asset_account','credit_account'])
			
			total_number_of_depreciations = frappe.db.get_value("Asset Category", item_doc.asset_category, "total_number_of_depreciations")
			depreciation_percent = frappe.db.get_value("Asset Category", item_doc.asset_category, "depreciation_percent")
				
		
		asset = frappe.new_doc("Asset")
		asset.item_code = self.item_code
		asset.asset_name = self.item_name 
		asset.cost_center = self.cost_center
		asset.parent_cost_center = parent_cost_center
		asset.branch = self.branch
		asset.purchase_date = self.issued_date
		asset.next_depreciation_date = self.issued_date
		asset.credit_account = credit_account
		asset.asset_account = fixed_asset_account
		asset.issued_to = self.issued_to
		asset.brand = self.brand
		asset.serial_number = self.serial_number
		asset.asset_quantity_ = self.qty
		asset.asset_rate = self.asset_rate
		asset.model = self.equipment_model
		asset.company = self.company
		asset.gross_purchase_amount = self.amount
		asset.total_number_of_depreciations = total_number_of_depreciations
		asset.asset_depreciation_percent = depreciation_percent
		asset.insert()
		asset.submit()
		frappe.db.commit()

		asset_code = asset.name
		if asset_code:
			self.db_set("reference_code", asset_code)
		else:
			frappe.throw("Asset not able to create for asset issue no.".format(self.name))
	
	def on_cancel(self):
		if self.reference_code:
			asset_status = frappe.db.get_value("Asset", self.reference_code, 'docstatus')
			if asset_status < 2:
				frappe.throw("You cannot cancel the document before cancelling asset with code {0}".format(self.reference_code))
			else:
				frappe.db.sql("update `tabAsset Issue Details` set reference_code = '' where name='{0}'".format(self.name))


@frappe.whitelist()
def check_item_code(doctype=None, txt=None, searchfield=None, start=None, page_len=None, filters=None):
	cond = ""
	if filters.get('item_code'):
		cond += " item_code = '{}' and reference_doctype = '{}' ".format(filters.get('item_code'), filters.get('ref_type'))
		cond += " and branch = '{}'".format(filters.get('branch'))
	query = "select ref_doc from `tabAsset Received Entries` where {cond}".format(cond=cond)
 
	return frappe.db.sql(query)
