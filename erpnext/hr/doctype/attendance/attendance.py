# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import getdate, nowdate
from frappe import _
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name

class Attendance(Document):
	def validate_duplicate_record(self):
		res = frappe.db.sql("""select name from `tabAttendance` where employee = %s and att_date = %s
			and name != %s and docstatus = 1""",
			(self.employee, self.att_date, self.name))
		if res:
			frappe.throw(_("Attendance for employee {0} is already marked").format(self.employee))

		set_employee_name(self)

	def check_leave_record(self):
		if self.status == 'Present':
			leave = frappe.db.sql("""select name from `tabLeave Application`
				where employee = %s and %s between from_date and to_date and status = 'Approved'
				and docstatus = 1""", (self.employee, self.att_date))

			if leave:
				frappe.throw(_("Employee {0} was on leave on {1}. Cannot mark attendance.").format(self.employee,
					self.att_date))

	def validate_att_date(self):
		if self.reference_name:
			return
		if getdate(self.att_date) > getdate(nowdate()):
			frappe.throw(_("Attendance can not be marked for future dates"))

	def validate_employee(self):
		emp = frappe.db.sql("select name from `tabEmployee` where name = %s and status = 'Active'",
		 	self.employee)
		if not emp:
			frappe.throw(_("Employee {0} is not active or does not exist").format(self.employee))

	def validate(self):
		from erpnext.controllers.status_updater import validate_status
		validate_status(self.status, ["Present", "Absent", "Half Day", "Tour", "Leave"])
		self.validate_att_date()
		self.validate_duplicate_record()
		self.check_leave_record()
		self.branch = frappe.db.get_value("Employee", self.employee, "branch")

	def on_update(self):
		# this is done because sometimes user entered wrong employee name
		# while uploading employee attendance
		employee_name, branch = frappe.db.get_value("Employee", self.employee, ["employee_name", "branch"])
		frappe.db.set(self, 'employee_name', employee_name)
		frappe.db.set(self, 'branch', branch)

	def on_submit(self):
		self.db_set("branch", frappe.db.get_value("Employee", self.employee, "branch"))

	#def on_cancel(self):
	#	user = frappe.session.user
        #       if "HR Manager" not in frappe.get_roles(user):
        #                frappe.throw("Only HR Manager Can Cancel the document")                                  		
