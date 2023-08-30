# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, flt, getdate, today

class BOQAdjustment(Document):
	def validate(self):
                self.validate_boq_item()

        def on_submit(self):
                self.update_boq_and_project()

        def on_cancel(self):
                self.update_boq_and_project()

        def validate_boq_item(self):
                for i in self.boq_item:
                        if not i.boq_item_name:
                                frappe.throw(_("Row#{0} : Adding new items not permitted.").format(i.idx), title="Not permitted")
                                
                        if i.is_group:
                                if flt(i.adjustment_quantity) or flt(i.adjustment_amount):
                                        frappe.throw(_("Row#{0} : Adjustments against group items not permitted.").format(i.idx), title="Not permitted")

                        i.balance_quantity, i.balance_amount = frappe.db.get_value("BOQ Item", i.boq_item_name, ["balance_quantity","balance_amount"])
                        if (flt(i.balance_amount)+flt(i.adjustment_amount)) < 0:
                                msg = '<b>Reference# : <a href="#Form/BOQ/{0}">{0}</a></b>'.format(self.boq)
                                frappe.throw(_("Row#{0} : Adjustment beyond available balance is not allowed.<br>{1}").format(i.idx,msg), title="Insufficient Balance")

        def update_boq_and_project(self):
                total_amount = 0.0
                
                for i in self.boq_item:
                        quantity            = 0.0
                        rate                = 0.0

                        adjustment_quantity = -1*flt(i.adjustment_quantity) if self.docstatus == 2 else flt(i.adjustment_quantity)
                        adjustment_amount   = -1*flt(i.adjustment_amount) if self.docstatus == 2 else flt(i.adjustment_amount)
                        adjustment_rate     = flt(adjustment_amount)
                        
                        total_amount       += flt(adjustment_amount) 

                        adjustment_quantity = 0.0 if self.boq_type == "Milestone Based" else flt(adjustment_quantity)
                        adjustment_rate     = flt(adjustment_amount) if self.boq_type == "Milestone Based" else 0.0
                        
                        i.balance_quantity, i.balance_amount = frappe.db.get_value("BOQ Item", i.boq_item_name, ["balance_quantity","balance_amount"])
                        if (flt(i.balance_amount)+flt(adjustment_amount)) < 0:
                                msg = '<b>Reference# : <a href="#Form/BOQ/{0}">{0}</a></b>'.format(self.boq)
                                frappe.throw(_("Row#{0} : Cannot cancel as the adjusted amount is already invoiced.<br>{1}").format(i.idx,msg), title="Not permitted")

                        # Update BOQ Item
                        bi_doc                  = frappe.get_doc("BOQ Item", i.boq_item_name)
                        quantity                = flt(bi_doc.quantity) + flt(adjustment_quantity)
                        rate                    = flt(bi_doc.rate) + flt(adjustment_rate)
                        bi_doc.amount           = flt(bi_doc.amount) + flt(adjustment_amount)
                        bi_doc.balance_quantity = flt(bi_doc.balance_quantity) + flt(adjustment_quantity)
                        bi_doc.balance_amount   = flt(bi_doc.balance_amount) + flt(adjustment_amount)
                        bi_doc.save(ignore_permissions = True)
                        frappe.db.set_value("BOQ Item", i.boq_item_name, "quantity", quantity)
                        frappe.db.set_value("BOQ Item", i.boq_item_name, "rate", rate)

                if total_amount:
                        # Update BOQ
                        boq_doc = frappe.get_doc("BOQ", self.boq)
                        boq_doc.total_amount   = flt(boq_doc.total_amount) + flt(total_amount)
                        boq_doc.balance_amount = flt(boq_doc.balance_amount) + flt(total_amount)
                        boq_doc.save(ignore_permissions = True)

                        # Update Project
                        pro_doc = frappe.get_doc("Project", self.project)
			pro_doc.flags.dont_sync_tasks = True
                        pro_doc.project_value = flt(pro_doc.project_value) + flt(total_amount)
                        pro_doc.save(ignore_permissions = True)

