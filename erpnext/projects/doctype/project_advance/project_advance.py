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
from frappe.utils import money_in_words, cint, flt, nowdate, now_datetime
from erpnext.setup.utils import get_company_currency
from erpnext.hr.doctype.travel_authorization.travel_authorization import get_exchange_rate
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba

class ProjectAdvance(Document):
	def validate(self):
                self.set_status()
                self.set_defaults()
                
        def on_submit(self):
                if flt(self.advance_amount) <= 0:
                        frappe.throw(_("Please input valid advance amount."), title="Invalid Amount")
                        
                if str(self.advance_date) > '2017-09-30':
                        self.post_journal_entry()
                self.project_advance_item_entry()
                
        def before_cancel(self):
                self.set_status()
                if self.journal_entry:
                        for t in frappe.get_all("Journal Entry", ["name"], {"name": self.journal_entry, "docstatus": ("<",2)}):
                                frappe.throw(_('Journal Entry  <a href="#Form/Journal Entry/{0}">{0}</a> for this transaction needs to be cancelled first').format(self.journal_entry),title='Not permitted')

        def on_cancel(self):
                self.project_advance_item_entry()

        def on_update_after_submit(self):
                self.project_advance_item_entry()

        def project_advance_item_entry(self):
                if self.docstatus == 2:
                        frappe.db.sql("delete from `tabProject Advance Item` where parent='{project}' and advance_name = '{advance_name}'".format(project=self.project, advance_name=self.name))
                else:
                        if not frappe.db.exists("Project Advance Item", {"parent": self.project, "advance_name": self.name}):
                                doc = frappe.get_doc("Project", self.project)
                                row = doc.append("project_advance_item", {})
                                row.advance_name        = self.name
                                row.advance_date        = self.advance_date
                                row.advance_amount      = flt(self.received_amount)+flt(self.paid_amount)
                                row.received_amount     = flt(self.received_amount)
                                row.paid_amount         = flt(self.paid_amount)
                                row.adjustment_amount   = flt(self.adjustment_amount)
                                row.balance_amount      = flt(self.balance_amount)
                                row.save(ignore_permissions=True)
                        else:
                                row = frappe.get_doc("Project Advance Item", {"parent": self.project, "advance_name": self.name})
                                row.advance_date        = self.advance_date
                                row.advance_amount      = flt(self.received_amount)+flt(self.paid_amount)
                                row.received_amount     = flt(self.received_amount)
                                row.paid_amount         = flt(self.paid_amount)
                                row.adjustment_amount   = flt(self.adjustment_amount)
                                row.balance_amount      = flt(self.balance_amount)
                                row.save(ignore_permissions=True)
                                
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
                if self.docstatus < 2:
                        self.journal_entry = None
                        self.journal_entry_status = None
                        self.paid_amount = 0
                        self.received_amount = 0
                        self.adjustment_amount = 0
                        self.balance_amount = 0
                        self.payment_type  = "Receive" if self.party_type == "Customer" else "Pay" 
                
                if self.project:
                        project = frappe.get_doc("Project", self.project)

                        if project.status in ('Completed','Cancelled'):
                                frappe.throw(_("Operation not permitted on already {0} Project.").format(base_project.status),title="Project Advance: Invalid Operation")
                                
                        self.cost_center      = project.cost_center
                        self.branch           = project.branch
                        self.company          = project.company

                        # fetch party information
                        self.party_type = self.party_type if self.party_type else project.party_type 
                        self.party      = self.party if self.party else project.party
                        if self.party_type and self.party:
                                doc = frappe.get_doc(self.party_type, self.party)
                                self.party_address = doc.get("customer_details") if self.party_type == "Customer" else doc.get("supplier_details") if self.party_type == "Supplier" else doc.get("employee_name")

                                if not self.currency:
                                        self.currency = get_company_currency(self.company) if self.party_type == "Employee" else doc.default_currency
                                
                if self.company and not self.exchange_rate:
                        company_currency = get_company_currency(self.company)
                        if company_currency == self.currency:
                                self.exchange_rate = 1
                        else:
                                self.exchange_rate = get_exchange_rate(self.currency, company_currency)
                        self.exchange_rate_original = self.exchange_rate

                if self.advance_amount_requested and not self.advance_amount:
                        self.advance_amount = flt(self.advance_amount_requested)*flt(self.exchange_rate)
                        
                
        def post_journal_entry(self):
                default_ba =  get_default_ba()
                # Fetching Advance GL
                adv_gl_field = "project_advance_account" if self.party_type == "Customer" else "advance_account_supplier" if self.party_type == "Supplier" else "advance_account_internal"
                adv_gl = frappe.db.get_value("Projects Accounts Settings",fieldname=adv_gl_field)  

                # added by phuntsho on june 24th, 2021
                if self.advance_account:
                        adv_gl = self.advance_account

                if not adv_gl:
                        frappe.throw(_("Advance GL is not defined in Projects Accounts Settings."))
                adv_gl_det = frappe.db.get_value(doctype="Account", filters=adv_gl, fieldname=["account_type","is_an_advance_account"], as_dict=True)

                # Fetching Revenue & Expense GLs
                rev_gl, exp_gl = frappe.db.get_value("Branch",self.branch,["revenue_bank_account", "expense_bank_account"])
                if self.payment_type == "Receive":
                        if not rev_gl:
                                frappe.throw(_("Revenue GL is not defined for this Branch '{0}'.").format(self.branch), title="Data Missing")
                        rev_gl_det = frappe.db.get_value(doctype="Account", filters=rev_gl, fieldname=["account_type","is_an_advance_account"], as_dict=True)
                else:
                        if not exp_gl:
                                frappe.throw(_("Expense GL is not defined for this Branch '{0}'.").format(self.branch), title="Data Missing")
                        exp_gl_det = frappe.db.get_value(doctype="Account", filters=exp_gl, fieldname=["account_type","is_an_advance_account"], as_dict=True)                                

                # Posting Journal Entry
                accounts = []
                accounts.append({"account": adv_gl,
                                 "credit_in_account_currency" if self.party_type == "Customer" else "debit_in_account_currency": flt(self.advance_amount),
                                 "cost_center": self.cost_center,
                                 "party_check": 1,
                                 "party_type": self.party_type,
                                 "party": self.party,
                                 "account_type": adv_gl_det.account_type,
                                 "is_advance": "Yes" if adv_gl_det.is_an_advance_account == 1 else None,
                                 "reference_type": "Project Advance",
                                 "reference_name": self.name,
                                 "project": self.project,
                                 "business_activity": default_ba
                })

                if self.party_type == "Customer":
                        accounts.append({"account": rev_gl,
                                         "debit_in_account_currency": flt(self.advance_amount),
                                         "cost_center": self.cost_center,
                                         "party_check": 0,
                                         "account_type": rev_gl_det.account_type,
                                         "is_advance": "Yes" if rev_gl_det.is_an_advance_account == 1 else "No",
                                         "business_activity": default_ba
                        })
                else:
                        accounts.append({"account": exp_gl,
                                         "credit_in_account_currency": flt(self.advance_amount),
                                         "cost_center": self.cost_center,
                                         "party_check": 0,
                                         "account_type": exp_gl_det.account_type,
                                         "is_advance": "Yes" if exp_gl_det.is_an_advance_account == 1 else "No",
                                         "business_activity": default_ba
                        })

                je = frappe.new_doc("Journal Entry")
                
                je.update({
                        "doctype": "Journal Entry",
                        "voucher_type": "Bank Entry",
                        "naming_series": "Bank Receipt Voucher" if self.payment_type == "Receive" else "Bank Payment Voucher",
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
                        self.db_set("journal_entry", je.name)
                        self.db_set("journal_entry_status", "Forwarded to accounts for processing payment on {0}".format(now_datetime().strftime('%Y-%m-%d %H:%M:%S')))
                        frappe.msgprint(_('Journal Entry <a href="#Form/Journal Entry/{0}">{0}</a> posted to accounts').format(je.name))
