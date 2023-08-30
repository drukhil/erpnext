# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr, flt

class ExpenseAllocation(Document):
	def validate(self):
		if self.items:
			total = 0
			for d in self.items:
				total += flt(d.amount)
				self.total_amount= total
