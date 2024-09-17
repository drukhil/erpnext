# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
class EmployeeSeparationClearance(Document):
	def validate(self):
		self.check_duplicates()
		self.check_reference()
		if self.approvers_set == 0:
			self.set_approvers()
	def autoname(self):
		abb = "ESC"
		self.name = make_autoname(str(abb) + './.YYYY./.#####.')
	# def apply(self):
	# 	if self.mail_sent == 0:
	# 		msg = self.notify_approvers()
	# 	return msg

	def on_submit(self):
		self.check_signatures()
		self.update_reference()
		# self.notify_employee()
		self.update_seperation_clearence_reference()
		self.update_update_employee()

	def on_cancel(self):
		self.update_reference()
		# self.notify_employee()
		self.update_seperation_clearence_reference()
		self.update_update_employee(cancel=True)
  
	def update_seperation_clearence_reference(self):
		reference = frappe.db.get_value("Employee Separation", self.employee_separation_id, "separation_clearance")
		if not reference:
			frappe.db.set_value("Employee Separation", self.employee_separation_id,"separation_clearance", self.name)
		else:
			frappe.db.set_value("Employee Separation", self.employee_separation_id,"separation_clearance", "")
	
	def update_update_employee(self, cancel=False):
		if not cancel:
			# relieving_date = frappe.db.get_value("Employee Separation",self.employee_separation_id, "separation_date")
			# reason_for_resignation =frappe.db.get_value("Employee Separation",self.employee_separation_id, "reason_for_resignation")
			id = frappe.get_doc("Employee",self.employee)
			id.status = 'Left'
			id.relieving_date = self.separation_date
			id.reason_for_resignation = self.reason_for_resignation
			id.save()
		else:
			id = frappe.get_doc("Employee",self.employee)
			id.status = 'Active'
			id.relieving_date = ''
			id.reason_for_resignation = ''
			id.save()

	def check_signatures(self):
		if self.supervisor_clearance == 0:
			frappe.throw("Supervisor {} has not granted clearance.".format(self.supervisor))
		if self.finance_clearance == 0:
			frappe.throw("Finance Manager {} has not granted clearance.".format(self.fd))
		if self.erp_clearance == 0:
			frappe.throw("ERP Approver {} has not granted clearance.".format(self.erp))
		if self.hra_clearance == 0:
			frappe.throw("HR Approver {} has not granted clearance.".format(self.hra))
		if self.adm_clearance == 0:
			frappe.throw("Asset Administrator {} has not granted clearance.".format(self.adm))

	def update_reference(self):
		id = frappe.get_doc("Employee Separation",self.employee_separation_id)
		id.clearance_acquired = 1 if self.docstatus == 1 else 0
		id.save()

	def check_reference(self):
		if not self.employee_separation_id:
			frappe.throw("Employee Separation Clearance creation should route through Employee Separation Document.",title="Cannot Save")

	def check_duplicates(self):
		duplicates = frappe.db.sql("""
			select name from `tabEmployee Separation Clearance` where employee_separation_id = '{0}'  and name != '{1}' and docstatus != 2
				""".format(self.employee_separation_id,self.name))
		if duplicates:
			frappe.throw("There is already a pending Separation Clearance created for the Employee Separation '{}'".format(self.employee_separation_id))
	
	def check_logged_in_user_role(self):
		#return values initialization-----------------
		display = 1
		supervisor = 1
		erp = 1
		fd = 1
		hra = 1
		adm = 1 

		#----------------------------Supervisor------------------------------------------------------------------------------------------------------------------------------------------------------------|
		if frappe.session.user == self.supervisor:
			supervisor = 0
		#----------------------------Finance Manager-----------------------------------------------------------------------------------------------------------------------------------------------------|
		if frappe.session.user == self.fd:
			fd = 0
		#----------------------------Infra Unit-----------------------------------------------------------------------------------------------------------------------------------------------------|
		if frappe.session.user == self.erp:
			erp = 0
		#----------------------------Procurement Approver-----------------------------------------------------------------------------------------------------------------------------------------------------|
		if frappe.session.user == self.hra:
			hra = 0
		#----------------------------Asset Administrator Approver-----------------------------------------------------------------------------------------------------------------------------------------------------|
		if frappe.session.user == self.adm:
			adm = 0
		return supervisor, fd, erp, hra, adm 

	
	def set_approvers(self):
		# frappe.throw(self.employee)
		#----------------------------Supervisor------------------------------------------------------------------------------------------------------------------------------------------------------------|
		self.supervisor = frappe.db.get_value("Employee",frappe.db.get_value("Employee",self.employee,"reports_to"),"user_id")
		#--------------------------- Finance Manager-----------------------------------------------------------------------------------------------------------------------------------------------------|
		self.fd = frappe.db.get_value("Employee", frappe.db.get_single_value("HR Settings", "fa_approver"), "user_id")
		#--------------------------- HR Approver-----------------------------------------------------------------------------------------------------------------------------------------------------|
		self.hra = frappe.db.get_value("Employee", frappe.db.get_single_value("HR Settings", "hr_approver"), "user_id")
		#--------------------------- ERP Approver-----------------------------------------------------------------------------------------------------------------------------------------------------|
		self.erp = frappe.db.get_value("Employee", frappe.db.get_single_value("HR Settings", "erp_approver"), "user_id")
		#--------------------------- Administrator Approver---------------------------------------------------------------------------------------------------------------------------------|
		self.adm = frappe.db.get_value("Employee", frappe.db.get_single_value("HR Settings", "aa_approver"), "user_id")
		self.db_set("approvers_set",1)


def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabEmployee Separation Clearance`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabEmployee Separation Clearance`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabEmployee Separation Clearance`.supervisor = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.fd = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.erp = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.hra = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.adm = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)

	)""".format(user=user)
