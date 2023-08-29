# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, date_diff, nowdate
from frappe.core.doctype.user.user import send_sms
from erpnext.crm_utils import add_user_roles, remove_user_roles
from frappe.model.mapper import get_mapped_doc

class TransportRequest(Document):
	def validate(self):
		#remove space in vehicle no
		v_no = self.vehicle_no
		self.vehicle_no = v_no.replace(" ","")
		
		#make status same with approval Status
		self.status = self.approval_status

		self.map_user_transport()
		self.request_date = getdate(nowdate())
		self.validate_vehicle()
		if self.is_boulder == 0:
			self.attach_cid()


	def map_user_transport(self):
		#if not self.user:
			#account_type = frappe.db.get_value("User", frappe.session.user, "account_type")
			#if account_type == "CRM":
			#	self.user = frappe.session.user
			
		if self.common_pool:
			self.add_user_roles()
			if not self.transporter_name:
				self.transporter_name = frappe.db.get_value("User", self.user, "first_name")

	'''
	def check_duplicate(self):
		if self.vehicle_no and self.approval_status == "Approved":
			vehicle_number = self.vehicle_no
			vehicle_last_four_digit = vehicle_number[-4:]
			check = 0
			if self.common_pool:
				for a in frappe.db.sql("select name, vehicle_status from `tabVehicle` where name like '%{0}'".format(vehicle_last_four_digit), as_dict=True):
					frappe.msgprint("Vehicle with similar number " + a.name + " status " + a.vehicle_status + " is already registered")
					check += 1
			if check > 0:
				frappe.throw("There are vehicle already registered with similar number to {0}".format(self.vehicle_no))
	'''

	def validate_vehicle(self):
		# if not self.vehicle_capacity or not self.vehicle_owner or not self.owner_cid:
		# 	frappe.throw("Vehicle Owner, Owner CID and Vehicle Capacity are mandatory"+str(self.is_boulder))
		self.vehicle_no = self.vehicle_no.upper()
		sand_vehicle = None
		vehicle = self.vehicle_no
		cond = "upper(vehicle_no)"
		for x in [' ', '+', '-', '(', ')', '/', '#']:
			vehicle = vehicle.replace(x, '')
			cond = "replace({},'{}','')".format(cond, x)
		cond1 = cond + " = '{}'".format(vehicle)
		cond += " like '%{}%'".format(vehicle)
		
		if self.is_boulder == 0:
			vehicle_dtl = frappe.db.sql("""select name, user from `tabTransport Request` 
				where {}
				and approval_status in ('Pending', 'Approved') 
				and name!= '{}' and is_boulder = 0 and docstatus != 2
			""".format(cond, self.name), as_dict = True)
		else:
			vehicle_dtl = frappe.db.sql("""select name, user from `tabTransport Request` 
				where {}
				and approval_status in ('Pending', 'Approved') 
				and name!= '{}' and is_boulder = 1 and docstatus != 2
			""".format(cond, self.name), as_dict = True)
			
			if not vehicle_dtl:
				sand_vehicle = frappe.db.sql("""select name, user from `tabTransport Request` 
					where {}
					and approval_status in ('Pending', 'Approved') 
					and name!= '{}' and is_boulder = 0 and docstatus != 2
				""".format(cond, self.name), as_dict = True)
			
		if vehicle_dtl:
			if not sand_vehicle:
				for a in vehicle_dtl:
					r_user = a.user
				frappe.throw("Vehicle {0} is already in Transport Request with User {1} {2}".format(self.vehicle_no, r_user, str(vehicle_dtl)))
		similar_vehicle_count = 0

		for a in frappe.db.sql("""select count(*) as similar_count from `tabVehicle`
					   where {} and docstatus != 2
					""".format(cond1), as_dict=True):
			similar_vehicle_count = a.similar_count
		if similar_vehicle_count > 0:
			for b in frappe.db.sql("""select name, vehicle_status, user, vehicle_no from `tabVehicle`
						   where {} and docstatus != 2
						""".format(cond1), as_dict=True):
				if b.vehicle_status != "Deregistered" and b.user and b.user != self.user:
					frappe.throw("Vehicle is already registered with status {0}".format(b.vehicle_status))
				if self.approval_status == "Approved" and self.docstatus == 1 and not sand_vehicle:
					frappe.db.sql("""
					Update `tabVehicle` set
					vehicle_capacity = '{0}', common_pool = '{1}', self_arranged = '{2}', is_boulder = '{8}',
					drivers_name = '{3}', owner_cid = '{4}', contact_no = '{5}', user = '{6}',
					vehicle_status = 'Active', docstatus = 1 
					where name = '{7}'
					""".format(self.vehicle_capacity, self.common_pool, self.self_arranged, self.drivers_name, self.owner_cid, self.contact_no, self.user, b.name, self.is_boulder))
					frappe.msgprint("Vehicle already exist and details are updated as per request for vehicle {}".format(b.name))
				elif self.approval_status == "Approved" and self.docstatus == 1 and sand_vehicle:
					frappe.db.sql("""
					Update `tabVehicle` set
					is_boulder = '{4}',
					drivers_name = '{0}', contact_no = '{1}', user = '{2}',
					vehicle_status = 'Active', docstatus = 1 
					where name = '{3}'
					""".format(self.drivers_name, self.contact_no, self.user, b.name, self.is_boulder))
					frappe.msgprint("Vehicle already exist and details are updated as per request for vehicle {}".format(b.name))
		else:
			if self.approval_status == "Approved" and self.docstatus == 1:
				v_doc = frappe.new_doc("Vehicle")
				v_doc.vehicle_no = self.vehicle_no
				v_doc.common_pool = self.common_pool
				v_doc.self_arranged = self.self_arranged
				v_doc.is_boulder = self.is_boulder
				if self.is_boulder == 0:
					v_doc.vehicle_capacity = self.vehicle_capacity
					v_doc.owner_cid = self.owner_cid
				v_doc.drivers_name = self.drivers_name
				v_doc.contact_no = self.contact_no
				v_doc.user = self.user
				v_doc.submit()

		if not self.common_pool:
			if not self.self_arranged and self.is_boulder == 0:
				frappe.throw("The transport request should be either Common Pool or Self Owned")
		
	def add_user_roles(self):
		""" add role `CRM Transporter` """
		add_user_roles(self.user, "CRM Transporter")

	def on_submit(self):
