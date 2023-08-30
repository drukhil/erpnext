# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class DesignWeightage(Document):
	def validate(self):
		self.update_weightage()

	def update_weightage(self):
		total_weightage = 0.0
		for a in self.get("items"):
			if flt(a.weightage) > 100:
				frappe.throw(" Weightage Cannot exceed 100")
			if flt(a.weightage) < 0:
				frappe.throw(" Weightage Cannot be less then zero")
			total_weightage += round(flt(a.weightage), 3)
		self.total_weightage = round(total_weightage, 3)

	def on_submit(self):
		if self.total_weightage != 100:
			frappe.throw("Total Weightage does not add up to 100, do change the weightage to make it 100")
