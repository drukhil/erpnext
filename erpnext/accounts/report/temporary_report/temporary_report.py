# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_data(filters):
	return frappe.db.sql(""" 
		select voucher_no,account,debit,credit,posting_date from `tabGL Entry` where voucher_no in (select ts.maintenance_payment from `tabTechnical Sanction Bill` ts inner join `tabMechanical Payment` m on m.name = ts.maintenance_payment  where m.docstatus=1) and posting_date between '2021-01-01' and '2021-12-31' order by voucher_no;
		""", as_dict=1)
def get_columns():
	return [
		{
		  "fieldname": "voucher_no",
		  "label": "Voucher No",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "account",
		  "label": "Account",
		  "fieldtype": "Data",
		  "width": 200
		},
		{
		  "fieldname": "debit",
		  "label": "Debit",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "credit",
		  "label": "Credit",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "posting_date",
		  "label": "Posting Date",
		  "fieldtype": "Date",
		  "width": 100
		}
	]