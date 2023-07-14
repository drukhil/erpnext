# # Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

# from __future__ import unicode_literals
# import frappe
# from frappe.utils import flt, getdate, formatdate, cstr

# def execute(filters=None):
# 	columns = get_columns()
# 	data = get_data(filters)
# 	return columns, data

# def get_data(filters=None):
    
#     return frappe.db.sql("""
# 				select po.name,
#  	date(po.transaction_date) as "PO Date::90", 
# 	poi.item_name as "Material Name::120", 
# 	poi.item_code as "PO Item Code::120", 
# 	poi.uom as "PO UoM::120",  
# 	poi.qty as "PO Qty::120",
# 	poi.rate  as "PO Rate::120",
# 	pr.name as "Purchase Receipt ID:Link/Purchase Receipt:120", 
# 	date(pr.actual_receipt_date) as "Actual Receipt Date::90", 
#         date(pr.posting_date) as "Good Receipt Date::90",
# 	pri.schedule_date as "Delivery Date::90",  
# 	pri.rate as "PR Rate::90" , 
# 	pri.received_qty as "PR Received Qty::50", 
# 	pr.status as "PR Status::90", 
# 	pi.name as "Purchase Invoice ID:Link/Purchase Invoice:100",  
# 	date(pi.posting_date) as "PR Invoice Date::90",
# 	pii.item_code as "PI Item Code::90",
# 	pii.qty as "PI Qty::90", 
# 	pii.uom as "PI UoM::90",
#        pi.branch,
# 	pi.ld_total as "LD Total::90", 
# 	pi.tds_amount as "TDS Amount::90"
# from  `tabPurchase Order` as po left join `tabPurchase Order Item` poi on poi.parent = po.name  
# left join `tabPurchase Receipt Item` pri on pri.purchase_order = po.name 
# left join `tabPurchase Receipt` pr on pr.name = pri.parent 
# left join `tabPurchase Invoice Item` pii on pii.purchase_receipt = pr.name 
# left join `tabPurchase Invoice` pi on pi.name = pii.parent 
# where pi.branch = '{branch}' and  pi.posting_date between '{from_date}' AND '{to_date}' 
# 			""".format( branch=filters.get("branch"), from_date=filters.get("from_date"), to_date=filters.get("to_date")), as_dict=True)
 

# def get_columns():
#         cols = [
                
# 		("RFQ Create Date") + ":Date:100",
# 		("RFQ Submit Date") + ":Date:100",
# 		("RFQ Status") + ":Data:100",
# 		("RFQ Owner") + ":Data:100",
#                 ("PO Name") + ":Link/Purchase Order:120",
#                 ("PO Create Date") + ":Date:100",
# 		        ("PO Submit Date") + ":Date:100",
                   
#                 ("PO Status") + ":Data:100",
# 		        ("PO Owner") + ":Link/User:140",
#                 ("PO Updated By") + ":Link/User:140",
#                 ("PR Name") + ":Link/Purchase Receipt:120",
#                 ("PR Create Date") + ":Date:100",
#                 ("PR Submit Date") + ":Date:100",
#                 ("PR Status") + ":Data:100",
# 		        ("PR Owner") + ":Link/User:140",
#                 ("PR Updated By") + ":Link/User:140",
#                 ("PI Name") + ":Link/Purchase Invoice:120",
#                 ("PI Create Date") + ":Date:100",
#                 ("PI Posting Date") + ":Date:100",
#                 ("PI Status") + ":Data:100",
# 		        ("PI Owner") + ":Link/User:140",
#                 ("PI updated By") + ":Link/User:140",

#         ]
#         return cols