# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AssignBranch(Document):
	def validate(self):
		self.assign_name()	
		self.check_mandatory()
		self.check_employee_duplicate()
		self.check_duplicate()


	def check_mandatory(self):
		if not self.user:
			frappe.throw("User Id is Mandatory")	

	def on_update(self):
		self.assign_branch()
	
	def assign_name(self):
		if self.employee:
			emp = frappe.get_doc(self.employee_type, self.employee)
			self.user = emp.user_id
			self.current_branch = emp.branch
		#else:
		#frappe.throw("Employee ID is Mandatory")

	def check_employee_duplicate(self):
		docs = frappe.db.sql("select name from `tabAssign Branch` where employee = %s and user = %s and name != %s", (self.employee, self.user, self.name), as_dict=True)
		if docs:
			frappe.throw("The Employee has been already assigned Branch through <b>" + str(docs[0].name) + "</b>")

	def check_duplicate(self):
		to_remove = []		
		for a in self.items:
			for b in self.items:
				if a.branch == b.branch and a.idx != b.idx:
					#to_remove.append(list(a))
					self.remove(a)
        				#[self.remove(a) for a in to_remove]
					#frappe.throw("Duplicate Entries in row " + str(a.idx) + " and " + str(b.idx))

	def assign_branch(self):
		#Clear user branch permissions 
		user_perms = frappe.defaults.get_user_permissions(self.user)
		for doc, names in user_perms.items():
			if doc == 'Branch':
				for a in names:
					pass
					#frappe.permissions.remove_user_permission(doc, a, self.user)

		#Add the branch permissions back as per assigned branches
                if self.action == 'Remove':
                        frappe.permissions.remove_user_permission("Branch", self.current_branch, self.user)
                        for a in self.items:
                                frappe.permissions.remove_user_permission('Branch', a.branch, self.user)

                        frappe.msgprint("Branch Removed")

                if self.action == 'Add':
                        frappe.permissions.add_user_permission("Branch", self.current_branch, self.user)
                        for a in self.items:
                                frappe.permissions.add_user_permission('Branch', a.branch, self.user)

                        frappe.msgprint("Branch Assigned")

	#Populate branches with active branches 
	def get_all_branches(self):
		query = """ select b.name as branch from tabBranch b, `tabCost Center` c where b.name = c.branch and b.is_disabled != 1"""
		if self.parent_cc:
			query += " and c.parent = '{0}'".format(self.parent_cc)

		entries = frappe.db.sql(query, as_dict=True)
		self.set('items', [])
		
		for d in entries:
			row = self.append('items', {})
			row.update(d)
