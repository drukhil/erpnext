# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, date_diff

class VehicleRequisition(Document):
	def validate(self):
		self.validate_dates()

	def on_submit(self):
		self.notify_all()


	def validate_dates(self):
		if self.head > 4:
			frappe.throw("Only one vehicle will be assigned for 4 passenger, For more than 4 passenger(No of Heads), kindly apply for another vehicle requisition. ")
		if self.head > 1:
			if not self.items:
				frappe.throw("Kindly fill in your travel companions under the <b> Companion Officials </b> section.")
		if getdate(self.travel_date) > getdate(self.return_date):
			frappe.throw("Travel Start Date Cannot be after Travel Return Date. Kindly check the travel dates.")


	def notify_all(self):
                subject = "Vehicle Requisition" + self.name
                message = """ Dear '{0}' - Phone #({1}), <br> 
				Your Vehicle Requisition '{2}' is approved. Mr '{3}' with vehicle '{4}' is assigned for this tour from '{5}' to '{6}'. His phone number is '{7}'. Have a nice trip.....""".format(self.employee_name, self.phone_number,  self.name, self.driver_name, self.equipment_number,self.travel_date, self.return_date, self.driver_phone)
				
		user = []
		users = ['dorjiphurba@gyalsunginfra.bt', 'gmpa@gyalsunginfra.bt','hr@gyalsunginfra.bt', self.email_id, self.driver_email ]
		user.extend(users)
		
       		if user:
            		for a in user:
                		try:
                    			frappe.sendmail(recipients=a, sender=self.owner, subject=subject, message=message, reference_doctype= self.doctype, reference_name= self.name)     
				except:
					pass


def has_record_permission(doc, user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)
	
	if "Fleet Manager" in user_roles:
		return True
	else:
		if frappe.db.exists("Employee", {"name":doc.employee, "user_id": user}):
			return True
		else:
			return False 

	return True

@frappe.whitelist()
def calculate_durations(from_date = None, to_date = None):
	
	duration = date_diff(to_date, from_date) + 1 
	return duration