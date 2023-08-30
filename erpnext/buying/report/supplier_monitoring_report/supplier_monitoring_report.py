# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, formatdate, cstr

def execute(filters=None):
	validate_filters(filters)
	data = get_data(filters)
	columns = get_columns()

	return columns, data

def get_data(filters):
	query = "SELECT sm.purchase_order, sm.transaction_date, sm.cost_center, sm.supplier, smi.item_code, smi.uom, smi.qty, smi.rate, smi.amount, smi.schedule_date, smi.received_date, smi.received_quantity, smi.days_delayed, smi.liquidated_damage from `tabSupplier Monitoring` sm, `tabSupplier Monitoring Item` smi WHERE sm.name= smi.parent and sm.docstatus = 1 and sm.transaction_date BETWEEN \'" + str(filters.from_date) + "\' AND \'" + str(filters.to_date) + "\'"
	
	
	
	if filters.supplier:
		query+= " AND sm.supplier = \'" + str(filters.supplier) +"\'"

	data = frappe.db.sql(query, as_dict=True)


	return data

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
		  "fieldname": "purchase_order",
		  "label": "Purchase Order",
		  "fieldtype": "Link",
		  "options": "Purchase Order",
		  "width": 100
		},
		{
		  "fieldname": "transaction_date",
		  "label": "PO Date",
		  "fieldtype": "Date",
		  "width": 80
		},
		{
		  "fieldname": "cost_center",
		  "label": "Cost Center",
		  "fieldtype": "Link",
		  "options": "Cost Center",
		  "width": 180
		},
		{
		  "fieldname": "supplier",
		  "label": "Vendor",
		  "fieldtype": "Link",
		  "options": "Supplier",
		  "width": 150
		},
		{
		  "fieldname": "item_code",
		  "label": "Item Code",
		  "fieldtype": "Data",
		  "width": 90
		},
		{
		  "fieldname": "uom",
		  "label": "UOM",
		  "fieldtype": "Data",
		  "width": 50
		},
		{
		  "fieldname": "qty",
		  "label": "PO Quantity",
		  "fieldtype": "Data",
		  "width": 70
		},
		{
		  "fieldname": "rate",
		  "label": "PO Rate",
		  "fieldtype": "Data",
		  "width": 70
		},
		{
		  "fieldname": "amount",
		  "label": "Amount",
		  "fieldtype": "Currency",
		  "width": 130
		},
		{
		  "fieldname": "sechedule_date",
		  "label": "Delivery Date",
		  "fieldtype": "Date",
		  "width": 100
		},
		{
		  "fieldname": "received_date",
		  "label": "Received Date",
		  "fieldtype": "Date",
		  "width": 100
		},
		{
		  "fieldname": "received_quantity",
		  "label": "Received Quantity",
		  "fieldtype": "Data",
		  "width": 70
		},
		{
		  "fieldname": "days_delayed",
		  "label": "Days Delayed",
		  "fieldtype": "Int",
		  "width": 90
		},
		{
		  "fieldname": "liquidated_damage",
		  "label": "Liquidated Damage",
		  "fieldtype": "Currency",
		  "width": 100
		}
	]