#		if not self.registration_document:
#			frappe.throw("Please attach vehicle registration document")
		#if self.owner == "Spouse":
		#	if not self.marriage_certificate:
		#		frappe.throw("You must attach MC copy as the vehicle is registered on your spouse name")
					
		if self.approval_status == "Pending":
			frappe.throw("Change the Approval Status other than Pending to submit ")

		if self.approval_status == "Approved":
			self.create_transporter_vehicle()
		self.sendsms()


	def attach_cid(self):
		target_doc = None
		def set_missing_values(source, target):
			target.attached_to_doctype = self.doctype
			target.attached_to_name = self.name

		''' attach documents '''
		file = frappe.db.sql("""
			select 
				f.name file, ur.name user_request,
				f.attached_to_doctype, f.attached_to_name, f.file_name, f.file_url 
			from `tabUser Request` ur, `tabFile` f
			where ur.user	 	  = "{user}"
			and ur.request_category   = "CID Details" 
			and ur.docstatus 	  = 1
			and f.attached_to_doctype = "User Request"
			and f.attached_to_name 	  = ur.name
			order by ur.modified desc
			limit 1
		""".format(user=self.user),as_dict=True)
		if file and not frappe.db.exists("File", {"attached_to_doctype": self.doctype, "attached_to_name": self.name, "file_url": file[0].file_url}):
			attachment = get_mapped_doc("File", file[0].file, {
					"File": {
						"doctype": "File",
					},
			}, target_doc, set_missing_values, ignore_permissions=True)
			attachment.save(ignore_permissions=True)

	def sendsms(self,msg=None):
		if self.docstatus == 1:
			msg = "Your request for Transport Registration is {0}. Tran Ref No {1}".format(str(self.approval_status).lower(),self.name)
		mobile_no = frappe.db.get_value("User", self.user, "mobile_no")
		if mobile_no:
			send_sms(mobile_no, msg)

	def create_transporter_vehicle(self):
		u_mobile_no = frappe.db.get_value("User", {"login_id":self.user}, "mobile_no")
		transporter = ""
		if self.common_pool:
			if not frappe.db.exists("Transporter", {"transporter_id": self.user, "docstatus": ("<",2)}):
				doc = frappe.new_doc("Transporter")
				if frappe.db.exists("Transporter", {"transporter_name": self.transporter_name}):
					transporter_name = self.transporter_name + "(" + self.user + ")"
				else:
					transporter_name = self.transporter_name

				doc.transporter_name = transporter_name
				doc.transporter_id = self.user
				doc.mobile_no = u_mobile_no
				doc.user = self.user		
				doc.submit()
	
			transporter, enabled = frappe.db.get_value("Transporter", {"transporter_id": self.user}, ["transporter_name", "enabled"])
			doc = frappe.get_doc("Transporter", {"transporter_id": self.user})
			self.db_set("transporter", doc.name)
	
	def change_to_draft(self):
		frappe.db.sql("update `tabTransport Request` set docstatus=0 where name = '{}'".format(self.name))
		frappe.db.commit()
						
