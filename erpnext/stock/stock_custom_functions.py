# Copyright (c) 2016, Druk Holding & Investments Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

#function to get the last item_code (material code)
#based on the item (material)group selected by the user
@frappe.whitelist()
def get_current_item_code(item_group): 
	item_code = frappe.db.sql("""select item_code from tabItem where item_group=%s order by item_code desc limit 1;""", item_group);
	if item_code:
		return (int(item_code[0][0]) + 1);
	else:
		return getItemCode(item_group);


def getItemCode(item_group):
	return {
		"Consumables": 100000,
		"Fixed Asset": 200000,
		"Spareparts": 300000,
		"Services Miscellaneous": 400000,
		"Services Works": 500000,
		"Locally Extract Material": 800000,
		"Sales Product": 600000
	}.get(item_group, 000000)

"""#select stock entry templates based on dates
@frappe.whitelist()
def get_template_list(doctype, txt, searchfield, start, page_len, filters): 
	if filters['naming_series']:
		query = "SELECT name, template_name FROM `tabStock Price Template` WHERE \'" + filters['posting_date'] +"\'  BETWEEN from_date AND to_date AND naming_series = \'" + filters['naming_series'] + "\' and docstatus = 1 and purpose= \'"+ filters['purpose'] +"\'";
		return frappe.db.sql(query);
	

#Get item values from "Initial Stock Templates" during stock entry
@frappe.whitelist()
def get_initial_values(name):
	result = frappe.db.sql("SELECT a.item_code, a.item_name, a.uom, a.rate_currency, a.rate_amount, b.expense_account, b.selling_cost_center, b.stock_uom FROM `tabStock Price Template` AS a, tabItem AS b WHERE a.item_name = b.item_name AND a.name = \'" + str(name) + "\'", as_dict=True);
	return result;
"""
