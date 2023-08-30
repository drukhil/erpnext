# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import now, now_datetime

class IssueList(Document):
	def validate(self):
                if self.status == 'Close':
			try:
				doc = frappe.get_doc("Employee", {'user_id': frappe.session.user})
			except:
				frappe.throw("User Id is not link with Employee, Kindly contact Administrator")
				
                        self.resolved_by = doc.name
			self.resolved_by_name = doc.employee_name
			self.resolver = frappe.session.user
			self.designation = doc.designation
			self.contact = doc.phone_number 
                        frappe.db.sql(""" update `tabIssue List` set docstatus = 1 where name ='{0}'""".format(self.name))
                        frappe.msgprint("Thanks, This issue is closed!")
                        self.db_set("docstatus", 1)
			self.db_set("workflow_state", "Resolved")
			frappe.sendmail(recipients= self.owner, sender='ERP System', subject="Ticket Resolved" , message="Your Ticket No {0} is closed.".format(self.name))
                if not self.requested_by:
			doc = frappe.get_doc("Employee", {'user_id': frappe.session.user})
                        self.requested_by = doc.name
                self.last_update = now_datetime()
                if self.workflow_state == 'New':
			self.notify_ctm()
		#To add comment based on use message
		#self.add_comment('Comment', text='Test Comment tashi')
	
	def notify_ctm(self):
                subject = "ERP Issue Management"
                message = "Issue({1}) Related to <b> {0} </b>  Module is raised in the System,  Check ERP system for details".format(self.module, self.name)
		user = []
		user.append('jigme@gyalsunginfra.bt')
		module_user = frappe.get_doc("Support Module", self.module).module_ctm
		user.append(module_user)
                if user:
                        for a in user:
                                try:
                                        frappe.sendmail(recipients=a, sender=None, subject=subject, message=message)
                                except:
                                        pass


	def get_series(self):
		self.add_comment('Comment', text= self.remarks)
		frappe.msgprint("Ticket updated!")
