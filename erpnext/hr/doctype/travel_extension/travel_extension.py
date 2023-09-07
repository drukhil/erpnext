# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import add_days, date_diff
from frappe.utils import getdate,datetime
import re

class TravelExtension(Document):
	def autoname(self):
		now = datetime.datetime.now()
		year = datetime.datetime.strftime((now),"%y")
		month = datetime.datetime.strftime((now),"%m")
		naming_code = "TE"+year+month
		latest_name = frappe.db.sql("select name from `tabTravel Extension` order by name desc limit 1",as_dict=True)
		if not latest_name:
			self.name = naming_code+"00001"
		else:
			num=[]
			num = [int(s) for s in re.findall(r"\d+",latest_name[0].name)]  	
			self.name = "TE"+str(num[0]+1)

	def validate(self):
		self.validate_travel_authorization()
		self.extension_date()

	def extension_date(self):
		if not self.new_travel_item:
			frappe.throw("There are no dates for the original travel authorization!")
		
		# original_end_date= ""
		# for index, item in enumerate(self.items):
		# 	if index+1 == len(self.items):
		# 		original_end_date = item.till_date

		# for item in self.new_travel_item:
		# 	if item.date < original_end_date:
		# 		frappe.throw("Travel extension date cannot be before the original travel date at line: {} in new travel addition".format(item.idx))

	def on_submit(self):
		self.validate_travel_dates()
		self.update_travel_authorization()
	
	##
	#Ensure the dates are consistent
	##
	def validate_travel_dates(self):
		for idx, item in enumerate(self.get("new_travel_item")):
			if item.halt:
				if not item.till_date:
					frappe.throw(_("Row#{0} : Till Date is Mandatory for Halt Days.").format(item.idx),title="Invalid Date")
			else:
				if not item.till_date:
					item.till_date = item.date

			if idx:
				if item.date != add_days(self.new_travel_item[idx-1].till_date, 1):
					frappe.throw(_("<b>From Date</b> {0} on line {1} might be wrongly typed. It should have been {2}. Kindly check and submit again").format(item.date, item.idx, add_days(self.new_travel_item[idx-1].till_date, 1)), title="Invalid Date")

	def validate_travel_authorization(self):
		existing = frappe.db.sql("""
			select name from `tabTravel Extension` where workflow_state in ('Waiting Supervisor Approval') and travel_authorization = '{}' limit 1
		""".format(self.travel_authorization), as_dict = 1)
		if existing:
			frappe.throw("""Submitted Travel Extension for Travel Authorization <b><a href="#Form/Travel%20Authorization/{0}">{0}</a></b> already exists. Please create new Travel Authorization.<br>Submitted Travel Extension: <b><a href="#Form/Travel%20\Extension/{1}">{1}</a></b>""".format(self.travel_authorization,existing[0].name))

    
	def update_travel_authorization(self):
		# child_table_name = frappe.db.sql("select name from `tabTravel Authorization Item` where parent='{}'".format(self.travel_authorization))
		# doc = frappe.get_doc("Travel Authorization", self.travel_authorization)

		#checking for existing submitted travel extension for the selected travel authorization
		for item in self.new_travel_item:
			taItem = frappe.get_doc({
				"doctype": 'Travel Authorization Item Log',
				"parenttype": 'Travel Authorization',
				"parentfield": 'travel_extension_log',
				"idx": item.idx,
				"parent": self.travel_authorization,
				"date": item.date,
				"till_date": item.till_date,
				"halt" : item.halt,
				"halt_at": item.halt_at,
				"from_place": item.from_place,
				"to_place": item.to_place,
				"reference_type": "Travel Extension",
				"reference_name": self.name
			})
			taItem.insert()
		frappe.db.sql("delete from `tabTravel Authorization Item` where parent = %s", (self.travel_authorization))
		
		for item in self.new_travel_item:
			taItem = frappe.get_doc({
				"doctype": 'Travel Authorization Item',
				"parenttype": 'Travel Authorization',
				"parentfield": 'items',
				"idx": item.idx,
				"parent": self.travel_authorization,
				"date": item.date,
				"till_date": item.till_date,
				"halt" : item.halt,
				"halt_at": item.halt_at,
				"from_place": item.from_place,
				"to_place": item.to_place
			})
			taItem.insert()

		frappe.msgprint("Done")