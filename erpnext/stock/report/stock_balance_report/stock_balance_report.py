# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate

def execute(filters=None):
	if not filters: filters = {}
	
	# validate_filters(filters)

	columns = get_columns()
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_map(filters)

	data = []
	for (company, item, warehouse) in sorted(iwb_map):
		qty_dict = iwb_map[(company, item, warehouse)]
		data.append([item, item_map[item]["item_name"],
			item_map[item]["item_group"],
			item_map[item]["item_sub_group"],
			warehouse,
			item_map[item]["rack"],
			item_map[item]["stock_uom"], qty_dict.opening_qty,
			qty_dict.opening_val, qty_dict.in_qty,
			qty_dict.in_val, qty_dict.out_qty,
			qty_dict.out_val, qty_dict.bal_qty,
			qty_dict.bal_val, qty_dict.val_rate,
			company
		])

	return columns, data

def get_columns():
	"""return columns"""

        '''
	columns = [
		_("Material Code")+":Link/Item:100",
		_("Material Name")+"::150",
		_("Material Group")+"::100",
		_("Material Sub Group")+"::100",
		_("Warehouse")+":Link/Warehouse:100",
		_("Rack")+":Data:90",
		_("Stock UOM")+":Link/UOM:90",
		_("Opening Qty")+":Float:100",
		_("Opening Value")+":Float:110",
		_("Receipt Qty")+":Float:80",
		_("Receipt Value")+":Float:80",
		_("Issue Qty")+":Float:80",
		_("Issue Value")+":Float:80",
		_("Balance Qty")+":Float/5:100",
		_("Balance Value")+":Float:100",
		_("MAP")+":Float:90",
		_("Company")+":Link/Company:100"
	]
        '''
        
	columns = [
                {
                        "label": "Material Code",
                        "fieldtype": "Link",
                        "options": "Item"
                },
                {
                        "label": "Material Name",
                        "fieldtype": "Data",
                        "width": 150
                },
                {
                        "label": "Material Group",
                        "fieldtype": "Data",
                        "width": 100
                },
		{
                        "label": "Material Sub Group",
                        "fieldtype": "Data",
                        "width": 100
                },
		{
                        "label": "Warehouse",
                        "fieldtype": "Link",
                        "options": "Warehouse",
                        "width": 100
                },
		{
                        "label": "Rack",
                        "fieldtype": "Data",
                        "width": 90
                },
		{
                        "label": "Stock UOM",
                        "fieldtype": "Link",
                        "options": "UOM",
                        "width": 90
                },
		{
                        "label": "Opening Qty",
                        "fieldtype": "Float",
                        "precision": 5,
                        "width": 100
                },
		{
                        "label": "Opening Value",
                        "fieldtype": "Float",
                        "width": 110
                },
		{
                        "label": "Receipt Qty",
                        "fieldtype": "Float",
                        "precision": 5,
                        "width": 80
                },
		{
                        "label": "Receipt Value",
                        "fieldtype": "Float",
                        "width": 80
                },
		{
                        "label": "Issue Qty",
                        "fieldtype": "Float",
                        "precision": 5,
                        "width": 80
                },
		{
                        "label": "Issue Value",
                        "fieldtype": "Float",
                        "width": 80
                },
		{
                        "label": "Balance Qty",
                        "fieldtype": "Float",
                        "precision": 5,
                        "width": 100
                },
		{
                        "label": "Balance Value",
                        "fieldtype": "Float",
                        "width": 100
                },
		_("MAP")+":Float:90",
		_("Company")+":Link/Company:100"
	]

	return columns

def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and posting_date <= '%s'" % frappe.db.escape(filters["to_date"])
	else:
		frappe.throw(_("'To Date' is required"))

	if filters.get("item_code"):
		conditions += " and item_code = '%s'" % frappe.db.escape(filters.get("item_code"), percent=False)

	if filters.get("warehouse"):
		conditions += " and warehouse = '%s'" % frappe.db.escape(filters.get("warehouse"), percent=False)

	return conditions

def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select item_code, warehouse, posting_date, actual_qty, valuation_rate,
			company, voucher_type, qty_after_transaction, stock_value_difference
		from `tabStock Ledger Entry` force index (posting_sort_index)
		where docstatus < 2 %s order by posting_date, posting_time, name""" %
		conditions, as_dict=1)

def get_item_warehouse_map(filters):
	iwb_map = {}
	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	sle = get_stock_ledger_entries(filters)

	for d in sle:
		key = (d.company, d.item_code, d.warehouse)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict({
				"opening_qty": 0.0000, "opening_val": 0.0000,
				"in_qty": 0.0000, "in_val": 0.0000,
				"out_qty": 0.0000, "out_val": 0.0000,
				"bal_qty": 0.0000, "bal_val": 0.0000,
				"val_rate": 0.0, "uom": None
			})

		qty_dict = iwb_map[(d.company, d.item_code, d.warehouse)]

		if d.voucher_type == "Stock Reconciliation":
			qty_diff = flt(d.qty_after_transaction,5) - flt(qty_dict.bal_qty,5)
		else:
			qty_diff = flt(d.actual_qty,5)

		value_diff = flt(d.stock_value_difference)

		if d.posting_date < from_date:
			qty_dict.opening_qty += flt(qty_diff,5)
			qty_dict.opening_val += value_diff

		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if qty_diff > 0:
				qty_dict.in_qty += flt(qty_diff,5)
				qty_dict.in_val += value_diff
			else:
				qty_dict.out_qty += abs(qty_diff)
				qty_dict.out_val += abs(value_diff)

		qty_dict.val_rate = d.valuation_rate
		qty_dict.bal_qty += flt(qty_diff,5)
		qty_dict.bal_val += value_diff

	return iwb_map

def get_item_details(filters):
	condition = ''
	value = ()
	if filters.get("item_code"):
		condition = "where item_code=%s"
		value = (filters["item_code"],)

	items = frappe.db.sql("""select name, item_name, stock_uom, item_group, item_sub_group, brand, rack, description
		from tabItem {condition}""".format(condition=condition), value, as_dict=1)

	return dict((d.name, d) for d in items)

def validate_filters(filters):
	if not (filters.get("item_code") or filters.get("warehouse")):
		sle_count = flt(frappe.db.sql("""select count(name) from `tabStock Ledger Entry`""")[0][0])
		if sle_count > 500000:
			frappe.throw(_("Please set filter based on Item or Warehouse"))
	
