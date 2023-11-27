# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cstr, flt, fmt_money, formatdate, nowdate
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.custom_utils import check_uncancelled_linked_doc, check_future_date

class HireChargeInvoice(AccountsController):
    def validate(self):
        check_future_date(self.posting_date)
        self.check_advances(self.ehf_name)
        if self.total_invoice_amount <= 0:
            frappe.throw("Total Invoice Amount should be greater than 0")
        if self.balance_amount < 0:
            frappe.throw("Balance amount cannot be negative")
        self.outstanding_amount = self.balance_amount
        self.set_advance_data()

    def set_advance_data(self):
        advance_amount = 0
        balance_amount = 0
        for a in self.advances:
            a.balance_advance_amount = flt(a.actual_advance_amount) - flt(a.allocated_amount)
            if flt(a.balance_advance_amount) < 0:
                frappe.throw("Allocated Amount should be smaller than Advance Available")
            advance_amount = flt(advance_amount) + flt(a.allocated_amount)
            balance_amount = flt(balance_amount) + flt(a.balance_advance_amount)
        self.advance_amount = advance_amount
        self.balance_advance_amount = balance_amount

    def on_submit(self):
        self.check_vlogs()
        self.set_advance_data()
        self.update_advance_amount();
        self.update_vlogs(1)
        if self.owned_by == "CDCL":
            self.post_journal_entry()
            self.db_set("outstanding_amount", 0)
        else:
            self.make_gl_entries()
        if self.close:
            self.refund_of_excess_advance()
        self.check_close()

    # def before_cancel(self):
    #     if frappe.session.user == "Administrator":
    #         self.make_gl_entries()

    def on_cancel(self):
        # if frappe.session.user == "Administrator":
        #     frappe.throw('Dont cancel')
        if self.owned_by != "CDCL":
            self.make_gl_entries()
            #self.make_gl_entries_on_cancel()
        check_uncancelled_linked_doc(self.doctype, self.name)
        cl_status = frappe.db.get_value("Journal Entry", self.invoice_jv, "docstatus")
        if cl_status and cl_status != 2:
            frappe.throw("You need to cancel the journal entry ("+ str(self.invoice_jv) + ")related to this invoice first!")
        if self.payment_jv:
            cl_status = frappe.db.get_value("Journal Entry", self.payment_jv, "docstatus")
            if cl_status and cl_status != 2:
                frappe.throw("You need to cancel the journal entry ("+ str(self.payment_jv) + ")related to this invoice first!")
        self.readjust_advance()
        if self.close:
            self.check_advances()
        self.update_vlogs(0)
        self.check_close(1)
        self.db_set("invoice_jv", "")
        self.db_set("payment_jv", "")

    def check_advances(self, cancel=None):
        hire_name = self.ehf_name
        if cancel:
            hire_name = self.name
        advance = frappe.db.sql("select t1.name from `tabJournal Entry` t1, `tabJournal Entry Account` t2 where t1.name = t2.parent and t2.is_advance = 'Yes' and (t1.docstatus = 1 or t1.docstatus = 0) and t2.reference_name = \'" + str(hire_name)  + "\'", as_dict=True)
        if advance and not cancel and not self.advances:
            frappe.msgprint("There is a Advance Payment for this Hire Form. You might want to pull it using 'Get Advances' button")
        if advance and cancel:
            frappe.throw("Cancel the Refund Journal Entry " + str(advance[0].name) + " before cancelling")

    def update_advance_amount(self):
        lst = []
        for d in self.get('advances'):
            if flt(d.allocated_amount) > 0:
                args = frappe._dict({
                    'voucher_type': 'Journal Entry',
                    'voucher_no' : d.jv_name,
                    'voucher_detail_no' : d.reference_row,
                    'against_voucher_type' : self.doctype,
                    'against_voucher'  : self.name,
                    'account' : d.advance_account,
                    'party_type': "Customer",
                    'party': self.customer,
                    'is_advance' : 'Yes',
                    'dr_or_cr' : "credit_in_account_currency",
                    'unadjusted_amount' : flt(d.actual_advance_amount),
                    'allocated_amount' : flt(d.allocated_amount),
                    'exchange_rate': 1,
                })
                lst.append(args)

        if lst:
            from erpnext.accounts.utils import reconcile_against_document
            reconcile_against_document(lst)


    def check_vlogs(self):
        for a in self.items:
            ic = frappe.db.get_value("Vehicle Logbook", a.vehicle_logbook, "invoice_created")			
            if ic:
                frappe.throw("Logbook <b>" + str(a.vehicle_logbook) + "</b> has already been invoiced")

    def update_vlogs(self, value):
        for a in self.items:
            logbook = frappe.get_doc("Vehicle Logbook", a.vehicle_logbook)			
            logbook.db_set("invoice_created", value)

    ##
    # make necessary journal entry
    ##
    def post_journal_entry(self):
        receivable_account = frappe.db.get_single_value("Maintenance Accounts Settings", "default_receivable_account")
        if not receivable_account:
            frappe.throw("Setup Reveivable Account in Maintenance Accounts Settings")
        advance_account = frappe.db.get_single_value("Maintenance Accounts Settings", "default_advance_account")
        if not advance_account:
            frappe.throw("Setup Advance Account in Maintenance Accounts Settings")
        hire_account = frappe.db.get_single_value("Maintenance Accounts Settings", "hire_revenue_account")
        if not hire_account:
            frappe.throw("Setup Hire Account in Maintenance Accounts Settings")
        ic_account = frappe.db.get_single_value("Accounts Settings", "intra_company_account")
        if not ic_account:
            frappe.throw("Setup Intra-Company Account in Accounts Settings")
        hr_account = frappe.db.get_single_value("Maintenance Accounts Settings", "hire_revenue_internal_account")
        if not hr_account:
            frappe.throw("Setup Hire Revenue Internal Account in Maintenance Accounts Settings")
        hea_account = frappe.db.get_single_value("Maintenance Accounts Settings", "hire_expense_account")
        if not hea_account:
            frappe.throw("Setup Hire Expense Internal Account in Maintenance Accounts Settings")
        discount_account = frappe.db.get_single_value("Maintenance Accounts Settings", "discount_account")
        if not discount_account:
            frappe.throw("Setup Discount Account in Maintenance Accounts Settings")

        je = frappe.new_doc("Journal Entry")
        je.flags.ignore_permissions = 1 
        je.title = "Hire Charge Invoice (" + self.name + ")"
        je.voucher_type = 'Hire Invoice'
        je.naming_series = 'Hire Invoice'
        je.remark = 'Payment against : ' + self.name;
        je.posting_date = self.posting_date
        je.branch = self.branch

        if self.owned_by == "CDCL":
            customer_cost_center = frappe.db.get_value("Equipment Hiring Form", self.ehf_name, "customer_cost_center")
            je.append("accounts", {
                    "account": hea_account,
                    "reference_type": "Hire Charge Invoice",
                    "reference_name": self.name,
                    "cost_center": customer_cost_center,
                    "debit_in_account_currency": flt(self.total_invoice_amount),
                    "debit": flt(self.total_invoice_amount),
                })
            je.append("accounts", {
                    "account": ic_account,
                    "reference_type": "Hire Charge Invoice",
                    "reference_name": self.name,
                    "cost_center": customer_cost_center,
                    "credit_in_account_currency": flt(self.total_invoice_amount),
                    "credit": flt(self.total_invoice_amount),
                })
            je.append("accounts", {
                    "account": ic_account,
                    "reference_type": "Hire Charge Invoice",
                    "reference_name": self.name,
                    "cost_center": self.cost_center,
                    "debit_in_account_currency": flt(self.total_invoice_amount),
                    "debit": flt(self.total_invoice_amount),
                })
            je.append("accounts", {
                    "account": hr_account,
                    "reference_type": "Hire Charge Invoice",
                    "reference_name": self.name,
                    "cost_center": self.cost_center,
                    "credit_in_account_currency": flt(self.total_invoice_amount),
                    "credit": flt(self.total_invoice_amount),
                })
            je.insert()

        else:		
            if self.total_invoice_amount > 0:
                je.append("accounts", {
                        "account": hire_account,
                        "reference_type": "Hire Charge Invoice",
                        "reference_name": self.name,
                        "cost_center": self.cost_center,
                        "credit_in_account_currency": flt(self.total_invoice_amount),
                        "credit": flt(self.total_invoice_amount),
                    })

            if self.advance_amount > 0:
                je.append("accounts", {
                        "account": advance_account,
                        "party_type": "Customer",
                        "party": self.customer,
                        "reference_type": "Hire Charge Invoice",
                        "reference_name": self.name,
                        "cost_center": self.cost_center,
                        "debit_in_account_currency": flt(self.advance_amount),
                        "debit": flt(self.advance_amount),
                    })

            if self.discount_amount > 0:
                je.append("accounts", {
                        "account": discount_account,
                        "party_type": "Customer",
                        "party": self.customer,
                        "reference_type": "Hire Charge Invoice",
                        "reference_name": self.name,
                        "cost_center": self.cost_center,
                        "debit_in_account_currency": flt(self.discount_amount),
                        "debit": flt(self.discount_amount),
                    })

            if self.balance_amount > 0:
                je.append("accounts", {
                        "account": receivable_account,
                        "party_type": "Customer",
                        "party": self.customer,
                        "reference_type": "Hire Charge Invoice",
                        "reference_name": self.name,
                        "cost_center": self.cost_center,
                        "debit_in_account_currency": flt(self.balance_amount),
                        "debit": flt(self.balance_amount),
                    })

            je.submit()
            
        self.db_set("invoice_jv", je.name)


    def readjust_advance(self):
        frappe.db.sql("update `tabJournal Entry Account` set reference_type=%s,reference_name=%s where reference_type=%s and reference_name=%s and docstatus = 1", ("Equipment Hiring Form", self.ehf_name, "Hire Charge Invoice", self.name))

    def check_close(self, cancel=0):
        if self.close:
            hire = frappe.get_doc("Equipment Hiring Form", self.ehf_name)
            if cancel:
                hire.db_set("payment_completed", 0)
            else:
                hire.db_set("payment_completed", 1)

    def make_gl_entries(self):
        from erpnext.accounts.general_ledger import make_gl_entries
        if self.total_invoice_amount > 0:
            gl_entries = []
            self.posting_date = self.posting_date

        receivable_account = frappe.db.get_single_value("Maintenance Accounts Settings", "default_receivable_account")
        if not receivable_account:
            frappe.throw("Setup Reveivable Account in Maintenance Accounts Settings")
        advance_account = frappe.db.get_single_value("Maintenance Accounts Settings", "default_advance_account")
        if not advance_account:
            frappe.throw("Setup Advance Account in Maintenance Accounts Settings")
        hire_account = frappe.db.get_single_value("Maintenance Accounts Settings", "hire_revenue_account")
        if not hire_account:
            frappe.throw("Setup Hire Account in Maintenance Accounts Settings")
        discount_account = frappe.db.get_single_value("Maintenance Accounts Settings", "discount_account")
        if not discount_account:
            frappe.throw("Setup Discount Account in Maintenance Accounts Settings")  
        gl_entries.append(
            self.get_gl_dict({
                                "account": hire_account,
                "               against_voucher_type": "Equipment Hiring Form",
                                "against": self.ehf_name,
                                "credit": self.total_invoice_amount,
                                "credit_in_account_currency": self.total_invoice_amount,
                                "cost_center": self.cost_center
                        }, self.currency)
        )

        if self.advance_amount:
            gl_entries.append(
                self.get_gl_dict({
                        "account": advance_account,
                        "against": self.customer,
                        "party_type": "Customer",
                        "party": self.customer,
                        "debit": self.advance_amount,
                        "debit_in_account_currency": self.advance_amount,
                        "cost_center": self.cost_center
                }, self.currency)
            )

        if self.discount_amount:
            gl_entries.append(
                self.get_gl_dict({
                        "account": discount_account,
                        "against": self.customer,
                        "debit": self.discount_amount,
                        "debit_in_account_currency": self.discount_amount,
                        "cost_center": self.cost_center
                }, self.currency)
            )
        if self.balance_amount:
            gl_entries.append(
                self.get_gl_dict({
                        "account": receivable_account,
                        "against": self.customer,
                        "party_type": "Customer",
                        "party": self.customer,
                        "against_voucher": self.name,
                        "against_voucher_type": self.doctype,
                        "debit": self.balance_amount,
                        "debit_in_account_currency": self.balance_amount,
                        "cost_center": self.cost_center
                }, self.currency)
            )
        # frappe.msgprint(format(gl_entries))
        make_gl_entries(gl_entries, cancel=(self.docstatus == 2),update_outstanding="No", merge_entries=False)

    def refund_of_excess_advance(self):
        revenue_bank_account = frappe.db.get_value("Branch", self.branch, "revenue_bank_account")
        if not revenue_bank_account:
            frappe.throw("Setup Default Revenue Bank Account for your Branch")

        je = frappe.new_doc("Journal Entry")
        je.flags.ignore_permissions = 1 
        je.title = "Advance Refund for Hire Charge Form  (" + self.ehf_name + ")"
        je.voucher_type = 'Bank Entry'
        je.naming_series = 'Bank Payment Voucher'
        je.remark = 'Payment against : ' + self.ehf_name;
        je.posting_date = self.posting_date
        je.branch = self.branch

        total_amount = 0

        for a in self.advances:
            if flt(a.actual_advance_amount) > flt(a.allocated_amount):
                amount = flt(a.actual_advance_amount) - flt(a.allocated_amount)
                total_amount = total_amount + amount
                je.append("accounts", {
                        "account": a.advance_account,
                        "party_type": "Customer",
                        "party": self.customer,
                        "reference_type": "Hire Charge Invoice",
                        "reference_name": self.name,
                        "cost_center": a.advance_cost_center,
                        "debit_in_account_currency": flt(amount),
                        "debit": flt(amount),
                    })

        if total_amount > 0:
            je.append("accounts", {
                    "account": revenue_bank_account,
                    "cost_center": self.cost_center,
                    "credit_in_account_currency": flt(total_amount),
                    "credit": flt(total_amount),
                })

            je.insert()

            frappe.msgprint("Bill processed to accounts through journal voucher " + je.name)

