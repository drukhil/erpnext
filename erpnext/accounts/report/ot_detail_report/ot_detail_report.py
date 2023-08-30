# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
        return[
		("Employee") + ":Link/Employee:120",
		("Employee Name") + ":Data:120",
                ("Bank Name") + ":Data:120",
		("Bank Account") + ":Data:120",
                ("Total Amount") + ":Currency:120",
		("OT Ref") + ":Link/Process Overtime Payment:120"
        ]

def get_data(filters):
        query = """ select oti.employee, oti.employee_name, oti.bank_name, oti.bank_account, sum(oti.total_ot_amount), ot.name 
			from `tabProcess Overtime Payment` ot, `tabOvertime Payment Item` oti where oti.parent = ot.name 
			and ot.docstatus <= 1"""

	if filters.get("ot_reference"):
		query += " and ot.name = '{0}'".format(filters.ot_reference)

        if filters.get("branch"):
                query += " and ot.branch = '{0}'".format(filters.branch)

	if filters.get("from_date") and filters.get("to_date"):
		query += " and ot.posting_date between '{0}' and '{1}'".format(filters.from_date, filters.to_date)
	
	query += " group by oti.employee"
	return frappe.db.sql(query)
