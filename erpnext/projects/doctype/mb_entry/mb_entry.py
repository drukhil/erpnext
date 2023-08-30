# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# project_invoice.py
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0		  SHIV		 2017/09/21                            Original Version
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, time_diff_in_hours, get_datetime, getdate, cint, get_datetime_str
from frappe.model.mapper import get_mapped_doc

class MBEntry(Document):
	def validate(self):
                self.set_status()
                self.default_validations()
                self.set_defaults()
                
        def on_submit(self):
                self.validate_boq_items()
                self.update_boq()

        def before_cancel(self):
                self.set_status()

        def on_cancel(self):
                self.update_boq()
                
        def set_status(self):
                self.status = {
                        "0": "Draft",
                        "1": "Uninvoiced",
                        "2": "Cancelled"
                }[str(self.docstatus or 0)]
                
        def default_validations(self):
                for rec in self.mb_entry_boq:
                        if flt(rec.entry_quantity) > flt(rec.act_quantity):
                                frappe.throw(_("Row{0}: Entry Quantity cannot be greater than Balance Quantity").format(rec.idx))
                        elif flt(rec.entry_amount) > flt(rec.act_amount):
                                frappe.throw(_("Row{0}: Entry Amount cannot be greater than Balance Amount").format(rec.idx))
                        elif flt(rec.entry_quantity) < 0 or flt(rec.entry_amount) < 0:
                                frappe.throw(_("Row{0}: Value cannot be in negative.").format(rec.idx))

        def set_defaults(self):
                if self.project:
                        base_project          = frappe.get_doc("Project", self.project)
                        self.company          = base_project.company
                        self.customer         = base_project.customer
                        self.branch           = base_project.branch
                        self.cost_center      = base_project.cost_center

                        if base_project.status in ('Completed','Cancelled'):
                                frappe.throw(_("Operation not permitted on already {0} Project.").format(base_project.status),title="MB Entry: Invalid Operation")
                        
                if self.boq:
                        base_boq              = frappe.get_doc("BOQ", self.boq)
                        self.cost_center      = base_boq.cost_center
                        self.branch           = base_boq.branch
                        self.boq_type         = base_boq.boq_type
                        
        def validate_boq_items(self):
                for rec in self.mb_entry_boq:
                        if rec.is_selected == 1 and flt(rec.entry_amount) > 0:
                                item = frappe.db.sql("""
                                                select
                                                        ifnull(balance_quantity,0) as balance_quantity,
                                                        ifnull(balance_amount,0) as balance_amount
                                                from
                                                        `tabBOQ Item`
                                                where   name = '{0}'
                                                """.format(rec.boq_item_name), as_dict=1)[0]

                                if flt(rec.entry_quantity) > flt(item.balance_quantity):
                                        frappe.throw(_('Row{0}: Insufficient Balance. Please refer to BOQ# <a href="#Form/BOQ/{1}">{1}</a>').format(rec.idx, self.boq))
                                elif flt(rec.entry_amount) > flt(item.balance_amount):
                                        frappe.throw(_('Row{0}: Insufficient Balance. Please refer to BOQ# <a href="#Form/BOQ/{1}">{1}</a>').format(rec.idx, self.boq))
                                        
                        
        def update_boq(self):
                # Updating `tabBOQ Item`
                boq_list = frappe.db.sql("""
                                select
                                        meb.boq_item_name,
                                        sum(
                                                case
                                                when '{0}' = 'Milestone Based' then 0
                                                else
                                                        case
                                                        when meb.docstatus < 2 then ifnull(meb.entry_quantity,0)
                                                        else -1*ifnull(meb.entry_quantity,0)
                                                        end
                                                end
                                        ) as entry_quantity,
                                        sum(
                                                case
                                                when meb.docstatus < 2 then ifnull(meb.entry_amount,0)
                                                else -1*ifnull(meb.entry_amount,0)
                                                end
                                        ) as entry_amount
                                from  `tabMB Entry BOQ` as meb
                                where meb.parent        = '{1}'
                                and   meb.is_selected   = 1
                                group by meb.boq_item_name
                                """.format(self.boq_type, self.name), as_dict=1)

                for item in boq_list:
                        frappe.db.sql("""
                                update `tabBOQ Item`
                                set
                                        booked_quantity  = ifnull(booked_quantity,0) + ifnull({1},0),
                                        booked_amount    = ifnull(booked_amount,0) + ifnull({2},0),
                                        balance_quantity = ifnull(balance_quantity,0) - ifnull({1},0),
                                        balance_amount   = ifnull(balance_amount,0) - ifnull({2},0)
                                where name = '{0}'
                                """.format(item.boq_item_name, flt(item.entry_quantity), flt(item.entry_amount)))

@frappe.whitelist()
def make_mb_invoice(source_name, target_doc=None):
        def update_master(source_doc, target_doc, source_partent):
                #target_doc.project = source_doc.project
                target_doc.invoice_title = str(target_doc.project) + "(Project Invoice)"
                target_doc.reference_doctype = "MB Entry"
                target_doc.reference_name    = source_doc.name

        def update_reference(source_doc, target_doc, source_parent):
                pass
                
        doclist = get_mapped_doc("MB Entry", source_name, {
                "MB Entry": {
                                "doctype": "Project Invoice",
                                "field_map":{
                                        "project": "project",
                                        "branch": "branch",
                                        "customer": "customer"
                                },
                                "postprocess": update_master
                        },
        }, target_doc)
        return doclist        
