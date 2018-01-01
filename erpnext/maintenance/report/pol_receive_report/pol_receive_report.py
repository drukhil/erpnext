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
                ("Equipment ") + ":Link/Equipment:120",
                ("Equipment No.") + ":Data:120",
                ("Book Type") + ":Data:120",
		("Supplier") + ":Data:120",
                ("POL Type")+ ":Data:100",
                ("Date") + ":Date:120",
                ("Quantity") + ":Data:120",
                ("Rate") + ":Data:120",
                ("Amount") + ":Currency:120"
        ]

def get_data(filters):

        query =  "select p.equipment, p.equipment_number, p.book_type, p.supplier, p.pol_type, p.date, p.qty, p.rate, ifnull(sum(p.total_amount),0) from tabPOL as p where p.docstatus = 1"

        if filters.get("branch"):
		query += " and p.branch = \'"+ str(filters.branch) + "\'"

        if filters.get("from_date") and filters.get("to_date"):

                query += " and p.date between \'" + str(filters.from_date) + "\' and \'"+ str(filters.to_date) + "\'"
	if filters.get("direct"):
                query += " and p.direct_consumption = 1"
	else:
		query += " and p.direct_consumption =  p.direct_consumption "
	
	query += " group by p.equipment"
        return frappe.db.sql(query)