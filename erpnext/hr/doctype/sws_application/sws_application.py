# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from datetime import datetime
from dateutil.relativedelta import relativedelta
from erpnext.custom_workflow import validate_workflow_states

class SWSApplication(Document):

	
	def validate(self):
		validate_workflow_states(self)
		# self.get_status()
		# self.validate_save()
		self.validate_dead()
		self.validate_amount()
		if self.workflow_state == "Approved":
			self.docstatus = 1
			self.approval_status = "Approved"
				
	def validate_amount(self):
		total_amount = 0
		for a in self.items:
			if not a.amount:
				a.amount = a.claim_amount
			total_amount = flt(total_amount) + flt(a.amount)	
		self.total_amount = total_amount

	def validate_dead(self):
		for a in self.items:
			doc = frappe.get_doc("SWS Membership Item", a.reference_document)
			if doc.deceased == 1:
				frappe.throw("The dependent is marked deceased in Membership and Employee Family Detail. Please contact HR Section")

	# def before_submit(self):
	# 	self.get_status()

	def on_submit(self):
		if self.total_amount <= 0:
			frappe.throw("Total Amount cannot be 0 or less")
		self.verify_approvals()
		self.update_status()
		self.post_sws_entry()
		# added by Kinley Dorji 2021/06/11
		salary_structure = frappe.get_doc("Salary Structure",{"employee":self.employee,"is_active":'Yes'})
		salary_structure.save(ignore_permissions = True)
	
	def verify_approvals(self):
		if not self.verified:
			frappe.throw("Cannot submit unverified application")
		if self.approval_status != "Approved":
			frappe.throw("Can submit only Approved application")

	def update_status(self):
		for a in self.items:
			if frappe.db.get_value("SWS Event", a.sws_event, "deceased"):
				doc = frappe.get_doc("Employee Family Details", a.reference_document)
				swsdoc = frappe.get_doc("SWS Membership Item", a.reference_document)
				if self.docstatus == 1:
					doc.db_set("dead", 1)
					swsdoc.db_set("deceased", 1)
				if self.docstatus == 2:
					doc.db_set("dead", 0)
					swsdoc.db_set("deceased", 0)
			row = frappe.get_doc("SWS Membership Item", a.reference_document)
			if self.docstatus == 1:
				row.status = 'Claimed'
				row.claim_amount = self.total_amount
				row.sws_application = self.name
			if self.docstatus == 2:
				row.status = 'Active'
				row.claim_amount = None
				row.sws_application = None
			row.save(ignore_permissions = True)

	def post_sws_entry(self):
		doc = frappe.new_doc("SWS Entry")
		doc.flags.ignore_permissions = 1
		doc.posting_date = self.posting_date
		doc.branch = self.branch
		doc.ref_doc = self.name
		doc.company = self.company
		doc.employee = self.employee
		doc.debit = self.total_amount
		doc.submit()

	def before_cancel(self):
		self.reset_status()

	def on_cancel(self):
		self.update_status()
		self.delete_sws_entry()

	def reset_status(self):
		self.verified = 0
		self.approval_status = None

	def delete_sws_entry(self):
		frappe.db.sql("delete from `tabSWS Entry` where ref_doc = %s", self.name)

@frappe.whitelist()
def get_event_amount(sws_event, reference, employee, relation):
	if not reference:
		frappe.throw("Please select Reference Document")
	parent_document = frappe.db.get_value("SWS Membership Item", reference, "parent")
	# relationship = frappe.db.get_value("SWS Membership Item", reference, "relationship")
	# relationship_type = frappe.db.get_value("Relationship", relationship, "relationship_type")
	# date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
	registration_date = frappe.db.get_value("SWS Membership", parent_document, "registration_date")
	# if relationship_type == "Immediate":
	# 	d1 = datetime.strptime(str(date_of_joining),'%Y-%m-%d')
	# else:
	# d1 = datetime.strptime(str(registration_date),'%Y-%m-%d')
	# d2 = datetime.strptime(frappe.utils.nowdate(), '%Y-%m-%d')
	# date_diff = relativedelta(d2,d1).years
	# frappe.msgprint(str(date_diff))
	if relation == 'Self':
		event_amount = frappe.db.sql("""
                    select amount from `tabSWS Event Item` where parent = '{0}' and member = 'Self'
                               """.format(sws_event), as_dict = True)
	# elif date_diff > 1 and date_diff <= 2:
	# 	event_amount = frappe.db.sql("""
    #                 select amount from `tabSWS Event Item` where parent = '{0}' and noof_years = 'Within 2 years'
    #                            """.format(sws_event), as_dict = True)
	# elif date_diff > 2 and date_diff <= 3:
	# 	event_amount = frappe.db.sql("""
    #                 select amount from `tabSWS Event Item` where parent = '{0}' and noof_years = 'Within 3 years'
    #                            """.format(sws_event), as_dict = True)
	# elif date_diff > 3 and date_diff <= 4:
	# 	event_amount = frappe.db.sql("""
    #                 select amount from `tabSWS Event Item` where parent = '{0}' and noof_years = 'Within 4 years'
    #                            """.format(sws_event), as_dict = True)
	else:
		event_amount = frappe.db.sql("""
                    select amount from `tabSWS Event Item` where parent = '{0}' and member = 'Members'
                               """.format(sws_event), as_dict = True)

	return event_amount

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabSWS Application`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabSWS Application`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabSWS Application`.supervisor = '{user}' and `tabSWS Application`.workflow_state != 'Draft')
	)""".format(user=user)