@frappe.whitelist()
def get_vehicle_logs(form=None):
    if form:
        return frappe.db.sql("select a.name, a.equipment, a.rate_type, a.equipment_number, (a.total_work_time + a.hour_taken) as total_work_time, a.total_idle_time, a.work_rate, a.idle_rate, (select count(1) from `tabVehicle Log` b where b.parent = a.name) as no_of_days from `tabVehicle Logbook` a where a.docstatus = 1 and a.invoice_created = 0 and a.ehf_name = \'" + str(form) + "\'", as_dict=True)
    else:
        frappe.throw("Select Equipment Hiring Form first!")

@frappe.whitelist()
def get_vehicle_accessories(form, equipment):
    if form and equipment:
        data = frappe.db.sql("select accessory1, accessory2, accessory3, accessory4, accessory5, rate1, rate2, rate3, rate4, rate5, irate1, irate2, irate3, irate4, irate5 from `tabHiring Approval Details` where parent = \'" + str(form) + "\' and equipment = \'" + str(equipment) + "\'", as_dict=True)
        accessories = []
        for a in data:
            if a.accessory1:
                accessories.append({"name": a.accessory1, "work": a.rate1, "idle": a.irate1})	
            if a.accessory2:
                accessories.append({"name": a.accessory2, "work": a.rate2, "idle": a.irate2})	
            if a.accessory3:
                accessories.append({"name": a.accessory3, "work": a.rate3, "idle": a.irate3})	
            if a.accessory4:
                accessories.append({"name": a.accessory4, "work": a.rate4, "idle": a.irate4})	
            if a.accessory5:
                accessories.append({"name": a.accessory5, "work": a.rate5, "idle": a.irate5})	
        return accessories
    else:
        frappe.throw("Select Equipment Hiring Form first!")
