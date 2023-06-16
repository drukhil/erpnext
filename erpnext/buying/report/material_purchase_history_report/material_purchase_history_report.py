
# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
    columns, data = get_column(), get_data(filters)
    return columns, data

def get_column():
    columns =[
        ("Material Code") + ":Link/Item:120",
        ("Material Name") + "::120",
        ("Material Group") + ":Link/Item Group:120",
        ("Material Description") + "::120",
        ("PO Qty") + ":Float:100",
        ("UOM") + ":Link/UOM:100",
        ("Rate") + ":Currency:100",
        ("Amount") + ":Currency:100",
        ("Purchase Order") + ":Link/Purchase Order:120",
        ("PO Date") + ":Date:100",
	("Delivery Date") + ":Date:100",
        ("Vendor") + ":Link/Supplier:120",
        ("Vendor Name") + "::120",
        ("Project Name") + "::120",
        ("Received Qty") + ":Float:120",
        ("Company") + ":Link/Company:120"
    ]
    return columns

def get_data(filters):
    cond = get_condition(filters)
    if filters.accumulate:
        data = frappe.db.sql("""
                             select 
                             po_item.item_code,
                             po_item.item_name,
                             po_item.item_group,
                             po_item.description,
                             sum(po_item.qty) as qty,
                             po_item.uom,
                             po_item.base_rate,
                             sum(po_item.base_amount) as base_amount,
                             po.name,
                             po.transaction_date,
			     po.schedule_date,		
                             po.supplier,
                             sup.supplier_name,
                             (select p.project_name from `tabProject` as p where p.name=po_item.project),
                             sum(ifnull(po_item.received_qty, 0)) as received_qty,
                             po.company
                             from `tabPurchase Order` as po, `tabPurchase Order Item` as po_item, `tabSupplier` as sup
                             where po.name=po_item.parent and po.supplier=sup.name and po.docstatus=1 and po.transaction_date between '{from_date}' and '{to_date}' {condition}
                             
                             """.format(from_date=filters.from_date, to_date=filters.to_date, condition=cond))
    else:                   #removed po.schedule_date in line 55
        data = frappe.db.sql("""
                SELECT
                    po_item.item_code, 
                    po_item.item_name, 
                    po_item.item_group, 
                    po_item.description,
                    po_item.qty,
                    po_item.uom,
                    po_item.base_rate,
                    po_item.base_amount,
                    po.name,
                    po.transaction_date,
		    po.schedule_date,	
                    po.supplier,
                    sup.supplier_name,
                    (select p.project_name from `tabProject` as p where p.name=po_item.project),
                    ifnull(po_item.received_qty, 0),
                    po.company 
                FROM `tabPurchase Order` as po, `tabPurchase Order Item` as po_item, `tabSupplier` as sup
                WHERE po.name=po_item.parent and po.supplier=sup.name and po.docstatus=1 and po.transaction_date between '{from_date}' and '{to_date}'
                {condition}
                """.format(from_date=filters.from_date, to_date=filters.to_date, condition=cond))
    return data
    #po.schedule_date removed in line 78
def get_condition(filters):
    conds = ""
    if filters.branch:
        conds += "and po.branch='{}'".format(filters.branch)
    if filters.material_code:
        conds += "and po_item.item_code='{}'".format(filters.material_code)
    if filters.material_group:
        conds += "and po_item.item_group='{}'".format(filters.material_group)
    if filters.vendor:
        conds += "and po.supplier='{}'".format(filters.vendor)
    return conds
# def execute(filters=None):
#     columns, data = get_column(), get_data(filters)
#     return columns, data

# def get_column():
#     columns =[
#         ("Material Code") + ":Link/Item:120",
#         ("Material Name") + "::120",
#         ("Material Group") + ":Link/Item Group:120",
#         ("Material Description") + "::120",
#         ("PO Qty") + ":Float:100",
#         ("UOM") + ":Link/UOM:100",
#         ("Rate") + ":Currency:100",
#         ("Amount") + ":Currency:100",
#         ("Purchase Order") + ":Link/Purchase Order:120",
#         ("PO Date") + ":Date:100",

#         ("Vendor") + ":Link/Supplier:120",
#         ("Vendor Name") + "::120",
#         ("Project Name") + "::120",
#         ("Received Qty") + ":Float:120",
#         ("Company") + ":Link/Company:120"
#     ]
#     return columns

# def get_data(filters):
#     cond = get_condition(filters)
#     data = frappe.db.sql("""
#                 SELECT
#                     po_item.item_code, 
#                     po_item.item_name, 
#                     po_item.item_group, 
#                     po_item.description,
#                     po_item.qty,
#                     po_item.uom,
#                     po_item.base_rate,
#                     po_item.base_amount,
#                     po.name,
#                    
		      
#                     po.supplier,
#                     sup.supplier_name,
#                     (select p.project_name from `tabProject` as p where p.name=po_item.project),
#                     ifnull(po_item.received_qty, 0),
#                     po.company 
#                 FROM `tabPurchase Order` as po, `tabPurchase Order Item` as po_item, `tabSupplier` as sup
#                 WHERE po.name=po_item.parent and po.supplier=sup.name and po.docstatus=1 and po.transaction_date between '{from_date}' and '{to_date}'
#                 {condition}
#                 """.format(from_date=filters.from_date, to_date=filters.to_date, condition=cond))
#     return data

# def get_condition(filters):
#     conds = ""
#     if filters.branch:
#         conds += "and po.branch='{}'".format(filters.branch)
#     return conds
