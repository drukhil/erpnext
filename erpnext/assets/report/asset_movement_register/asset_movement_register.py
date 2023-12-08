# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
        movement_query = get_asset_movement_query(filters)
        bulk_transfer_query = get_bulk_transfer_query(filters)
        columns = get_columns(filters)
        data = get_data(movement_query,bulk_transfer_query,filters)
        frappe.errprint(str(movement_query))
        return columns, data

def get_columns(filters):
        if filters.get("type") == "Asset Movement":
        
                return[
               
                 {
                        "fieldname": "posting_date",
                        "label": ("Transaction Date"),
                        "fieldtype": "Date",
                       
                        "width": 100
                },
                 
                              {
                        "fieldname": "name",
                        "label": ("Transaction Id"),
                        "fieldtype": "Data",
                       
                        "width": 100
                },
                {
                        "fieldname": "asset",
                        "label": ("Asset Code"),
                        "fieldtype": "Data",
                        "width": 200
                },
                {
                        "fieldname": "asset_name",
                        "label": ("Asset Name"),
                        "fieldtype": "Data",
                        "width": 200
                },
                {
                        "fieldname": "source_custodian",
                        "label": ("Source Custodian"),
                        "fieldtype": "Data",
                       
                        "width": 200
                },
                {
                        "fieldname":"current_cost_center",
                        "label": ("Source Cost Center"),
                        "fieldtype": "Data",
                       
                        "width": 200
                },
		{
                        "fieldname": "target_custodian",
                        "label": ("Target Custodian"),
                        "fieldtype": "Data",
                        "width": 150
                },
                 {
                        "fieldname": "target_custodian_cost_center",
                        "label":("Target Cost Center"),
                        "fieldtype": "Data",
                        "width": 150
                },
                
        ]
        if filters.get("type") == "Bulk Asset Transfer":
                return [
                         {
                        "fieldname": "posting_date",
                        "label": ("Transaction Date"),
                        "fieldtype": "Date",
                       
                        "width": 100
                },
                              {
                        "fieldname": "bulk_id",
                        "label": ("Transaction Id"),
                        "fieldtype": "Data",
                       
                        "width": 100
                },
                         
                {
                        "fieldname": "asset_code",
                        "label": ("Asset Code"),
                        "fieldtype": "Data",
                        "width": 200
                },
                {
                        "fieldname": "asset_name",
                        "label": ("Asset Name"),
                        "fieldtype": "Data",
                        "width": 200
                },
                {
                        "fieldname": "current_custodian",
                        "label": ("Source Custodian"),
                        "fieldtype": "Data",
                       
                        "width": 200
                },
                {
                        "fieldname":"cost_center",
                        "label": ("Source Cost Center"),
                        "fieldtype": "Data",
                       
                        "width": 200
                },
		{
                        "fieldname": "custodian",
                        "label": ("Target Custodian"),
                        "fieldtype": "Data",
                        "width": 150
                },
                 {
                        "fieldname": "custodian_cost_center",
                        "label":("Target Cost Center"),
                        "fieldtype": "Data",
                        "width": 150
                },
                ]
                
def get_asset_movement_query(filters):
        # frappe.errprint(filters)

        query = """
        SELECT
        t1.asset,
        t1.posting_date,
        t1.name,
        t1.source_custodian,
        t1.target_custodian,
        t1.target_custodian_cost_center,
        t1.current_cost_center, 
        t2.asset_name
        FROM `tabAsset Movement` t1, `tabAsset` t2
        WHERE t1.asset = t2.name and t1.docstatus = 1 and t1.posting_date between '{from_date}' and '{to_date}'
""".format(from_date = filters.from_date, to_date = filters.to_date)
        return query
def get_bulk_transfer_query(filters):
        query = """ select 
        t1.asset_name,
        t2.current_custodian,
        t2.name as bulk_id,
        t1.asset_code,
        t1.cost_center,
        t2.custodian,
        t2.custodian_cost_center,
        t2.posting_date
        from 
        `tabBulk Asset Transfer Item` t1 ,`tabBulk Asset Transfer` 
        t2 where t1.custodian = t2.custodian and t2.docstatus = 1 and posting_date between '{from_date}' and '{to_date}'

       """.format(from_date = filters.from_date, to_date = filters.to_date)
        return query
       
        
        

def get_data(movement_qry,bulk_qry,filters):
        if filters.get('type') == 'Asset Movement':
                data = frappe.db.sql(movement_qry, as_dict =True)
                frappe.errprint(str(data))
                return data
        if filters.get('type') == 'Bulk Asset Transfer':
                data = frappe.db.sql(bulk_qry, as_dict = True)
                frappe.errprint(str(data))
                return data