#Get advances
@frappe.whitelist()
def get_advances(hire_name):
    if hire_name:
        return frappe.db.sql("select t1.name, t1.remark, t2.credit_in_account_currency as amount, t2.account as advance_account, t2.cost_center, t2.name as reference_row from `tabJournal Entry` t1, `tabJournal Entry Account` t2 where t1.name = t2.parent and t2.is_advance = 'Yes' and t1.docstatus = 1 and t2.reference_name = \'" + str(hire_name)  + "\'", as_dict=True)
    else:
        frappe.throw("Select Equipment Hiring Form first!")

@frappe.whitelist()
def make_payment_entry(source_name, target_doc=None): 
    def update_docs(obj, target, source_parent):
        target.posting_date = nowdate()
        target.payment_for = "Hire Charge Invoice"
        target.net_amount = obj.outstanding_amount
        target.actual_amount = obj.outstanding_amount
        target.income_account = frappe.db.get_value("Branch", obj.branch, "revenue_bank_account")

        target.append("items", {
                        "reference_type": "Hire Charge Invoice",
                        "reference_name": obj.name,
                        "outstanding_amount": obj.outstanding_amount,
                        "allocated_amount": obj.outstanding_amount,
                        "customer": obj.customer
                })
    
    doc = get_mapped_doc("Hire Charge Invoice", source_name, {
            "Hire Charge Invoice": {
                "doctype": "Mechanical Payment",
                "field_map": {
                    "name": "ref_no",
                    "outstanding_amount": "receivable_amount",
                },
                "postprocess": update_docs,
                "validation": {"docstatus": ["=", 1]}
            },
        }, target_doc)
    return doc
