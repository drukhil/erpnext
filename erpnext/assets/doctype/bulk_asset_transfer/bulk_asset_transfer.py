# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.utils import make_asset_transfer_gl
from erpnext.assets.asset_utils import check_valid_asset_transfer
# from erpnext.assets.doctype.asset_movement.asset_movement import save_equipment

class BulkAssetTransfer(Document):
	def validate_data(self):
		self.custodian_cost_center = frappe.db.get_value("Employee", self.custodian, "cost_center")
		self.custodian_branch = frappe.db.get_value("Employee", self.custodian, "branch")

		for a in self.items:
			a.custodian, a.cost_center = frappe.db.get_value("Asset", a.asset_code, ["issued_to", "cost_center"])
			if self.purpose == "Custodian" and self.current_custodian != a.custodian:
				frappe.throw("Asset data ("+str(a.asset_code)+") had changed since you created the document. Pull the assets again")
			if self.purpose == "Cost Center" and self.cost_center != a.cost_center:
				frappe.throw("Asset data ("+str(a.asset_code)+") had changed since you created the document. Pull the assets again")

	def on_submit(self):
		self.update_asset()

	def before_submit(self):
		if not self.custodian or not self.custodian_cost_center or not self.custodian_branch:
			frappe.throw("The custodian doesn't have Cost Center and Branch defined in Employee Master")

		self.validate_data()

		for a in self.items:
			check_valid_asset_transfer(a.asset_code, self.posting_date)

	def update_asset(self):
		if not self.custodian or not self.custodian_cost_center or not self.custodian_branch:
			frappe.throw("The custodian doesn't have Cost Center and Branch defined in Employee Master")

		for a in self.items:
			doc = frappe.get_doc("Asset", a.asset_code)
			doc.db_set("issued_to", self.custodian)

			if a.cost_center != self.custodian_cost_center:
				doc.db_set("cost_center", self.custodian_cost_center)
				doc.db_set("branch", self.custodian_branch)
				equipment = frappe.db.get_value("Equipment", {"asset_code": a.asset_code, "docstatus": 1}, "name")
				if equipment:
					equip = frappe.get_doc("Equipment", equipment)
					equip.branch = self.custodian_branch
					equip.save()
					#save_equipment(equipment, self.custodian_branch, self.posting_date, self.name, "Submit")
					#doc.db_set("branch", self.custodian_branch)
				make_asset_transfer_gl(self, a.asset_code, self.posting_date, a.cost_center, self.custodian_cost_center)

	def get_assets(self):
		if not self.purpose:
			frappe.throw("Select a Purpose first!")
		if self.cost_center and self.purpose == "Cost Center":
			entries = frappe.db.sql("select name as asset_code, asset_name, gross_purchase_amount as gross_amount, cost_center, issued_to as custodian from tabAsset where status not in ('Scrapped', 'Sold') and cost_center = %s and docstatus = 1", self.cost_center, as_dict=True)
		elif self.current_custodian and self.purpose == "Custodian":
			entries = frappe.db.sql("select name as asset_code, asset_name, gross_purchase_amount as gross_amount, cost_center, issued_to as custodian from tabAsset where status not in ('Scrapped', 'Sold') and issued_to = %s and docstatus = 1", self.current_custodian, as_dict=True)
		else:
			frappe.throw("Either select Cost Center or Custodian")
		self.set('items', [])

		for d in entries:
			row = self.append('items', {})
			row.update(d)

	def on_cancel(self):
		self.reverse_asset_assignment()
		self.delete_gl_entries()

	def reverse_asset_assignment(self):
		for a in self.items:
			check_valid_asset_transfer(a.asset_code, self.posting_date)
			doc = frappe.get_doc("Asset", a.asset_code)
			doc.db_set("issued_to", a.custodian)

			if a.cost_center != self.custodian_cost_center:
				branch = frappe.db.get_value("Cost Center", a.cost_center, "branch")
				doc.db_set("cost_center", a.cost_center)
				doc.db_set("branch", branch)
				equipment = frappe.db.get_value("Equipment", {"asset_code": a.asset_code}, "name")
				if equipment:
					equip = frappe.get_doc("Equipment", equipment)
					equip.branch = branch
					equip.save()
					#save_equipment(equipment, branch, self.posting_date, self.name, "Cancel")

	def delete_gl_entries(self):
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", self.name)

