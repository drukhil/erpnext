#Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate
from frappe import utils
utils.now()
utils.today()

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_conditions(filters):
        conditions = ""
        if filters.get("month"):
                month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
                        "Dec"].index(filters["month"]) + 1
                filters["month"] = month
                conditions += " month(mr.creation_date) = {0}".format(filters["month"])

        if filters.get("fiscal_year"): conditions += " and year(mr.creation) = {0}".format(filters.get("fiscal_year"))
	if filters.get("cost_center"): conditions += " and mr.branch =  '{0}'".format(filters.get("cost_center"))
        conditions += " and mr.workflow_state  != 'Cancelled'"
        conditions += " and case when rq.status IS NOT NULL then rq.status != 'Cancelled' else 1 =1 end"
        conditions += " and case when po.docstatus IS NOT NULL then po.docstatus != 2 else 1 =1 end"
        conditions += " and case when pr.status IS NOT NULL then pr.status != 'Cancelled' else 1 =1 end"
        conditions += " and case when pi.docstatus IS NOT NULL then pi.docstatus != 2 else 1 =1 end"
        #and ifnull(1 =1, pi.docstatus != 2)"
        return conditions, filters

def get_data(filters):
    #today = frappe.utils.nowdate()
    #frappe.msgprint("{0}".format(today))
    conditions, filters = get_conditions(filters)
    query = frappe.db.sql("""
            select distinct
			mr.name                             as mr_name,
			mr.branch    			as mr_cost_center,
			mr.creation_date                    as mr_create_date,
			date(mr.submission)                 as mr_submit_date,
			mr.workflow_state                   as mr_status,
			mr.owner                            as mr_owner,
			case
                            when mr.workflow_state = 'Approved' and mr.material_request_type = "Purchase" then mr.purchase_change_date
                            else ''
                        end                                 as forwarded_to_procurement,
			mr.material_request_type            as mr_type,
			rq.name                             as rq_name,
			date(rq.creation)                   as rq_create_date,
			date(rq.submission)                 as rq_submit_date,
			rq.status                           as rq_status,
			rq.owner                            as rq_owner,
			po.name                             as po_name,
			date(po.creation)                   as po_create_date,
			date(po.submission)                 as po_submit_date,
                        
			po.status                           as po_status,
			po.owner                            as po_owner,
			po.modified_by                      as po_modified_by,
			pr.name                             as pr_name,
			date(pr.creation)                   as pr_create_date,
			date(pr.submission)                 as pr_submit_date,
			pr.status                           as pr_status,
			pr.owner                            as pr_owner,
			pr.modified_by                      as pr_modified_by,
			pi.name                             as pi_name,
			date(pi.creation)                   as pi_create_date,
			date(pi.submission)                 as pi_submit_date,
			case
                            when pi.is_return = 1 then "Return"
                            when pi.is_return = 0 and pi.outstanding_amount > 0 and pi.docstatus = 1 and datediff(pi.due_date, curdate())<0 then "Overdue"
                            when pi.is_return = 0 and pi.outstanding_amount > 0 and pi.docstatus = 1 and datediff(pi.due_date, curdate()) >= 0 then "Unpaid"
                            when pi.is_return = 0 and pi.outstanding_amount = 0 and pi.docstatus = 1 then "Paid"
                            when pi.docstatus = 0 then "Draft"
                            when pi.docstatus = 2 then "Cancelled"
			end                                 as pi_status,
			pi.owner                            as pi_owner,
			pi.modified_by                      as pi_modified_by
	    from `tabMaterial Request` mr
	    left join `tabRequest for Quotation Item` rqi on rqi.material_request = mr.name 
	    left join `tabRequest for Quotation` rq on rq.name = rqi.parent
            left join `tabPurchase Order Item` poi on poi.material_request = mr.name
            left join `tabPurchase Order` po on po.name = poi.parent
            left join `tabPurchase Receipt Item` pri on pri.purchase_order = po.name
            left join `tabPurchase Receipt` pr on pr.name = pri.parent
            left join `tabPurchase Invoice Item` pii on pii.purchase_receipt = pr.name
            left join `tabPurchase Invoice` pi on pi.name = pii.parent
	    where {0} order by mr.creation_date desc""".format(conditions))
    #frappe.msgprint(query)
    return query

def get_columns(filters):
        cols = [
                ("MR Name") + ":Link/Material Request:120",
		("MR Cost Center") + ":Data:160",
		        ("MR Create Date") + ":Date:100",
                ("MR Submit Date") + ":Date:110",
                ("MR Status") + ":Data:100",
		        ("MR Owner") + ":Link/User:140",
		        ("Forward To Procurment") + ":Date:100",
                ("MR Type") + ":Data:120",
		("RFQ Name") + ":Link/Request For Quotation:100",
		("RFQ Create Date") + ":Date:100",
		("RFQ Submit Date") + ":Date:100",
		("RFQ Status") + ":Data:100",
		("RFQ Owner") + ":Data:100",
                ("PO Name") + ":Link/Purchase Order:120",
                ("PO Create Date") + ":Date:100",
		        ("PO Submit Date") + ":Date:100",
                   
                ("PO Status") + ":Data:100",
		        ("PO Owner") + ":Link/User:140",
                ("PO Updated By") + ":Link/User:140",
                ("PR Name") + ":Link/Purchase Receipt:120",
                ("PR Create Date") + ":Date:100",
                ("PR Submit Date") + ":Date:100",
                ("PR Status") + ":Data:100",
		        ("PR Owner") + ":Link/User:140",
                ("PR Updated By") + ":Link/User:140",
                ("PI Name") + ":Link/Purchase Invoice:120",
                ("PI Create Date") + ":Date:100",
                ("PI Posting Date") + ":Date:100",
                ("PI Status") + ":Data:100",
		        ("PI Owner") + ":Link/User:140",
                ("PI updated By") + ":Link/User:140",

        ]
        return cols
