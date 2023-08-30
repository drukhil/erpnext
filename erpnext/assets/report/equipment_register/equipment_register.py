# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	data = get_data(filters)
	columns = get_columns(filters)

	return columns, data

def get_columns(filters):
	columns = [
		 _("Equipment Code") + ":Link/Equipment:120",	
	 	 _("Registration No") + "::90",	
	 	 _("Equipment Type") + "::120",	
	 	 _("Equipment Model") + "::140",	
	 	 _("Equipment Category.") + "::140", 
	         _("Amount") + " :Currency:100",
		_("Branch") + "::140"	

	]
	
	return columns	

def get_data(filters):
	data = """ select e.name, e.equipment_number, e.equipment_type, e.equipment_model, e.equipment_category, (select gross_purchase_amount from `tabAsset` where name = e.asset_code) as amount, e.branch from `tabEquipment` e where 1 = 1"""
	if filters.get("owner"):
		if filters.get("owner") == 'Own':		
			data += " and e.not_cdcl = 0"	

		if filters.get("owner") == 'Others':
			data += " and e.not_cdcl = 1"

	if filters.get("branch"): 		
		data += " and e.branch = '{0}'".format(filters.branch)	

	return frappe.db.sql(data)
