# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0		  SSK		                   02/09/2017         Original Version
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import money_in_words
from frappe.utils import cint, flt, nowdate

class ProjectAdvance(Document):
	def validate(self):
                self.set_status()
                self.set_defaults()
                
        def on_submit(self):
                if flt(self.advance_amount) <= 0:
                        frappe.throw(_("Please input valid advance amount."), title="Invalid Amount")
                        
                if str(self.advance_date) > '2017-09-30':
                        self.post_journal_entry()

        def before_cancel(self):
                self.set_status()
        
        def set_status(self):
                self.status = {
                        "0": "Draft",
                        "1": "Submitted",
                        "2": "Cancelled"
                }[str(self.docstatus or 0)]
                """
                if self.sales_invoice:
                        self.status = "Billed"
                """

        def set_defaults(self):
                if self.project:
                        base_project = frappe.get_doc("Project", self.project)

                        self.company          = base_project.company
                        self.customer         = base_project.customer
                        self.customer_details = base_project.customer_address
                        self.cost_center      = base_project.cost_center
                        self.branch           = base_project.branch

                        if base_project.status in ('Completed','Cancelled'):
                                frappe.throw(_("Operation not permitted on already {0} Project.").format(base_project.status),title="Project Advance: Invalid Operation")

                if self.customer:
                        base_customer = frappe.get_doc("Customer", self.customer)
                        self.customer_details = base_customer.customer_details
                        self.customer_currency= base_customer.default_currency
                
        def post_journal_entry(self):
                accounts = []

                # Fetching GLs
                #get_value(self, doctype, filters=None, fieldname="name", ignore=None, as_dict=False, debug=False):
                adv_gl = frappe.db.get_value(doctype="Projects Accounts Settings",fieldname="project_advance_account", as_dict=True)
                rev_gl = frappe.db.get_value(doctype="Branch",filters=self.branch,fieldname="revenue_bank_account", as_dict=True)
                
                if not adv_gl.project_advance_account:
                        frappe.throw(_("Advance GL is not defined in Projects Accounts Settings."))

                if not rev_gl.revenue_bank_account:
                        frappe.throw(_("Revenue GL is not defined in Branch '{0}'.").format(self.branch))

                # Fetching GL Account details
                adv_gl_det = frappe.db.get_value(doctype="Account", filters=adv_gl.project_advance_account, fieldname=["account_type","is_an_advance_account"], as_dict=True)
                rev_gl_det = frappe.db.get_value(doctype="Account", filters=rev_gl.revenue_bank_account, fieldname=["account_type","is_an_advance_account"], as_dict=True)
                
                accounts.append({"account": adv_gl.project_advance_account,
                                 "credit_in_account_currency": flt(self.advance_amount),
                                 "cost_center": self.cost_center,
                                 "party_check": 1,
                                 "party_type": "Customer",
                                 "party": self.customer,
                                 "account_type": adv_gl_det.account_type,
                                 "is_advance": "Yes" if adv_gl_det.is_an_advance_account == 1 else None,
                                 "reference_type": "Project Advance",
                                 "reference_name": self.name,
                                 "project": self.project
                })

                accounts.append({"account": rev_gl.revenue_bank_account,
                                 "debit_in_account_currency": flt(self.advance_amount),
                                 "cost_center": self.cost_center,
                                 "party_check": 0,
                                 "account_type": rev_gl_det.account_type,
                                 "is_advance": "Yes" if rev_gl_det.is_an_advance_account == 1 else None
                })                        


                '''
                je = frappe.get_doc({
                        "doctype": "Journal Entry",
                        "voucher_type": "Bank Entry",
                        "naming_series": "Bank Receipt Voucher",
                        "title": "Project Advance - "+self.project,
                        "user_remark": "Project Advance - "+self.project,
                        "posting_date": nowdate(),
                        "company": self.company,
                        "total_amount_in_words": money_in_words(self.advance_amount),
                        "accounts": accounts,
                        "branch": self.branch
                })
        
                if self.advance_amount:
                        je.insert()

                '''

                je = frappe.new_doc("Journal Entry")
                
                je.update({
                        "doctype": "Journal Entry",
                        "voucher_type": "Bank Entry",
                        "naming_series": "Bank Receipt Voucher",
                        "title": "Project Advance - "+self.project,
                        "user_remark": "Project Advance - "+self.project,
                        "posting_date": nowdate(),
                        "company": self.company,
                        "total_amount_in_words": money_in_words(self.advance_amount),
                        "accounts": accounts,
                        "branch": self.branch
                })
        
                if self.advance_amount:
                        je.save(ignore_permissions = True)
