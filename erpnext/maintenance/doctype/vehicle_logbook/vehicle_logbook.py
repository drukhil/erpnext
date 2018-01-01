# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint

class VehicleLogbook(Document):
	def validate(self):
		self.check_hire_form()
		self.check_duplicate()
		self.calculate_totals()
		self.update_operator()	

	def on_update(self):
		if self.rate_type == 'With Fuel':
			self.calculate_balance()

	def on_submit(self):
		self.update_hire()
		self.check_tank_capacity()

	def check_hire_form(self):
		if self.ehf_name:
			docstatus = frappe.db.get_value("Equipment Hiring Form", self.ehf_name, "docstatus")
			if docstatus != 1:
				frappe.throw("Cannot create Vehicle Logbook without submitting Hire Form")
	
	def update_operator(self):
		self.equipment_operator = frappe.db.get_value("Equipment", self.equipment, "current_operator")

	def check_duplicate(self):		
		for a in self.vlogs:
			for b in self.vlogs:
				if a.date == b.date and a.idx != b.idx:
					frappe.throw("Duplicate Dates in Vehicle Logs in row " + str(a.idx) + " and " + str(b.idx))

	def calculate_totals(self):
		if self.vlogs:
			total_w = total_i = 0
			for a in self.vlogs:
				total_w += flt(a.work_time)
				total_i += flt(a.idle_time)
			self.total_work_time = total_w
			self.total_idle_time = total_i
		
		self.hsd_received = frappe.db.sql("select sum(qty) as qty from `tabConsumed POL` where equipment = %s and date between %s and %s and docstatus = 1 and pol_type = %s", (self.equipment, self.from_date, self.to_date, frappe.db.get_value("Equipment", self.equipment, "hsd_type")), as_dict=True)
		self.consumption = flt(self.other_consumption) + flt(self.consumption_hours) + flt(self.consumption_km)
		self.closing_balance = flt(self.hsd_received) + flt(self.opening_balance) - flt(self.consumption)

	def update_hire(self):
		if self.ehf_name:
			doc = frappe.get_doc("Equipment Hiring Form", self.ehf_name)
			doc.db_set("hiring_status", 1)
		e = frappe.get_doc("Equipment", self.equipment)

		if self.final_km:
			self.check_repair(cint(e.current_km_reading), cint(self.final_km))
			e.db_set("current_km_reading", flt(self.final_km))

		if self.final_hour:
			self.check_repair(cint(e.current_hr_reading), cint(self.final_hour))
			e.db_set("current_hr_reading", flt(self.final_hour))

	def calculate_balance(self):
		self.db_set("closing_balance", flt(self.opening_balance) + flt(self.hsd_received) - flt(self.consumption))

	def check_repair(self, start, end):
		et, em, branch = frappe.db.get_value("Equipment", self.equipment, ["equipment_type", "equipment_model", "branch"])
		interval = frappe.db.get_value("Hire Charge Parameter", {"equipment_type": et, "equipment_model": em}, "interval")
		if interval:
			for a in xrange(start, end):
				if (flt(a) % flt(interval)) == 0:
					manager = frappe.db.get_value("Branch Fleet Manager", branch, "manager")
					if not manager:
						frappe.msgprint("Setup the fleet manager in Branch Fleet Manager")
					email = frappe.db.get_value("Employee", manager, "user_id")
					subject = "Regular Maintenance for " + str(self.equipment)
					message = "It is time to do regular maintenance for equipment " + str(self.equipment) + " since it passed the hour/km reading of " + str(a) 
					if email:
						try:
							frappe.sendmail(recipients=email, sender=None, subject=subject, message=message)
						except:
							pass
					break

	def check_tank_capacity(self):
		em = frappe.db.get_value("Equipment", self.equipment, "equipment_model")
		tank = frappe.db.get_value("Equipment Model", em, "tank_capacity") 
		if tank:
			if flt(tank) < flt(self.closing_balance):
				frappe.msgprint("Closing balance cannot be greater than the tank capacity (" + str(tank) + ")")


@frappe.whitelist()
def get_opening(equipment, from_date, to_date, pol_type):
	if not pol_type:
		frappe.throw("Set HSD type in Equipment")

	closing = frappe.db.sql("select closing_balance from `tabVehicle Logbook` where docstatus = 1 and equipment = %s and rate_type = 'With Fuel' and to_date <= %s order by to_date desc limit 1", (equipment, from_date), as_dict=True)

	qty = frappe.db.sql("select sum(qty) as qty from `tabConsumed POL` where equipment = %s and date between %s and %s and docstatus = 1 and pol_type = %s", (equipment, from_date, to_date, pol_type), as_dict=True)

	c_km = frappe.db.sql("select final_km from `tabVehicle Logbook` where docstatus = 1 and equipment = %s and to_date <= %s order by to_date desc limit 1", (equipment, from_date), as_dict=True)

	c_hr = frappe.db.sql("select final_hour from `tabVehicle Logbook` where docstatus = 1 and equipment = %s and to_date <= %s order by to_date desc limit 1", (equipment, from_date), as_dict=True)
	result = []
	if closing:
		result.append(closing[0].closing_balance)
	else:
		result.append(0)

	if qty:
		result.append(qty[0].qty)
	else:
		result.append(0)

	if c_km:
		result.append(c_km[0].final_km)
	else:
		result.append(0)

	if c_hr:
		result.append(c_hr[0].final_hour)
	else:
		result.append(0)

	return result
		
