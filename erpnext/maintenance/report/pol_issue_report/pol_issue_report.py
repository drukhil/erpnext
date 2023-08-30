# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from erpnext.maintenance.report.maintenance_report import get_pol_between

def execute(filters=None):
        columns = get_columns()
        data = get_data(filters)

        return columns, data

def get_columns():
        return [
                ("Equipment ") + ":Link/Equipment:120",
                ("Equipment No.") + ":Data:120",
                ("Item Code") + ":Link/Item:100",
                ("Item Name") + ":Data:170",
                ("UoM") + ":Data:120",
                ("Quantity") + ":Float:120"
        ]

def get_data(filters):
	data = []
        query =  "select name, equipment_number FROM tabEquipment WHERE 1"

        if filters.get("branch"):
                query += " and branch = \'" + str(filters.branch) + "\'"

        if filters.get("not_cdcl"):
                query += " and not_cdcl = 0"

        if not filters.get("include_disabled"):
                query += " and is_disabled = 0"

	items = frappe.db.sql("select item_code, item_name, stock_uom from tabItem where is_pol_item = 1", as_dict=True)
	row = []
        for eq in frappe.db.sql(query, as_dict=True):
		for item in items:
			own_cc = 0
			if filters.get("own_cc"):
				own_cc = 1
			balance = get_pol_between("Issue", eq.name, filters.from_date, filters.to_date, item.item_code, own_cc)
			if balance:
				row = [eq.name, eq.equipment_number, item.item_code, item.item_name, item.stock_uom, balance]
				data.append(row)
	return data

