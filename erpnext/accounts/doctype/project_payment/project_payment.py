# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# project_payment.py
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
2.0		  SHIV		                   05/09/2017         Original Version
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, getdate, get_url, nowdate
from frappe.model.mapper import get_mapped_doc
from frappe.utils import money_in_words
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.custom_utils import generate_receipt_no
import collections

class ProjectPayment(AccountsController):
	def __setup__(self):
                self.onload()
                
        def onload(self):
                if not self.get('__unsaved') and not self.get("references") and self.get("project"):
                        #self.load_references()
                        #self.load_advances()
                        pass

        def on_update(self):
                self.validate_invoice_balance()
                self.validate_advance_balance()

        def validate(self):
                self.set_status()
                self.set_defaults()
                self.validate_other_deductions()
                self.validate_tds()
                self.validate_allocated_amounts()
                self.load_boq_allocation()
		self.clearance_date = None

        def on_submit(self):
                self.update_invoice_balance()
                self.update_advance_balance()                
                self.update_boq_balance()
                self.make_gl_entries()

        def before_cancel(self):
                self.set_status()

        def on_cancel(self):
		if self.clearance_date:
                        frappe.throw("Already done bank reconciliation.")

                self.make_gl_entries()
                self.update_invoice_balance()
                self.update_advance_balance()
                self.update_boq_balance()

        def load_boq_allocation(self):
                self.details    = []
                items           = {}
                for inv in self.references:
                        boq            = {}
                        balance_amount = flt(inv.allocated_amount)
                        if inv.invoice_type == "MB Based Invoice":
                                # MB Based Invoice
                                if flt(inv.allocated_amount) > 0:
                                        mb_list = frappe.get_all("Project Invoice MB", ["entry_name","boq","subcontract","boq_type","entry_amount","price_adjustment_amount"], {"parent": inv.reference_name, "is_selected": 1}, order_by="boq, subcontract, parent")
                                        det = frappe.db.sql("""
                                                select
                                                        concat(boq,'_',ifnull(subcontract,'x'),'_',invoice_name,'_',entry_name) as `key`,
                                                        sum(ifnull(allocated_amount,0)) as received_amount
                                                from `tabProject Payment Detail`
                                                where parent != '{parent}'
                                                and invoice_name = '{invoice_name}'
                                                and docstatus = 1
                                                group by concat(boq,'_',ifnull(subcontract,'x'),'_',invoice_name,'_',entry_name)
                                        """.format(parent=self.name, invoice_name=inv.reference_name), as_dict=1)
                                        for d in det:
                                                if boq.has_key(d.key):
                                                        boq[d.key] += flt(d.received_amount)
                                                else:
                                                        boq.update({d.key : flt(d.received_amount)})
                                        
                                        for mb in mb_list:
                                                allocated_amount = 0.0
                                                received_amount  = 0.0
                                                key = str(mb.boq) + "_" + str(mb.subcontract if mb.subcontract else "x") + "_" + str(inv.reference_name) + "_" + str(mb.entry_name)
                                                
                                                if boq.has_key(key):
                                                        received_amount =  flt(boq[key])
                                                        
                                                if (flt(mb.entry_amount)+flt(mb.price_adjustment_amount)-flt(received_amount)) > 0 and flt(balance_amount) > 0:
                                                        if flt(balance_amount) >= (flt(mb.entry_amount)+flt(mb.price_adjustment_amount)-flt(received_amount)):
                                                                allocated_amount = (flt(mb.entry_amount) + flt(mb.price_adjustment_amount)-flt(received_amount))
                                                                balance_amount   = flt(balance_amount) - flt(allocated_amount)
                                                        else:
                                                                allocated_amount = flt(balance_amount)
                                                                balance_amount   = 0.0

                                                                
                                                        if items.has_key(key):
                                                                items[key] += flt(allocated_amount)
                                                        else:
                                                                items.update({key : flt(allocated_amount)})
                        else:
                                # Direct Invoice
                                if flt(inv.allocated_amount) > 0:
                                        allocated_amount = flt(balance_amount)
                                        received_amount  = 0.0
                                        
                                        boq, subcontract = frappe.db.get_value("Project Invoice", inv.reference_name, ["boq", "subcontract"])
                                        bal = frappe.db.sql("""
                                                select sum(ifnull(allocated_amount,0)) as received_amount
                                                from `tabProject Payment Detail`
                                                where invoice_name = '{invoice_name}'
                                                and parent != '{parent}'
                                                and docstatus = 1
                                        """.format(invoice_name=inv.reference_name, parent=self.name), as_dict=1)

                                        if bal:
                                                received_amount = flt(bal[0].received_amount)

                                        key = str(boq) + "_" + str(subcontract if subcontract else "x") + "_" + str(inv.reference_name) + "_" + "x"
                                        if (flt(allocated_amount)-flt(received_amount)) > 0:
                                                if items.has_key(key):
                                                        items[key] += flt(allocated_amount)
                                                else:
                                                        items.update({key : flt(allocated_amount)})
                        
                if items:
                        for key,value in collections.OrderedDict(sorted(items.items())).iteritems():
                                self.append("details",{
                                                        "boq": key.split('_')[0],
                                                        "subcontract": None if key.split('_')[1]=="x" else key.split('_')[1],
                                                        "invoice_name": key.split('_')[2],
                                                        "entry_name": None if key.split('_')[3]=="x" else key.split('_')[3],
                                                        "allocated_amount": flt(value)
                                })
                        
        def set_status(self):
                status = {}
                status.setdefault("Supplier",{}).update({"0": "Draft", "1": "Paid", "2": "Cancelled"})
                status.setdefault("Customer",{}).update({"0": "Draft", "1": "Received", "2": "Cancelled"})
                status.setdefault("Employee",{}).update({"0": "Draft", "1": "Received", "2": "Cancelled"})
                '''
                self.status = {
                        "0": "Draft",
                        "1": "Payment Received",
                        "2": "Cancelled"
                }[str(self.docstatus or 0)]
                '''
                self.status = status[self.party_type][str(self.docstatus or 0)]

        def set_defaults(self):
                if self.project:
                        base_project          = frappe.get_doc("Project", self.project)
                        self.company          = base_project.company
                        self.branch           = base_project.branch
                        self.cost_center      = base_project.cost_center

                        if base_project.status in ('Completed','Cancelled'):
                                frappe.throw(_("Operation not permitted on already {0} Project.").format(base_project.status),title="Project Payment: Invalid Operation")
                        
        def update_invoice_balance(self):
                for inv in self.references:
                        allocated_amount = 0.0
                        if flt(inv.allocated_amount) > 0:
                                total_balance_amount = frappe.db.get_value("Project Invoice", inv.reference_name, "total_balance_amount")
                                
                                if flt(total_balance_amount) < flt(inv.allocated_amount) and self.docstatus != 2:
                                        frappe.throw(_("Invoice#{0} : Allocated amount Nu. {1}/- cannot be more than Invoice Balance Nu. {2}/-").format(inv.reference_name, "{:,.2f}".format(flt(inv.allocated_amount)),"{:,.2f}".format(flt(total_balance_amount))))
                                else:
                                        allocated_amount = -1*flt(inv.allocated_amount) if self.docstatus == 2 else flt(inv.allocated_amount)

                                        inv_doc = frappe.get_doc("Project Invoice", inv.reference_name)
                                        if self.party_type == "Supplier":
                                                inv_doc.total_paid_amount = flt(inv_doc.total_paid_amount) + flt(allocated_amount)
                                        else:
                                                inv_doc.total_received_amount = flt(inv_doc.total_received_amount) + flt(allocated_amount)
                                        balance_amount                = flt(inv_doc.total_balance_amount) - flt(allocated_amount)
                                        inv_doc.total_balance_amount  = flt(balance_amount)
                                        inv_doc.status                = "Unpaid" if flt(balance_amount) > 0 else "Paid"
                                        inv_doc.save(ignore_permissions = True)

        def update_advance_balance(self):
                for adv in self.advances:
                        allocated_amount = 0.0
                        if flt(adv.allocated_amount) > 0:
                                balance_amount = frappe.db.get_value("Project Advance", adv.reference_name, "balance_amount")

                                if flt(balance_amount) < flt(adv.allocated_amount) and self.docstatus < 2:
                                        frappe.throw(_("Advance#{0} : Allocated amount Nu. {1}/- cannot be more than Advance Balance Nu. {2}/-").format(adv.reference_name, "{:,.2f}".format(flt(adv.allocated_amount)),"{:,.2f}".format(flt(balance_amount))))
                                else:
                                        allocated_amount = -1*flt(adv.allocated_amount) if self.docstatus == 2 else flt(adv.allocated_amount)

                                        adv_doc = frappe.get_doc("Project Advance", adv.reference_name)
                                        adv_doc.adjustment_amount = flt(adv_doc.adjustment_amount) + flt(allocated_amount)
                                        adv_doc.balance_amount    = flt(adv_doc.balance_amount) - flt(allocated_amount)
                                        adv_doc.save(ignore_permissions = True)
                                        
        def update_boq_balance(self):
                if not self.details:
                        frappe.throw(_("No BOQs found for update. Please contact the system administrator."),title="Invalid Data")
                        
                for d in self.details:
                        if flt(d.allocated_amount) > 0:
                                allocated_amount = -1*flt(d.allocated_amount) if self.docstatus == 2 else flt(d.allocated_amount)
                                doc = frappe.get_doc("Subcontract" if d.subcontract else "BOQ", d.subcontract if d.subcontract else d.boq)
                                balance_amount = flt(doc.balance_amount)
                                
                                if (flt(balance_amount)-flt(allocated_amount)) < 0:
                                        msg = '<b>Reference# : <a href="#Form/BOQ/{0}">{0}</a></b>'.format(d.boq)
                                        frappe.throw(_("Payment cannot exceed total BOQ value. <br/>{0}").format(msg), title="Invalid Data")

                                if self.party_type == "Supplier":
                                        doc.paid_amount = flt(doc.paid_amount) + flt(allocated_amount)
                                else:
                                        doc.received_amount = flt(doc.received_amount) + flt(allocated_amount)
                                doc.balance_amount  = flt(doc.balance_amount) - flt(allocated_amount)
                                doc.save(ignore_permissions = True)
                                                
        def validate_invoice_balance(self):
                for inv in self.references:
                        if flt(inv.allocated_amount) > 0:
                                total_balance_amount = frappe.db.get_value("Project Invoice", inv.reference_name, "total_balance_amount")
                                if flt(total_balance_amount) < flt(inv.allocated_amount):
                                        frappe.throw(_("<b>Invoice#{0} :</b> Allocated amount Nu. {1}/- cannot be more than Invoice Available Balance Amount Nu. {2}/-").format(inv.reference_name, "{:,.2f}".format(flt(inv.allocated_amount)),"{:,.2f}".format(flt(total_balance_amount))))

        def validate_advance_balance(self):
                for adv in self.advances:
                        if flt(adv.allocated_amount) > 0:
                                balance_amount = frappe.db.get_value("Project Advance", adv.reference_name, "balance_amount")
                                if flt(balance_amount) < flt(adv.allocated_amount):
                                        frappe.throw(_("Advance#{0} : Allocated amount Nu. {1}/- cannot be more than advance available balance amount Nu. {2}/-").format(adv.reference_name, "{:,.2f}".format(flt(adv.allocated_amount)),"{:,.2f}".format(flt(total_balance_amount))))                                        
                
        def validate_other_deductions(self):
                for ded in self.deductions:
                       if not ded.account and flt(ded.amount) > 0:
                               frappe.throw(_("Row#{0} : Please select a valid account under `Other Deductions`.").format(ded.idx), title="Missing Data")

        def validate_tds(self):
                if not self.tds_account and flt(self.tds_amount) > 0.0:
                        frappe.throw(_("Please select a valid TDS Account."),title="Missing Data")

        def validate_allocated_amounts(self):
                tot_adv_amount = 0.0
                tot_inv_amount = 0.0

                if flt(self.total_amount,2) <= 0:
                        frappe.throw(_("Total amount should be greater than zero"),title="Invalid Data")
                        
                for adv in self.advances:
                        tot_adv_amount += flt(adv.allocated_amount,2)
                        if flt(adv.allocated_amount,2) > flt(adv.total_amount,2):
                                frappe.throw(_("Advance#{0} : Allocated amount cannot be more than available balance").format(adv.reference_name))

                for inv in self.references:
                        tot_inv_amount += flt(inv.allocated_amount,2)
                        if flt(inv.allocated_amount,2) > flt(inv.total_amount,2):
                                frappe.throw(_("Invoice#{0} : Allocated amount cannot be more than available balance").format(inv.reference_name))                        

                if flt(tot_adv_amount,2) > flt(tot_inv_amount,2):
                        frappe.throw(_("Total advance allocated Nu. {0}/- cannot be more than total invoice amount allocated Nu. {1}/-.".format("{:,.2f}".format(flt(tot_adv_amount)), "{:,.2f}".format(flt(tot_inv_amount)))))

                if flt(self.total_amount,2) > flt(tot_inv_amount,2):
                        frappe.throw(_("Total Amount({0}) cannot be more than Total Invoice Amount Allocated({1})").format(flt(self.total_amount),flt(tot_inv_amount)))
                        
        def load_references(self):
                self.references = []
                for invoice in self.get_references():
                        self.append("references",{
                                "reference_doctype": "Project Invoice",
                                "reference_name": invoice.name,
                                "total_amount": invoice.total_balance_amount
                        })

        def load_advances(self):
                self.advances = []
                for advance in self.get_advances():
                        self.append("advances",{
                                "reference_doctype": "Project Advance",
                                "reference_name": advance.name,
                                "total_amount": advance.balance_amount
                        })


        def get_references(self):
                return frappe.get_all("Project Invoice","*",filters={"project":self.project, "docstatus":1, "total_balance_amount": [">",0]})

        def get_advances(self):
                return frappe.get_all("Project Advance","*",filters={"project":self.project, "docstatus":1, "balance_amount": [">",0]})

        
	def get_series(self):
		fiscal_year = getdate(self.posting_date).year
		generate_receipt_no(self.doctype, self.name, self.branch, fiscal_year)

        def make_gl_entries(self):
                if flt(self.total_amount) > 0:
                        from erpnext.accounts.general_ledger import make_gl_entries
                        gl_entries = []
                        currency = frappe.db.get_value(doctype=self.party_type, filters=self.party, fieldname=["default_currency"], as_dict=True)
                        
                        bank_account = self.expense_bank_account if self.party_type == "Supplier" else self.revenue_bank_account
                        
                        # Bank Entry
                        if flt(self.paid_amount) > 0:
                                if not bank_account:
                                        frappe.throw(_("Please set {0} Bank Account under Branch master").format("Expense" if self.party_type == "Supplier" else "Revenue"))
                                        
                                bank_account_type = frappe.db.get_value(doctype="Account", filters=bank_account, fieldname=["account_type"])
                                
                                gl_entries.append(
                                        self.get_gl_dict({"account": bank_account,
                                                         "credit" if self.party_type == "Supplier" else "debit": flt(self.paid_amount),
                                                         "credit_in_account_currency" if self.party_type == "Supplier" else "debit_in_account_currency": flt(self.paid_amount),
                                                         "cost_center": self.cost_center,
                                                         "party_check": 0,
                                                         "account_type": bank_account_type,
                                                         "is_advance": "No",
                                                         "party_type": self.party_type if bank_account_type in ("Payable","Receivable") else None,
                                                         "party": self.party if bank_account_type in ("Payable","Receivable") else None,
                                        }, currency.default_currency)
                                )

                        # Advance Entry
                        tot_advance = 0.0
                        for adv in self.advances:
                                tot_advance += flt(adv.allocated_amount)

                        if flt(tot_advance) > 0:
                                advance_map = {"Supplier": "advance_account_supplier", "Customer": "project_advance_account", "Employee": "advance_account_internal"}
                                advance_account = frappe.db.get_value(doctype="Projects Accounts Settings",fieldname=advance_map[self.party_type])

                                if not advance_account:
                                        frappe.throw(_("Project Advance Account for party type {0} is not defined under Projects Accounts Settings").format(self.party_type))
                                        
                                advance_account_type = frappe.db.get_value(doctype="Account", filters=advance_account, fieldname=["account_type"])                   
                                        
                                gl_entries.append(
                                        self.get_gl_dict({"account": advance_account,
                                                         "credit" if self.party_type == "Supplier" else "debit": flt(tot_advance),
                                                         "credit_in_account_currency" if self.party_type == "Supplier" else "debit_in_account_currency": flt(tot_advance),
                                                         "cost_center": self.cost_center,
                                                         "party_check": 1 if advance_account_type in ("Payable","Receivable") else 0,
                                                         "party_type": self.party_type,
                                                         "party": self.party,
                                                         "account_type": advance_account_type,
                                                         "is_advance": "No",
                                                         "reference_type": "Project Payment",
                                                         "reference_name": self.name,
                                                         "project": self.project
                                        }, currency.default_currency)
                                )

                        # Other Deductions
                        for ded in self.deductions:
                                if flt(ded.amount) > 0:
                                        if not ded.account:
                                                frappe.throw(_("Row#{0}: Account cannot be blank under other deductions.").format(ded.idx))
                                                
                                        deduction_account_type = frappe.db.get_value(doctype="Account", filters=ded.account, fieldname=["account_type"])
                                        gl_entries.append(
                                                self.get_gl_dict({"account": ded.account,
                                                                 "credit" if self.party_type == "Supplier" else "debit": flt(ded.amount),
                                                                 "credit_in_account_currency" if self.party_type == "Supplier" else "debit_in_account_currency": flt(ded.amount),
                                                                 "cost_center": self.cost_center,
                                                                 "account_type": deduction_account_type,
                                                                 "is_advance": "No",
                                                                 "reference_type": "Project Payment",
                                                                 "reference_name": self.name,
                                                                 "project": self.project,
                                                                 "party_check": 1 if deduction_account_type in ("Payable","Receivable") else 0,
                                                                 "party_type": self.party_type,
                                                                 "party": self.party
                                                }, currency.default_currency)
                                        )

                        # TDS Deductions
                        if flt(self.tds_amount) > 0:
                                if not self.tds_account:
                                        frappe.throw("TDS Account cannot be blank.")
                                        
                                tds_account_type = frappe.db.get_value(doctype="Account", filters=self.tds_account, fieldname=["account_type"])

                                gl_entries.append(
                                        self.get_gl_dict({"account": self.tds_account,
                                                        "credit" if self.party_type == "Supplier" else "debit": flt(self.tds_amount),
                                                        "credit_in_account_currency" if self.party_type == "Supplier" else "debit_in_account_currency": flt(self.tds_amount),
                                                        "cost_center": self.cost_center,
                                                        "account_type": tds_account_type,
                                                        "is_advance": "No",
                                                        "reference_type": "Project Payment",
                                                        "reference_name": self.name,
                                                        "project": self.project
                                        }, currency.default_currency)
                                )
                        # Receivable Account
                        if flt(self.total_amount) > 0:
                                sundry_map  = {"Supplier": "default_payable_account", "Customer": "default_receivable_account", "Employee": "default_receivable_account"}
                                sundry_account = frappe.db.get_value(doctype="Company",filters=self.company,fieldname=sundry_map[self.party_type])
                                
                                if not sundry_account:
                                        frappe.throw(_("Default {0} Account is not defined in Company Settings").format("Payable" if self.party_type == "Supplier" else "Receivable"))

                                sundry_account_type = frappe.db.get_value(doctype="Account", filters=sundry_account, fieldname=["account_type"])
                                        
                                gl_entries.append(
                                        self.get_gl_dict({"account": sundry_account,
                                                         "debit" if self.party_type == "Supplier" else "credit": flt(self.total_amount),
                                                         "debit_in_account_currency" if self.party_type == "Supplier" else "credit_in_account_currency": flt(self.total_amount),
                                                         "cost_center": self.cost_center,
                                                         "party_check": 1,
                                                         "party_type": self.party_type,
                                                         "party": self.party,
                                                         "account_type": sundry_account_type,
                                                         "is_advance": "No",
                                                         "reference_type": "Project Payment",
                                                         "reference_name": self.name,
                                                         "project": self.project
                                        }, currency.default_currency)
                                )
                                 
                        make_gl_entries(gl_entries, cancel=(self.docstatus == 2),update_outstanding="No", merge_entries=False)
                        
        def post_journal_entry(self):
                accounts    = []
                tot_advance = 0.0
                
                # Bank Entry
                if flt(self.paid_amount) > 0:
                        #rev_gl = frappe.db.get_value(doctype="Branch",filters=self.branch,fieldname="revenue_bank_account", as_dict=True)
                        rev_gl_det = frappe.db.get_value(doctype="Account", filters=self.revenue_bank_account, fieldname=["account_type"], as_dict=True)
                        accounts.append({"account": self.revenue_bank_account,
                                         "debit_in_account_currency": flt(self.paid_amount),
                                         "cost_center": self.cost_center,
                                         "party_check": 0,
                                         "account_type": rev_gl_det.account_type,
                                         "is_advance": "No"
                        })

                # Advance Entry
                for adv in self.advances:
                        tot_advance += flt(adv.allocated_amount)

                if flt(tot_advance) > 0:        
                        adv_gl = frappe.db.get_value(doctype="Projects Accounts Settings",fieldname="project_advance_account", as_dict=True)
                        adv_gl_det = frappe.db.get_value(doctype="Account", filters=adv_gl.project_advance_account, fieldname=["account_type"], as_dict=True)
                        accounts.append({"account": adv_gl.project_advance_account,
                                         "debit_in_account_currency": flt(tot_advance),
                                         "cost_center": self.cost_center,
                                         "party_check": 1,
                                         "party_type": "Customer",
                                         "party": self.party,
                                         "account_type": adv_gl_det.account_type,
                                         "is_advance": "No",
                                         "reference_type": "Project Payment",
                                         "reference_name": self.name,
                                         "project": self.project
                        })

                # Other Deductions
                for ded in self.deductions:
                        if flt(ded.amount) > 0 and ded.account:
                                ded_gl_det = frappe.db.get_value(doctype="Account", filters=ded.account, fieldname=["account_type"], as_dict=True)
                                accounts.append({"account": ded.account,
                                                 "debit_in_account_currency": flt(ded.amount),
                                                 "cost_center": self.cost_center,
                                                 "account_type": ded_gl_det.account_type,
                                                 "is_advance": "No",
                                                 "reference_type": "Project Payment",
                                                 "reference_name": self.name,
                                                 "project": self.project
                                })

                # TDS Deductions
                if flt(self.tds_amount) > 0 and self.tds_account:
                        tds_gl_det = frappe.db.get_value(doctype="Account", filters=self.tds_account, fieldname=["account_type"], as_dict=True)

                        accounts.append({"account": self.tds_account,
                                        "debit_in_account_currency": flt(self.tds_amount),
                                        "cost_center": self.cost_center,
                                        "account_type": tds_gl_det.account_type,
                                        "is_advance": "No",
                                        "reference_type": "Project Payment",
                                        "reference_name": self.name,
                                        "project": self.project
                                        })
                # Receivable Account
                if flt(self.total_amount) > 0:
                        rec_gl = frappe.db.get_value(doctype="Company",filters=self.company,fieldname="default_receivable_account", as_dict=True)
                        rec_gl_det = frappe.db.get_value(doctype="Account", filters=rec_gl.default_receivable_account, fieldname=["account_type"], as_dict=True)

                        accounts.append({"account": rec_gl.default_receivable_account,
                                         "credit_in_account_currency": flt(self.total_amount),
                                         "cost_center": self.cost_center,
                                         "party_check": 1,
                                         "party_type": "Customer",
                                         "party": self.party,
                                         "account_type": rec_gl_det.account_type,
                                         "is_advance": "No",
                                         "reference_type": "Project Payment",
                                         "reference_name": self.name,
                                         "project": self.project
                        })                         
                         
                        je = frappe.get_doc({
                                "doctype": "Journal Entry",
                                "voucher_type": "Bank Entry",
                                "naming_series": "Bank Receipt Voucher",
                                "title": "Project Payment - "+self.project,
                                "user_remark": "Project Payment - "+self.project,
                                "posting_date": nowdate(),
                                "company": self.company,
                                "total_amount_in_words": money_in_words(self.total_amount),
                                "accounts": accounts,
                                "branch": self.branch
                        })
                
                        je.submit()

# ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++        
# Following method is created by SHIV on 05/09/2017
@frappe.whitelist()
def make_project_payment(source_name, target_doc=None):
        def update_master(source_doc, target_doc, source_partent):
                target_doc.payment_type = "Pay" if source_doc.party_type == "Supplier" else "Receive"
                target_doc.naming_series = "Bank Payment Voucher" if source_doc.party_type == "Supplier" else "Bank Receipt Voucher"
                
        def update_reference(source_doc, target_doc, source_parent):
                pass
                
        doclist = get_mapped_doc("Project Invoice", source_name, {
                "Project Invoice": {
                                "doctype": "Project Payment",
                                "field_map":{
                                        "project": "project",
                                        "branch": "branch",
                                        "customer": "customer",
                                        "name": "reference_name",
                                        "party": "pay_to_recd_from"
                                },
                                "postprocess": update_master
                        },
        }, target_doc)
        return doclist

# Following code added by SHIV on 2019/06/19
@frappe.whitelist()
def get_invoice_list(project, party_type, party):
        result = frappe.db.sql("""
                select *
                from `tabProject Invoice`
                where project = '{project}'
                and party_type = '{party_type}'
                and party = '{party}'
                and docstatus = 1
                and total_balance_amount > 0
                """.format(project=project, party_type=party_type, party=party), as_dict=True)

        return result

# Following code commented by SHIV on 2019/06/19
'''
@frappe.whitelist()
def get_invoice_list(project, reference_name):
        if reference_name == "dummy":
                reference_name = None
                
        result = frappe.db.sql("""
                select *
                from `tabProject Invoice`
                where project = %s
                and docstatus = 1
                and total_balance_amount > 0
                and name = ifnull(%s,name)
                """, (project, reference_name), as_dict=True)

        return result
'''

# Following code added by SHIV on 2019/06/19
@frappe.whitelist()
def get_advance_list(project, party_type, party):
        result = frappe.db.sql("""
                select *
                from `tabProject Advance`
                where project = '{project}'
                and party_type = '{party_type}'
                and party = '{party}'
                and docstatus = 1
                and balance_amount > 0
                """.format(project=project, party_type=party_type, party=party), as_dict=True)

        return result

# Following code commented by SHIV on 2019/06/19
'''
@frappe.whitelist()
def get_advance_list(project):
        result = frappe.db.sql("""
                select *
                from `tabProject Advance`
                where project = %s
                and docstatus = 1
                and balance_amount > 0
                """, (project), as_dict=True)

        return result
'''
# +++++++++++++++++++++ Ver 2.0 ENDS +++++++++++++++++++++
