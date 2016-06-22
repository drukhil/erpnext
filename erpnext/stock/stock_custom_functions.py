# Copyright (c) 2016, Druk Holding & Investments Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

#function to get the last item_code (material code)
#based on the item (material)group selected by the user
@frappe.whitelist()
def get_current_item_code(item_group): 
	item_code = frappe.db.sql("""select item_code from tabItem where item_group=%s order by item_code desc limit 1;""", item_group);
	return (int(item_code[0][0]) + 1);


