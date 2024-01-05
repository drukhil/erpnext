# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.utils import make_asset_transfer_gl
from frappe.utils import getdate, nowdate
from erpnext.assets.asset_utils import check_valid_asset_transfer

class AssetMovement(Document):
	def validate(self):
		self.assign_data()
		self.validate_asset()
		if self.target_warehouse:
			self.validate_warehouses()
		if self.target_custodian:
			self.validate_custodian()
			self.target_cost_center = None
			self.target_custodian_cost_center, self.target_user_id = frappe.db.get_value("Employee", self.target_custodian, ["cost_center", "user_id"])	
		if self.target_cost_center:
			if self.target_cost_center == self.current_cost_center:
				frappe.throw("Target and Source Cost Center cannot be same.")
			self.target_custodian = None
			self.target_custodian_cost_center = None

	def assign_data(self):
		self.source_custodian = frappe.db.get_value("Asset", self.asset, "issued_to")
		self.source_custodian_name = frappe.db.get_value("Asset", self.asset, "employee_name")
		self.current_cost_center = frappe.db.get_value("Asset", self.asset, "cost_center")

	def validate_asset(self):
		status, company = frappe.db.get_value("Asset", self.asset, ["status", "company"])
		if status in ("Draft", "Scrapped", "Sold"):
			frappe.throw(_("{0} asset cannot be transferred").format(status))
			
		if company != self.company:
			frappe.throw(_("Asset {0} does not belong to company {1}").format(self.asset, self.company))
			
	def validate_warehouses(self):
		if not self.source_warehouse:
			self.source_warehouse = frappe.db.get_value("Asset", self.asset, "warehouse")
		
		if self.source_warehouse == self.target_warehouse:
			frappe.throw(_("Source and Target Warehouse cannot be same"))

	def validate_custodian(self):
		if not self.source_custodian:
			self.source_custodian = frappe.db.get_value("Asset", self.asset, "issued_to")
		
		if self.source_custodian == self.target_custodian:
			frappe.throw(_("Source and Target Custodian cannot be same"))

	def before_submit(self):
		self.assign_data()
		check_valid_asset_transfer(self.asset, self.posting_date)
	
	def on_submit(self):
		if not self.target_custodian and not self.target_cost_center:
			frappe.throw("Target Custodian or Cost Center is Mandatory")
		if self.target_warehouse:
			self.set_latest_warehouse_in_asset()
		if self.target_custodian:
			self.set_latest_custodian_in_asset()
			if self.target_custodian_cost_center != self.current_cost_center:		
				make_asset_transfer_gl(self, self.asset, self.posting_date, self.current_cost_center, self.target_custodian_cost_center)
		if self.target_cost_center:	
			self.set_latest_cc_in_asset()
			make_asset_transfer_gl(self, self.asset, self.posting_date, self.current_cost_center, self.target_cost_center)
	
	def on_cancel(self):
		check_valid_asset_transfer(self.asset, self.posting_date)
		self.check_depreciation_done()
		if self.target_warehouse:
			self.set_latest_warehouse_in_asset()
		if self.target_custodian:
			self.set_latest_custodian_in_asset(True)
		if self.target_cost_center:	
			self.set_latest_cc_in_asset(True)
		self.cancel_gl_entries()

	def check_depreciation_done(self):
		if self.target_custodian:
			if self.target_custodian_cost_center != self.current_cost_center:		
				self.check_gls()
		if self.target_cost_center:	
			self.check_gls()

	def check_gls(self):
		jes = frappe.db.sql("select je.name from `tabJournal Entry` je, `tabJournal Entry Account` jea where je.name = jea.parent and jea.reference_name = %s and je.posting_date between %s and %s", (self.asset, self.posting_date, getdate(nowdate())), as_dict=True)
		for a in jes:
			frappe.throw("Cannot cancel since asset depreciations had already taken place")

	def cancel_gl_entries(self):
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", self.name)
	
	def set_latest_warehouse_in_asset(self):
		latest_movement_entry = frappe.db.sql("""select target_warehouse from `tabAsset Movement`
			where asset=%s and docstatus=1 and company=%s
			order by posting_date desc limit 1""", (self.asset, self.company))
		
		if latest_movement_entry:
			warehouse = latest_movement_entry[0][0]
		else:
			warehouse = frappe.db.sql("""select source_warehouse from `tabAsset Movement`
				where asset=%s and docstatus=2 and company=%s
				order by posting_date asc limit 1""", (self.asset, self.company))[0][0]
		
		frappe.db.set_value("Asset", self.asset, "warehouse", warehouse)
	
	def set_latest_custodian_in_asset(self, cancel=None):
		#latest_movement_entry = frappe.db.sql("""select target_custodian from `tabAsset Movement`
		#	where asset=%s and docstatus=1 and company=%s
		#	order by posting_date desc limit 1""", (self.asset, self.company))
		#
		#if latest_movement_entry:
		#	custodian = latest_movement_entry[0][0]
		#else:
		#	custodian = frappe.db.sql("""select source_custodian from `tabAsset Movement`
		#		where asset=%s and docstatus=2 and company=%s
		#		order by posting_date asc limit 1""", (self.asset, self.company))[0][0]
		if cancel:
			custodian = self.source_custodian	
			purpose = "Cancel"
                        cost_center = self.current_cost_center
		else:
			custodian = self.target_custodian
			purpose = "Submit"
                        cost_center = self.target_custodian_cost_center

		frappe.db.set_value("Asset", self.asset, "issued_to", custodian)
		frappe.db.set_value("Asset", self.asset, "employee_name", frappe.get_doc("Employee", custodian).employee_name)
	
		if self.current_cost_center != self.target_custodian_cost_center:
			branch = frappe.db.get_value("Cost Center", cost_center, "branch")
			frappe.db.set_value("Asset", self.asset, "cost_center", frappe.db.get_value("Employee", custodian, "cost_center"))
			frappe.db.set_value("Asset", self.asset, "branch", branch)
			
			equipment = frappe.db.get_value("Equipment", {"asset_code": self.asset}, "name")
			if equipment:
				equip = frappe.get_doc("Equipment", equipment)
				equip.branch = branch
				equip.save()
				#save_equipment(equipment, branch, self.posting_date, self.name, purpose)
			fuelbook = frappe.db.get_value("Equipment", {"asset_code": self.asset}, "fuelbook")
			if fuelbook:
				fuelb = frappe.get_doc("Fuelbook", fuelbook)
				fuelb.branch = branch
				fuelb.save()

	def set_latest_cc_in_asset(self, cancel=None):
		#latest_movement_entry = frappe.db.sql("""select target_cost_center from `tabAsset Movement`
		#	where asset=%s and docstatus=1 and company=%s
		#	order by posting_date desc limit 1""", (self.asset, self.company))
		#
		#if latest_movement_entry:
		#	cc = latest_movement_entry[0][0]
		#else:
		#	cc = frappe.db.sql("""select current_cost_center from `tabAsset Movement`
		#		where asset=%s and docstatus=2 and company=%s
		#		order by posting_date asc limit 1""", (self.asset, self.company))[0][0]
		if cancel:
			cc = self.current_cost_center
			purpose = "Cancel"
		else:
			cc = self.target_cost_center
			purpose = "Submit"

		branch = frappe.db.get_value("Cost Center", cc, "branch")
		frappe.db.set_value("Asset", self.asset, "cost_center", cc)
		frappe.db.set_value("Asset", self.asset, "branch", branch)

# 		equipment = frappe.db.get_value("Equipment", {"asset_code": self.asset}, "name")
#                 if equipment:
#                         save_equipment(equipment, branch, self.posting_date, self.name, purpose)

# def save_equipment(equipment, branch, posting_date, ref_doc, purpose):
#                 equip = frappe.get_doc("Equipment", equipment)
#                 equip.branch = branch
#                 equip.create_equipment_history(branch, posting_date, ref_doc, purpose)
#                 equip.save()
