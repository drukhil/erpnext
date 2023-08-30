# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0		  SHIV		                    2017/08/15         Original Version
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.model.naming import make_autoname
from frappe.utils import cstr, flt, getdate, today

class BOQ(Document):
        """
        def autoname(self):
                self.name = make_autoname(str('BOQ')+'.YYYY.MM.####')
        """
                
	def validate(self):
                self.update_defaults()
                self.validate_defaults()

        def on_submit(self):
                self.update_project_value()

        def on_cancel(self):
                self.update_project_value()
                
        def validate_defaults(self):
                if not self.project:
                        frappe.throw("`Project` cannot be null.")
                        
                if not self.branch:
                        frappe.throw("`Branch` cannot be null.")

                if not self.cost_center:
                        frappe.throw("`Cost Center` cannot be null.")

                if flt(self.total_amount,0) <= 0:
                        frappe.throw(_("Invalid total amount."), title="Invalid Data")
                        
        def update_defaults(self):
                item_group = ""
                self.total_amount     = 0.0
                self.price_adjustment = 0.0
                self.claimed_amount   = 0.0
                self.received_amount  = 0.0
                self.balance_amount   = 0.0
                
                for item in self.boq_item:
                        if item.is_group:
                                item_group              = item.item
                                item.quantity           = 0.0
                                item.rate               = 0.0
                                item.amount             = 0.0
                                item.claimed_quantity   = 0.0
                                item.claimed_amount     = 0.0
                                item.booked_quantity    = 0.0
                                item.booked_amount      = 0.0
                                item.balance_quantity   = 0.0
                                item.balance_amount     = 0.0
                        else:
                                item.amount           = flt(item.quantity)*flt(item.rate)
                                item.claimed_quantity = 0.0
                                item.claimed_amount   = 0.0
                                item.booked_quantity  = 0.0
                                item.booked_amount    = 0.0
                                item.balance_quantity = flt(item.quantity)
                                item.balance_amount   = flt(item.amount)

                                '''
                                self.total_amount    += flt(item.amount)
                                self.claimed_amount  += flt(item.claimed_amount)
                                self.received_amount += flt(item.received_amount)
                                self.balance_amount  += (flt(item.amount)-flt(item.received_amount))
                                '''
                        
                                self.total_amount    += flt(item.amount)
                                self.balance_amount  += flt(item.amount)

                        item.parent_item = item_group
                        if flt(item.amount) < 0:
                                frappe.throw(_("Row#{0} : Invalid amount."),title="Invalid Data")
                                
                # Defaults
                base_project = frappe.get_doc("Project", self.project)
                
                if base_project.status in ('Completed','Cancelled'):
                                frappe.throw(_("Operation not permitted on already {0} Project.").format(base_project.status),title="BOQ: Invalid Operation")
                                
                if not self.branch:
                        self.branch = base_project.branch

                if not self.cost_center:
                        self.cost_center = base_project.cost_center

                if not self.boq_date:
                        self.boq_date = today()

        def update_project_value(self):
                if self.total_amount:
                        pro_doc = frappe.get_doc("Project", self.project)
                        pro_doc.flags.dont_sync_tasks = True
                        pro_doc.project_value = flt(pro_doc.project_value)+(-1*(self.total_amount) if self.docstatus==2 else flt(self.total_amount))
                        pro_doc.save(ignore_permissions = True)

                '''
                total_amount = 0.0
                
                boq = frappe.db.sql("""
                                        select sum(ifnull(total_amount,0)) total_amount
                                        from `tabBOQ`
                                        where project = '{0}'
                                        and   docstatus = 1
                                """.format(self.project), as_dict=1)[0]

                if boq:
                        total_amount = flt(boq.total_amount) if boq.total_amount else 0.0

                frappe.db.sql("""
                        update `tabProject`
                        set project_value = {0}
                        where name = '{1}'
                """.format(flt(total_amount), self.project))
                '''

@frappe.whitelist()
def make_boq_adjustment(source_name, target_doc=None):
        def update_master(source_doc, target_doc, source_parent):
                target_doc.total_amount = 0.0
                
        def update_item(source_doc, target_doc, source_parent):
                pass
                
        doclist = get_mapped_doc("BOQ", source_name, {
                "BOQ": {
                        "doctype": "BOQ Adjustment",
                        "field_map": {
                                "name": "boq"
                        },
                        "postprocess": update_master
                },

                "BOQ Item": {
                        "doctype": "BOQ Adjustment Item",
                        "field_map": {
                                "name": "boq_item_name"
                        },
                        "postprocess": update_item
                }
        }, target_doc)

        return doclist
        
@frappe.whitelist()
def make_direct_invoice(source_name, target_doc=None):
        def update_master(source_doc, target_doc, source_parent):
                target_doc.invoice_title = str(target_doc.project) + "(Project Invoice)"
                target_doc.invoice_type = "Direct Invoice"
                target_doc.check_all = 1
                
        def update_item(source_doc, target_doc, source_parent):
                target_doc.act_quantity = flt(target_doc.invoice_quantity)
                target_doc.act_rate     = flt(target_doc.invoice_rate)
                target_doc.act_amount   = flt(target_doc.invoice_amount)
                target_doc.original_rate= flt(target_doc.invoice_rate)
                
        doclist = get_mapped_doc("BOQ", source_name, {
                "BOQ": {
                        "doctype": "Project Invoice",
                        "field_map": {
                                "project": "project"
                        },
                        "postprocess": update_master
                },

                "BOQ Item": {
                        "doctype": "Project Invoice BOQ",
                        "field_map": {
                                "name": "boq_item_name",
                                "balance_quantity": "invoice_quantity",
                                "rate": "invoice_rate",
                                "balance_amount": "invoice_amount",
                                "quantity": "original_quantity",
                                "amount": "original_amount"
                        },
                        "postprocess": update_item
                }
        }, target_doc)

        return doclist

@frappe.whitelist()
def make_mb_invoice(source_name, target_doc=None):
        def update_master(source_doc, target_doc, source_parent):
                target_doc.invoice_title = str(target_doc.project) + "(Project Invoice)"
                target_doc.invoice_type = "MB Based Invoice"
                target_doc.check_all_mb = 1
                
        doclist = get_mapped_doc("BOQ", source_name, {
                "BOQ": {
                        "doctype": "Project Invoice",
                        "field_map": {
                                "project": "project"
                        },
                        "postprocess": update_master
                }
        }, target_doc)

        return doclist


@frappe.whitelist()
def make_book_entry(source_name, target_doc=None):
        def update_master(source_doc, target_doc, source_parent):
                target_doc.check_all = 1
                
        def update_item(source_doc, target_doc, source_parent):
                target_doc.act_quantity = flt(target_doc.entry_quantity)
                target_doc.act_rate     = flt(target_doc.entry_rate)
                target_doc.act_amount   = flt(target_doc.entry_amount)
                target_doc.original_rate= flt(target_doc.entry_rate)
                
        doclist = get_mapped_doc("BOQ", source_name, {
                "BOQ": {
                        "doctype": "MB Entry",
                        "field_map": {
                                "project": "project"
                        },
                        "postprocess": update_master
                },

                "BOQ Item": {
                        "doctype": "MB Entry BOQ",
                        "field_map": {
                                "name": "boq_item_name",
                                "balance_quantity": "entry_quantity",
                                "rate": "entry_rate",
                                "balance_amount": "entry_amount",
                                "quantity": "original_quantity",
                                "amount": "original_amount"
                        },
                        "postprocess": update_item
                }
        }, target_doc)

        return doclist
