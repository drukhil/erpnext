# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr

def execute(filters=None):
	validate_filters(filters)
	columns = get_columns()
	queries = construct_query(filters)
	data = get_data(queries)

	return columns, data

def get_data(query):
	data = []
	datas = frappe.db.sql(query, as_dict=True)
	for d in datas:
		status = 'Not Paid'
		bil = frappe.db.sql(""" select name from `tabRRCO Receipt Entries` where  purchase_invoice = '{0}' and docstatus =1""".format(d.bill_no), as_dict = 1)
		if bil:
			status = 'Paid'
		row = [d.vendor, d.vendor_tpn_no, d.bill_no, d.bill_date, d.tds_taxable_amount, d.tds_rate, d.tds_amount, d.cost_center, status]
		data.append(row)
	
	return data

def construct_query(filters=None):
	if not filters.tds_rate:
		filters.tds_rate = '2'
	cond = ""
	cond1 = ""
	if filters.branch:
		cond = "AND d.branch = '{}'".format(filters.branch)
		cond1 = "AND p.branch = '{}'".format(filters.branch)
	query = """
			SELECT s.vendor_tpn_no, s.name as vendor, p.name as bill_no, p.bill_date, 
   			p.tds_taxable_amount, p.tds_rate, p.tds_amount, p.buying_cost_center as cost_center
			FROM `tabPurchase Invoice` as p, `tabSupplier` as s 
			WHERE p.docstatus = 1 and p.supplier = s.name AND p.tds_amount > 0 
			AND p.posting_date BETWEEN '{0}' AND '{1}'
			AND p.tds_rate = '{2}'
			{3}
			UNION 
			SELECT 
   				(select vendor_tpn_no from `tabSupplier` where name = d.party) as vendor_tpn_no, 
				d.party as vendor, d.name as bill_no, d.posting_date as bill_date,
    			d.taxable_amount as tds_taxable_amount, d.tds_percent as tds_rate, 
       			d.tds_amount as tds_amount, d.cost_center as cost_center 
			FROM `tabDirect Payment` as d
			
			WHERE d.docstatus = 1
			AND d.payment_type = 'Payment'
			AND d.tds_amount > 0 AND d.posting_date BETWEEN '{0}' AND '{1}'  
			AND d.tds_percent = '{2}'
			AND d.tds_amount > 0
			{4}
			""".format(str(filters.from_date), str(filters.to_date), filters.tds_rate, cond1, cond)
	return query

def validate_filters(filters):

	if not filters.fiscal_year:
		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))

	fiscal_year = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"], as_dict=True)
	if not fiscal_year:
		frappe.throw(_("Fiscal Year {0} does not exist").format(filters.fiscal_year))
	else:
		filters.year_start_date = getdate(fiscal_year.year_start_date)
		filters.year_end_date = getdate(fiscal_year.year_end_date)

	if not filters.from_date:
		filters.from_date = filters.year_start_date

	if not filters.to_date:
		filters.to_date = filters.year_end_date

	filters.from_date = getdate(filters.from_date)
	filters.to_date = getdate(filters.to_date)

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

	if (filters.from_date < filters.year_start_date) or (filters.from_date > filters.year_end_date):
		frappe.msgprint(_("From Date should be within the Fiscal Year. Assuming From Date = {0}")\
			.format(formatdate(filters.year_start_date)))

		filters.from_date = filters.year_start_date

	if (filters.to_date < filters.year_start_date) or (filters.to_date > filters.year_end_date):
		frappe.msgprint(_("To Date should be within the Fiscal Year. Assuming To Date = {0}")\
			.format(formatdate(filters.year_end_date)))
		filters.to_date = filters.year_end_date


def get_columns():
	return [
		{
		  "fieldname": "vendor_name",
		  "label": "Vendor Name",
		  "fieldtype": "Data",
		  "width": 250
		},
		{
		  "fieldname": "tpn_no",
		  "label": "TPN Number",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "invoice_no",
		  "label": "Invoice No",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "Invoice_date",
		  "label": "Invoice Date",
		  "fieldtype": "Date",
		  "width": 100
		},
		{
		  "fieldname": "bill_amount",
		  "label": "Bill Amount",
		  "fieldtype": "Currency",
		  "width": 100
		},
		{
		  "fieldname": "tds_rate",
		  "label": "TDS Rate(%)",
		  "fieldtype": "Data",
		  "width": 90
		},
  		{
		  "fieldname": "tds_amount",
		  "label": "TDS Amount",
		  "fieldtype": "Currency",
		  "width": 100
		},
      	{
		  "fieldname": "cost_center",
		  "label": "Cost Center",
		  "fieldtype": "Link",
		  "options": "Cost Center",
		  "width": 100
		},
		{
		"fieldname": "status",
		"label": "Status",
		"fieldtype": "Data",
		"width": 100
		},
	]
