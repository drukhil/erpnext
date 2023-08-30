# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
        columns = get_columns()
        data = get_data(filters)

        return columns, data

def get_columns():
        return [
                ("Branch ") + ":Data:100",
                ("Employee Type") + ":Data:100",
                ("Employee ID") + ":Data:90",
                ("Employee Name") + ":Data:100",
                ("CID") + ":Data:90",
                ("Designation") + ":Data:90",
		("Qualification ") + ":Data:80",
                ("Bank") + ":Data:60",
                ("Account Number") + ":Data:100",
                ("Year") + ":Data:40",
                ("Month") + ":Data:40",
                ("No. of Days") + ":Data:60",
		("Daily Rate") + ":Data:60",
                ("Total Wage") + ":Data:60",
                ("No. of Hours") + ":Data:60",
                ("Hourly Rate") + ":Data:60",
                ("Total OT ") + ":Data:60",
                ("Health Contribution") + ":Data:60",
		("Gross Pay ") + ":Data:80",
                ("Net Pay") + ":Data:90"

        ]
def get_data(filters):
	query = """select p.branch, p.employee_type, i.employee, i.person_name, i.id_card, i.designation, i.qualification, i.bank,
                         i.account_no, i.fiscal_year, i.month, i.number_of_days, i.daily_rate,i.total_wage,  i.number_of_hours, 
                         i.hourly_rate, i.total_ot_amount, i.health, i.wage_payable, i.total_amount from `tabMR Payment Item` as i, 
                          `tabProcess MR Payment` as p where i.parent = p.name and p.docstatus = 1 """

	if filters.get("branch"):
		query += " and p.branch = \'" + str(filters.branch) + "\'"
	if filters.get("year"):
		query += " and i.fiscal_year = \'" + str(filters.year) + "\'"
	if filters.get("month"):
                query += " and i.month = \'" + str(filters.month) + "\'"
        if filters.get("employee_type"):
                query += " and p.employee_type = '{0}'".format(filters.get("employee_type"))
	return frappe.db.sql(query)


