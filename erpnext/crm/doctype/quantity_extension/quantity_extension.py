# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt
from frappe.model.document import Document
from erpnext.crm.doctype.site.site import site_active
from frappe.core.doctype.user.user import send_sms

class QuantityExtension(Document):
	def validate(self):
		self.validate_mandatory()
		self.validate_items()
		self.update_user_details()
		self.validate_duplciate_request()

	def on_submit(self):
		self.update_site()
		self.sendsms()

	def on_cancel(self):
		self.update_site()
	
	def validate_duplciate_request(self):
		if frappe.db.exists("Quantity Extension",{"user":self.user,"approval_status":"Pending", "site":self.site}):
			frappe.throw("Quantity Extension already requested and still Pending")

	def sendsms(self,msg=None):
		if self.docstatus == 1:
			if self.approval_status == "Rejected":
				msg = "Your request for Quantity Extension is {0}. Tran Ref No {1}. {2}".format(str(self.approval_status).lower(),self.name,self.rejection_reason)	
			else:
				msg = "Your request for Quantity Extension is {0}. Tran Ref No {1}".format(str(self.approval_status).lower(),self.name)	
		mobile_no = frappe.db.get_value("User", self.user, "mobile_no")
		if mobile_no:
			send_sms(mobile_no, msg)

	def validate_mandatory(self):
		if self.approval_status == "Rejected" and not self.rejection_reason:
			frappe.throw(_("<b>Rejection Reason</b> is mandatory"))
		else:
			if not cint(site_active(self.site)):
				frappe.throw(_("Extension not permitted as the Site is already deactivated"))

	def update_user_details(self):
		if frappe.db.exists("User Account", self.user):
			doc = frappe.get_doc("User Account", self.user)
			self.full_name = doc.full_name
			self.mobile_no = doc.mobile_no
			self.alternate_mobile_no = doc.alternate_mobile_no

	def validate_items(self):
		count = 0
		total_quantity = 0
		for i in self.get("items"):
			count += 1

			# Commented by SHIV on 2020/08/03
			# To allow negative quantity in order to allow quantity adjustment as the back office
			# 	users approve mistakenly some times 

			#if flt(i.additional_quantity) < 0:
			#	frappe.throw(_("Row#{0} : <b>Additional Quantity</b> cannot be a negative value").format(i.idx))

			if not i.site_item_name:
				frappe.throw(_("Row#{0} : <b>Site Item Name</b> not found").format(i.idx))
			initial_quantity = frappe.db.get_value("Site Item", i.site_item_name, "overall_expected_quantity")

			i.initial_quantity = flt(initial_quantity)
			i.final_quantity   = flt(initial_quantity) + flt(i.additional_quantity)
			total_quantity    += flt(i.additional_quantity) 

		if count and not flt(total_quantity):
			frappe.throw(_("You must extend quantity for any one item"))

	def update_site(self):
		""" update Site Item quantity """
		if self.approval_status == "Rejected":
			return
		elif self.approval_status == "Pending":
			frappe.throw(_("Request cannot be submitted in <b>Pending</b> status"))
		#elif not self.approval_document:
		#	frappe.throw(_("Please attach <b>Quantity Extension Approval Document</b>"))
	
		for i in self.get("items"):
			doc = frappe.get_doc("Site Item", i.site_item_name)
			extended_quantity = -1*flt(i.additional_quantity) if self.docstatus == 2 else flt(i.additional_quantity)

			# check for negative quantity adjustment
			if flt(extended_quantity) < 0 and (flt(doc.balance_quantity)+flt(extended_quantity)) < 0:
				frappe.throw(_("Row#{}: Quantity adjustment cannot be beyond the available balance {}").format(i.idx,flt(doc.balance_quantity)))

			doc.overall_expected_quantity = flt(doc.expected_quantity) + flt(doc.extended_quantity) + flt(extended_quantity)
			doc.balance_quantity = flt(doc.expected_quantity) + flt(doc.extended_quantity) + flt(extended_quantity) - flt(doc.ordered_quantity)
			doc.extended_quantity         = flt(doc.extended_quantity) + flt(extended_quantity)
			doc.save(ignore_permissions=True)
