# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Meeting(Document):
	def on_submit(self):
		# if not self.dispatch_number:
		# 	frappe.throw("Please mention a dispatch number for information and future references. Thank You.")
		self.send_mom()
		
	#notify members about the meeting
	def notify_members(self):
		subject = 'Meeting on ' + self.topic
		message = "The Meeting on '{0}' is created in the system for your kind perusal. Please provide your agendas or inputs/changes if any. The meeting ID is '{1}'. ".format(self.topic, self.name)
		sender = frappe.session.user
		
		for a in self.get('table_10'):
			try:
				frappe.sendmail(recipients=a.email_id,sender= sender,subject=subject,message= message)
			except frappe.OutgoingEmailError:
				pass
	
	#send the Minutes of the meeting to the members.
	def send_mom(self):
                subject = "Minutes of Meeting on" + self.topic
                message = "Find Attached the Minutes of the meeting on the '{0}'. Check ERP system for the same. The meeting ID is '{1}'.".format(self.topic, self.name)
		user = []
		user.append('jairajrai@gyalsunginfra.bt')
		for a in self.table_10:
			user.append(a.email_id)
                if user:
                        for a in user:
                                try:
                                        frappe.sendmail(recipients=a, sender=self.owner, subject=subject, message=message, attachments=[frappe.attach_print(self.doctype, self.name, file_name=self.name)], reference_doctype= self.doctype, reference_name= self.name)     
				except:
					pass


def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	if user == "Administrator":
		return

	return """(
		`tabMeeting`.owner = '{user}'
		or
		exists(select 1
			from `tabMeeting Member`
			where `tabMeeting Member`.parent = `tabMeeting`.name
			and `tabMeeting Member`.email_id = '{user}'
		)
	)""".format(user=user)



def has_record_permission(doc, user):
	if not user: user = frappe.session.user
	if user == "Administrator":
		return

	if doc.owner == user:
		return True
	elif frappe.db.exists("Meeting Member", {"parent":doc.name, "email_id": user}):
		return True
	else:
		return False 

