# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class GCELeaveCancellation(Document):
	
	def on_submit(self):
		for row in self.get("items"):
			if row.employee:
				frappe.db.sql("""
					update  `tabEmployee` set casual_leave_allocated=0 where name='{}'
				""".format(row.employee))
			else:
				frappe.throw("Need to enter Employee")
