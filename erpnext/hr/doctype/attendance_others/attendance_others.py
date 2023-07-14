# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AttendanceOthers(Document):
	def validate(self):
                res = frappe.db.sql("""select name from `tabAttendance Others` where employee = %s and date = %s
                        and name != %s and docstatus = 1""",
                        (self.employee, self.date, self.name))
                if res:
                        frappe.throw(("Attendance for employee {0} is already marked").format(self.employee))

	def on_cancel(self):
                user = frappe.session.user
                if "DFG User" not in frappe.get_roles(user):
                        frappe.throw("Only HR Manager Can Cancel the document")

                
