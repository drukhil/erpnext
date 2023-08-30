# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class UnfreezeOAP(Document):
	def validate(self):
		abc = """select docstatus, status from `tabOpen Air Prisoner` where name = '{}' """.format(self.oap)
		entry = frappe.db.sql(abc, as_dict=True)
		for a in entry:
			if a.status != 'Left':
				frappe.throw ("The Open Air Prisoner is still Active. You cannot change it.")

	def on_submit(self):
		frappe.db.sql(""" update `tabOpen Air Prisoner` set docstatus = 0, status = 'Active', date_of_separation = NULL  where name = '{}' """.format(self.oap))
		frappe.db.sql(""" update `tabEmployee Internal Work History` set docstatus = 0 where parent = '{}' """.format(self.oap))