# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# project_invoice.py
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0		  SHIV		 2017/08/23                            Original Version
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, time_diff_in_hours, get_datetime, getdate, cint, get_datetime_str
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba
from erpnext.custom_utils import check_tds_remittance

class ProjectInvoice(AccountsController):
    def validate(self):
                self.set_status()
                self.validate_mb_entries()
                self.load_invoice_boq()
                self.validate_items()
                self.set_defaults()
                
    def on_submit(self):
        self.update_boq_item()
        self.update_boq()
        self.update_mb_entries()
        self.make_gl_entries()
        self.project_invoice_item_entry()
        self.update_advance_balance()
        # self.consume_budget()  

    def before_cancel(self):
            self.set_status()

    def on_cancel(self):
            check_tds_remittance(self.name)
            self.make_gl_entries()
            self.update_boq_item()
            self.update_boq()
            self.update_mb_entries()
            self.project_invoice_item_entry()
            self.update_advance_balance()  
            self.cancel_consumed()  

    def on_update_after_submit(self):
            self.project_invoice_item_entry()

    def project_invoice_item_entry(self):
            if self.docstatus == 2:
                    frappe.db.sql("delete from `tabProject Invoice Item` where parent='{project}' and invoice_name = '{invoice_name}'".format(project=self.project, invoice_name=self.name))
            else:
                    if not frappe.db.exists("Project Invoice Item", {"parent": self.project, "invoice_name": self.name}):
                            doc = frappe.get_doc("Project", self.project)
                            row = doc.append("project_invoice_item", {})
                            row.invoice_name            = self.name
                            row.invoice_date            = self.invoice_date
                            row.boq                     = self.boq
                            row.subcontract             = self.subcontract
                            row.gross_invoice_amount    = flt(self.gross_invoice_amount)
                            row.price_adjustment_amount = flt(self.price_adjustment_amount)
                            row.net_invoice_amount      = flt(self.net_invoice_amount)
                            row.total_received_amount   = flt(self.total_received_amount)
                            row.total_paid_amount       = flt(self.total_paid_amount)
                            row.total_balance_amount    = flt(self.total_balance_amount)
                            row.save(ignore_permissions=True)
                    else:
                            row = frappe.get_doc("Project Invoice Item", {"parent": self.project, "invoice_name": self.name})
                            row.invoice_date            = self.invoice_date
                            row.boq                     = self.boq
                            row.subcontract             = self.subcontract
                            row.gross_invoice_amount    = flt(self.gross_invoice_amount)
                            row.price_adjustment_amount = flt(self.price_adjustment_amount)
                            row.net_invoice_amount      = flt(self.net_invoice_amount)
                            row.total_received_amount   = flt(self.total_received_amount)
                            row.total_paid_amount       = flt(self.total_paid_amount)
                            row.total_balance_amount    = flt(self.total_balance_amount)
                            row.save(ignore_permissions=True)

    def set_status(self):
            self.status = {
                    "0": "Draft",
                    "1": "Unpaid",
                    "2": "Cancelled"
            }[str(self.docstatus or 0)]

    def set_defaults(self):
            if self.project:
                    base_project          = frappe.get_doc("Project", self.project)
                    self.company          = base_project.company
                    #self.customer         = base_project.customer
                    #self.party_type       = base_project.party_type
                    #self.party            = base_project.party
                    self.branch           = base_project.branch
                    self.cost_center      = base_project.cost_center

                    if not self.invoice_title:
                            self.invoice_title = "Project Invoice ({0})".format(base_project.project_name)

                    if base_project.status in ('Completed','Cancelled'):
                            frappe.throw(_("Operation not permitted on already {0} Project.").format(base_project.status),title="Project Invoice: Invalid Operation")

            if self.boq:
                    base_boq              = frappe.get_doc("BOQ", self.boq)
                    self.cost_center      = base_boq.cost_center
                    self.branch           = base_boq.branch
                    self.boq_type         = base_boq.boq_type

    # following method created by SHIV on 2019/06/20
    def validate_mb_entries(self):
            for i in self.get("project_invoice_mb"):
                    for t in frappe.get_all("Project Invoice MB", ["parent"], {"entry_name": i.entry_name, "is_selected": 1, "docstatus": 1}, order_by="boq, subcontract, parent"):
                            msg = '<b>Reference# : <a href="#Form/Project Invoice/{0}">{0}</a></b>'.format(t.parent)
                            frappe.throw(_("Row#{0}: Measurement Book Entry {1} is already invoiced<br>{2}").format(i.idx,i.entry_name,msg))
    # following method created by SHIV on 2019/06/19
    def get_name_list(self):
            name_list = frappe._dict()
            boq_list         = []
            subcontract_list = []
            mb_list          = []
            if self.invoice_type == "MB Based Invoice":
                    for i in self.get("project_invoice_mb"):
                            if i.is_selected and i.subcontract:
                                    subcontract_list.append(i.subcontract)
                            elif i.is_selected and not i.subcontract:
                                    boq_list.append(i.boq)

                            if i.is_selected:
                                    mb_list.append(i.entry_name)
            else:
                    boq_list.append(self.boq)
                    subcontract_list.append(self.subcontract)

            # remove duplicate values
            boq_list = list(set(boq_list))
            subcontract_list = list(set(subcontract_list))
            mb_list = list(set(mb_list))

            # invoice can be either for BOQ or Subcontract only
            table_name = "Subcontract" if subcontract_list else "BOQ"

            name_list.setdefault('table_name',table_name)
            name_list.setdefault('boq_list',boq_list)
            name_list.setdefault('subcontract_list',subcontract_list)
            name_list.setdefault('mb_list',mb_list)

            return name_list

    # load project_invoice_boq for Running Account Bill print
    def load_invoice_boq(self):
            name_list = self.get_name_list()

            if self.invoice_type == "MB Based Invoice":
                    if not name_list.get("mb_list"):
                            return

                    mb_list          = "'"+"','".join(name_list.get("mb_list"))+"'"
                    boq_list         = "'"+"','".join(name_list.get("boq_list"))+"'"
                    subcontract_list = "'"+"','".join(name_list.get("subcontract_list"))+"'"

                    mb_boq = frappe.db.sql("""
                                    select
                                            boq                              as boq,
                                            subcontract                      as subcontract,
                                            boq_item_name                    as boq_item_name,
                                            max(boq_code)                    as boq_code,
                                            max(item)                        as item,
                                            max(uom)                         as uom,
                                            max(ifnull(is_group,0))          as is_group,
                                            max(ifnull(is_selected,0))       as is_selected,
                                            sum(ifnull(idx,0))               as idx,
                                            sum(ifnull(a.original_quantity,0)) as original_quantity,
                                            max(ifnull(original_rate,0))     as original_rate,
                                            sum(ifnull(original_amount,0))   as original_amount,
                                            sum(ifnull(entry_quantity,0))    as entry_quantity,
                                            max(ifnull(entry_rate,0))        as entry_rate,
                                            sum(ifnull(entry_amount,0))      as entry_amount,
                                            max(creation)                    as creation,
                                            sum(flag)                        as flag
                                    from (
                                            select
                                                    bi.parent         as boq,
                                                    Null              as subcontract, 
                                                    bi.name           as boq_item_name,
                                                    bi.boq_code       as boq_code,
                                                    bi.item           as item,
                                                    bi.uom            as uom,
                                                    bi.is_group       as is_group,
                                                    0                 as is_selected,
                                                    bi.idx            as idx,
                                                    bi.quantity       as original_quantity,
                                                    bi.rate           as original_rate,
                                                    bi.amount         as original_amount,
                                                    0                 as entry_quantity,
                                                    0                 as entry_rate,
                                                    0                 as entry_amount,
                                                    bi.creation       as creation,
                                                    2                 as flag
                                            from `tabBOQ Item` as bi
                                            where parent in ({boq_list})
                                            union all
                                            select
                                                    sc.boq            as boq,
                                                    sc.name           as subcontract,
                                                    sci.name          as boq_item_name,
                                                    sci.boq_code      as boq_code,
                                                    sci.item          as item,
                                                    sci.uom           as uom,
                                                    sci.is_group      as is_group,
                                                    0                 as is_selected,
                                                    sci.idx           as idx,
                                                    sci.quantity      as original_quantity,
                                                    sci.rate          as original_rate,
                                                    sci.amount        as original_amount,
                                                    0                 as entry_quantity,
                                                    0                 as entry_rate,
                                                    0                 as entry_amount,
                                                    sci.creation      as creation,
                                                    2                 as flag
                                            from `tabSubcontract Item` as sci, `tabSubcontract` as sc
                                            where sc.name in ({subcontract_list}) 
                                            and sci.parent = sc.name 
                                            union all
                                            select
                                                    me.boq            as boq,
                                                    me.subcontract    as subcontract,
                                                    mb.boq_item_name  as boq_item_name,
                                                    0                 as boq_code,
                                                    mb.item           as item,
                                                    mb.uom            as uom,
                                                    0                 as is_group,
                                                    mb.is_selected    as is_selected,
                                                    0                 as idx,
                                                    0                 as original_quantity,
                                                    0                 as original_rate,
                                                    0                 as original_amount,
                                                    (case
                                                            when me.boq_type = 'Milestone Based' then 0
                                                            else mb.entry_quantity
                                                    end)              as entry_quantity,
                                                    mb.entry_rate     as entry_rate,
                                                    mb.entry_amount   as entry_amount,
                                                    mb.creation       as creation,
                                                    -2                as flag
                                            from `tabMB Entry BOQ` as mb, `tabMB Entry` me
                                            where mb.parent in ({mb_list})
                                            and   me.name = mb.parent
                                            and   mb.is_selected = 1
                                    ) as a
                                    group by boq, subcontract, boq_item_name
                                    order by ifnull(subcontract,boq), idx
                                    """.format(boq_list=boq_list, subcontract_list=subcontract_list, mb_list=mb_list), as_dict=1)

                    self.project_invoice_boq = []
                    for item in mb_boq:
                            act_quantity = flt(item.original_quantity)
                            act_rate     = flt(item.original_rate)
                            act_amount   = flt(item.original_amount)

                            uptodate_quantity = 0.0
                            uptodate_rate     = 0.0
                            uptodate_amount   = 0.0

                            if not item.is_group:
                                    # Total Invoiced so far (excluding this Invoice)
                                    ti = frappe.db.sql("""
                                                    select
                                                            sum(ifnull(invoice_quantity,0)) as tot_invoice_quantity,
                                                            max(ifnull(invoice_rate,0))     as tot_invoice_rate,
                                                            sum(ifnull(invoice_amount,0))   as tot_invoice_amount
                                                    from   `tabProject Invoice BOQ`
                                                    where  boq_item_name    = '{boq_item_name}'
                                                    and    is_selected      = 1
                                                    and    docstatus        = 1
                                                    and    parent           != '{parent}'
                                                    """.format(boq_item_name=item.boq_item_name, parent=self.name), as_dict=1)[0]

                                    if ti:
                                            act_quantity = flt(item.original_quantity)-flt(ti.tot_invoice_quantity)
                                            act_rate     = flt(ti.tot_invoice_rate)
                                            act_amount   = flt(item.original_amount)-flt(ti.tot_invoice_amount)

                                            uptodate_quantity = flt(ti.tot_invoice_quantity)
                                            uptodate_rate     = flt(ti.tot_invoice_rate)
                                            uptodate_amount   = flt(ti.tot_invoice_amount)

                            self.append("project_invoice_boq",{
                                    "boq": item.boq,
                                    "subcontract": item.subcontract,
                                    "boq_item_name": item.boq_item_name,
                                    "boq_code": item.boq_code,
                                    "item": item.item,
                                    "is_group": item.is_group,
                                    "uom": item.uom,
                                    "is_selected": item.is_selected,
                                    "original_quantity": item.original_quantity,
                                    "original_rate": item.original_rate,
                                    "original_amount": item.original_amount,
                                    "act_quantity": act_quantity,
                                    "act_rate": act_rate,
                                    "act_amount": act_amount,
                                    "invoice_quantity": item.entry_quantity,
                                    "invoice_rate": item.entry_rate,
                                    "invoice_amount": item.entry_amount,
                                    "uptodate_quantity": uptodate_quantity,
                                    "uptodate_rate": uptodate_rate,
                                    "uptodate_amount": uptodate_amount,
                                    "creation": self.creation,
                                    "modified": self.modified,
                                    "modified_by": self.modified_by,
                                    "owner": self.owner
                            })
            else:
                    #Direct Invoice
                    for item in self.project_invoice_boq:
                            item.uptodate_quantity = 0.0
                            item.uptodate_rate     = 0.0
                            item.uptodate_amount   = 0.0
                            
                            if not item.is_group:
                                    # Total Invoiced so far (excluding this Invoice)
                                    ti = frappe.db.sql("""
                                                    select
                                                            sum(ifnull(invoice_quantity,0)) as tot_invoice_quantity,
                                                            max(ifnull(invoice_rate,0))     as tot_invoice_rate,
                                                            sum(ifnull(invoice_amount,0))   as tot_invoice_amount
                                                    from   `tabProject Invoice BOQ`
                                                    where  boq_item_name    = '{boq_item_name}'
                                                    and    is_selected      = 1
                                                    and    docstatus        = 1
                                                    and    parent           != '{parent}'
                                                    """.format(boq_item_name=item.boq_item_name, parent=self.name), as_dict=1)[0]

                                    if ti:
                                            item.uptodate_quantity = flt(ti.tot_invoice_quantity)
                                            item.uptodate_rate     = flt(ti.tot_invoice_rate)
                                            item.uptodate_amount   = flt(ti.tot_invoice_amount)
                    
    def validate_items(self):
            gross_invoice_amount    = 0
            price_adjustment_amount = 0

            if self.invoice_type == "Direct Invoice":
                    is_selected = 0
                    for rec in self.project_invoice_boq:
                            is_selected += 1 if rec.is_selected else 0
                            rec.boq = self.boq
                            rec.subcontract = self.subcontract
                            if rec.is_selected and flt(rec.invoice_amount):
                                    gross_invoice_amount += flt(rec.invoice_amount)
                                    
                            if round(flt(rec.invoice_quantity)) > round(flt(rec.act_quantity)):
                                    frappe.throw(_("Row{0}: Invoice Quantity cannot be greater than Balance Quantity").format(rec.idx))
                            elif round(flt(rec.invoice_amount)) > round(flt(rec.act_amount)):
                                    frappe.throw(_("Row{0}: Invoice Amount cannot be greater than Balance Amount").format(rec.idx))
                            elif flt(rec.invoice_quantity) < 0 or flt(rec.invoice_amount) < 0:
                                    frappe.throw(_("Row{0}: Value cannot be in negative.").format(rec.idx))

                    price_adjustment_amount = flt(self.price_adjustment_amount)

                    if not is_selected:
                            frappe.throw(_("You need to select atleast one BOQ ITEM for invoicing"),title="Invalid Data")
            else:
                    is_selected = 0
                    for rec in self.project_invoice_mb:
                            is_selected += 1 if rec.is_selected else 0
                            if rec.is_selected and flt(rec.entry_amount):
                                    gross_invoice_amount    += flt(rec.entry_amount)
                                    price_adjustment_amount += flt(rec.price_adjustment_amount)

                    if not is_selected:
                            frappe.throw(_("You need to select atleast one MEASUREMENT BOOK ENTRY for invoicing"),title="Invalid Data")
            
            # added by phuntsho on Aug 12, 2021 for rebate deductions
            rebate_deduction_total = 0
            if self.rebate: 
                    for item in self.rebate:
                            if item.addition:
                                    rebate_deduction_total -= item.amount
                            else:
                                    rebate_deduction_total += item.amount
            # ---- end of code ----

            total_deduction_amount = self.calculate_total_deductions()

            self.gross_invoice_amount    = flt(gross_invoice_amount)
            self.net_amount              = flt(self.gross_invoice_amount)-flt(rebate_deduction_total) #added by phuntsho on aug 11, 2021
            self.price_adjustment_amount = flt(price_adjustment_amount)
            self.net_invoice_amount      = flt(self.net_amount)+flt(self.price_adjustment_amount)-flt(self.advance_recovery)-flt(self.total_deduction_amount)
            self.total_balance_amount    = flt(self.net_invoice_amount)-flt(self.total_received_amount)-flt(self.total_paid_amount)
            
            if flt(self.gross_invoice_amount) == 0:
                    frappe.throw(_("Gross Invoice Amount should be greater than zero"), title="Invalid Data")

    def calculate_total_deductions (self):
            total_deduction_amount = 0 
            if self.deductions:
                    for item in self.deductions:
                            total_deduction_amount += item.amount

            if self.advances:
                    for item in self.advances:
                            total_deduction_amount += item.allocated_amount
            if self.tds_amount:
                    pass


    def make_gl_entries(self):
            if self.net_invoice_amount:
                    from erpnext.accounts.general_ledger import make_gl_entries
                    gl_entries = []
                    self.posting_date = self.invoice_date
                    currency = frappe.db.get_value(doctype=self.party_type, filters=self.party, fieldname=["default_currency"], as_dict=True)
                    default_ba =  get_default_ba()

                    if self.party_type == "Customer":
                            inv_gl = frappe.db.get_value(doctype="Projects Accounts Settings",fieldname="project_invoice_account")
                            rec_gl = frappe.db.get_value(doctype="Company",filters=self.company,fieldname="default_receivable_account")
                    elif self.party_type == "Supplier":
                            if self.supplier_invoice:
                                    inv_gl = self.supplier_invoice
                            else:
                                    inv_gl = frappe.db.get_value(doctype="Projects Accounts Settings",fieldname="invoice_account_supplier")
                            rec_gl = frappe.db.get_value(doctype="Company",filters=self.company,fieldname="default_payable_account")
                            if self.net_invoice_amount < 0: #added by Jai 6 Oct 2021
                                    rec_gl = frappe.db.get_value(doctype="Projects Accounts Settings",fieldname="refundable_account_supplier")
                    else:
                            inv_gl = frappe.db.get_value(doctype="Projects Accounts Settings",fieldname="invoice_account_internal")
                            rec_gl = frappe.db.get_value(doctype="Company",filters=self.company,fieldname="default_receivable_account")

                    if not inv_gl:
                            frappe.throw(_("Project Invoice Account is not defined in Projects Accounts Settings."))

                    if not rec_gl:
                            frappe.throw(_("Default Receivable Account is not defined in Company Settings."))
                            
                    gl_entries.append(
                            self.get_gl_dict({
                                    "account":  rec_gl,
                                    "party_type": self.party_type,
                                    "party": self.party,
                                    "against": inv_gl,
                                    "credit" if self.party_type == "Supplier" else "debit": self.net_invoice_amount,
                                    "credit_in_account_currency" if self.party_type == "Supplier" else "debit_in_account_currency": self.net_invoice_amount,
                                    "against_voucher": self.name,
                                    "against_voucher_type": self.doctype,
                                    "project": self.project,
                                    "cost_center": self.cost_center,
                                    "business_activity": default_ba
                            }, self.currency)
                    )
                    

                    gl_entries.append(
                            self.get_gl_dict({
                                    "account":  inv_gl,
                                    "against": self.party,
                                    "debit" if self.party_type == "Supplier" else "credit": self.net_amount,
                                    "debit_in_account_currency" if self.party_type == "Supplier" else "credit_in_account_currency": self.net_amount,
                                    "project": self.project,
                                    "cost_center": self.cost_center,
                                    "business_activity": default_ba
                            }, self.currency)
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
                                                                "party": self.party,
                                                                "business_activity": default_ba
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
                                                        "project": self.project,
                                                        "business_activity": default_ba
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
                                                    "project": self.project,
                                                    "business_activity": default_ba
                                    }, currency.default_currency)
                            )

                    make_gl_entries(gl_entries, cancel=(self.docstatus == 2),update_outstanding="No", merge_entries=False)
                    

    def update_boq_item(self):
            name_list = self.get_name_list()
            if self.invoice_type == "Direct Invoice":
                    # Direct Invoice
                    item_list = frappe.db.sql("""
                                    select
                                            pib.boq,
                                            pib.subcontract,
                                            pib.boq_item_name,
                                            sum(
                                                    case
                                                    when '{boq_type}' = 'Milestone Based' then 0
                                                    else
                                                            case
                                                            when pib.docstatus < 2 then ifnull(pib.invoice_quantity,0)
                                                            else -1*ifnull(pib.invoice_quantity,0)
                                                            end
                                                    end
                                                ) as invoice_quantity,
                                            sum(
                                                    case
                                                    when pib.docstatus < 2 then ifnull(pib.invoice_amount,0)
                                                    else -1*ifnull(pib.invoice_amount,0)
                                                    end
                                                ) as invoice_amount
                                    from `tabProject Invoice BOQ` pib
                                    where pib.parent         = '{parent}'
                                    and   pib.is_selected    = 1
                                    and   pib.invoice_amount > 0
                                    group by pib.boq,pib.subcontract,pib.boq_item_name
                                    """.format(boq_type=self.boq_type, parent=self.name), as_dict=1)
            
                    for item in item_list:
                            frappe.db.sql("""
                                    update `tab{table_name} Item`
                                    set
                                            claimed_quantity = ifnull(claimed_quantity,0)+ifnull({claimed_quantity},0),
                                            claimed_amount   = ifnull(claimed_amount,0)+ifnull({claimed_amount},0),
                                            balance_quantity = ifnull(balance_quantity,0) - ifnull({claimed_quantity},0),
                                            balance_amount   = ifnull(balance_amount,0) - ifnull({claimed_amount},0)
                                    where name = '{boq_item_name}'
                                    """.format(table_name="Subcontract" if item.subcontract else "BOQ", boq_item_name=item.boq_item_name, claimed_quantity=flt(item.invoice_quantity), claimed_amount=flt(item.invoice_amount)))
            else:
                    # MB Based Invoice
                    boq_list = frappe.db.sql("""
                                    select
                                            pim.boq,
                                            pim.subcontract,
                                            meb.boq_item_name,
                                            sum(
                                                    case
                                                    when pim.boq_type = 'Milestone Based' then 0
                                                    else
                                                            case
                                                            when pim.docstatus < 2 then ifnull(meb.entry_quantity,0)
                                                            else -1*ifnull(meb.entry_quantity,0)
                                                            end
                                                    end
                                            ) as entry_quantity,
                                            sum(
                                                    case
                                                    when pim.docstatus < 2 then ifnull(meb.entry_amount,0)
                                                    else -1*ifnull(meb.entry_amount,0)
                                                    end
                                            ) as entry_amount
                                    from  `tabProject Invoice MB` as pim, `tabMB Entry BOQ` meb
                                    where pim.parent        = '{parent}'
                                    and   pim.is_selected   = 1
                                    and   meb.parent        = pim.entry_name
                                    and   meb.is_selected   = 1
                                    group by pim.boq,pim.subcontract,meb.boq_item_name
                                    """.format(parent=self.name), as_dict=1)

                    for item in boq_list:
                            frappe.db.sql("""
                                    update `tab{table_name} Item`
                                    set
                                            claimed_quantity = ifnull(claimed_quantity,0)+ifnull({claimed_quantity},0),
                                            booked_quantity  = ifnull(booked_quantity,0)-ifnull({claimed_quantity},0),
                                            claimed_amount   = ifnull(claimed_amount,0)+ifnull({claimed_amount},0),
                                            booked_amount    = ifnull(booked_amount,0)-ifnull({claimed_amount},0)
                                    where name = '{boq_item_name}'
                            """.format(table_name="Subcontract" if item.subcontract else "BOQ", boq_item_name=item.boq_item_name, claimed_quantity=flt(item.entry_quantity), claimed_amount=flt(item.entry_amount)))
                    
    def update_boq(self):
            if self.invoice_type == "Direct Invoice":
                    tot_invoice_amount = flt(self.net_invoice_amount) if self.docstatus < 2 else -1*flt(self.net_invoice_amount)
                    tot_price_adj      = flt(self.price_adjustment_amount) if self.docstatus < 2 else -1*flt(self.price_adjustment_amount)

                    if tot_invoice_amount or tot_price_adj:
                            boq_doc = frappe.get_doc("Subcontract" if self.subcontract else "BOQ", self.subcontract if self.subcontract else self.boq)
                            boq_doc.claimed_amount   = flt(boq_doc.claimed_amount) + flt(tot_invoice_amount)
                            boq_doc.price_adjustment = flt(boq_doc.price_adjustment) + flt(tot_price_adj)
                            boq_doc.balance_amount   = flt(boq_doc.balance_amount) + flt(tot_price_adj)
                            boq_doc.save(ignore_permissions = True)                                
            else:
                    for i in self.project_invoice_mb:
                            if i.is_selected:
                                    tot_invoice_amount = (flt(i.entry_amount)+flt(i.price_adjustment_amount)) if self.docstatus < 2 else -1*(flt(i.entry_amount)+flt(i.price_adjustment_amount))
                                    tot_price_adj      = flt(i.price_adjustment_amount) if self.docstatus < 2 else -1*flt(i.price_adjustment_amount)

                                    if tot_invoice_amount or tot_price_adj:
                                            boq_doc = frappe.get_doc("Subcontract" if i.subcontract else "BOQ", i.subcontract if i.subcontract else i.boq)
                                            boq_doc.claimed_amount   = flt(boq_doc.claimed_amount) + flt(tot_invoice_amount)
                                            boq_doc.price_adjustment = flt(boq_doc.price_adjustment) + flt(tot_price_adj)
                                            boq_doc.balance_amount   = flt(boq_doc.balance_amount) + flt(tot_price_adj)
                                            boq_doc.save(ignore_permissions = True)

    def update_mb_entries(self):
            if self.invoice_type == "MB Based Invoice":
                    for mb in self.project_invoice_mb:
                            if (flt(mb.entry_amount) > 0 or flt(mb.price_adjustment_amount) != 0.0) and mb.is_selected:
                                    entry_amount      = -1*flt(mb.entry_amount) if self.docstatus == 2 else flt(mb.entry_amount)
                                    adjustment_amount = -1*flt(mb.price_adjustment_amount) if self.docstatus == 2 else flt(mb.price_adjustment_amount) 

                                    mb_doc = frappe.get_doc("MB Entry", mb.entry_name)
                                    mb_doc.total_invoice_amount   = flt(mb_doc.total_invoice_amount) + (flt(entry_amount)+flt(adjustment_amount))
                                    mb_doc.total_price_adjustment = flt(mb_doc.total_price_adjustment) + flt(adjustment_amount)
                                    balance_amount                = flt(mb_doc.total_balance_amount) - flt(entry_amount)
                                    mb_doc.total_balance_amount   = flt(balance_amount)
                                    mb_doc.status                 = 'Uninvoiced' if flt(balance_amount) > 0 else 'Invoiced'
                                    mb_doc.save(ignore_permissions = True)           

    # picked from project payment by phuntsho on may 6th
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

    #Cancel the consumed budget
def cancel_consumed(self):
    frappe.db.sql("delete from `tabConsumed Budget` where po_no = %s", self.name)

    def consume_budget(self): #added by Jai
            # pass
            if self.party_type == "Supplier":
                    if not self.supplier_invoice:
                            inv_account = frappe.db.get_value(doctype="Projects Accounts Settings",fieldname="invoice_account_supplier")
                            if inv_account:
                                    account_type = frappe.db.get_value("Account", inv_account, "account_type")
                                    if account_type in ("Capital Work in Progress"):
                                            # po_date = frappe.db.get_value("Purchase Order", item.purchase_order, "transaction_date")
                                            project = frappe.get_doc('Project', self.project)
                                            po_date = self.invoice_date
                                            company = 'National Housing Development Corporation Ltd.'
                                            consume = frappe.get_doc({
                                                    "doctype": "Consumed Budget",
                                                    "account": inv_account,
                                                    "cost_center": self.cost_center,
                                                    "po_no": self.name,
                                                    "company": company,
                                                    "po_date": po_date,
                                                    "amount": self.net_invoice_amount,
                                                    "poi_name": '',
                                                    "pii_name": '',
                                                    "item_code": '',
                                                    "com_ref": project.name,
                                                    "date": frappe.utils.nowdate()})
                                            consume.flags.ignore_permissions=1
                                            consume.submit()
            
@frappe.whitelist()
def get_project_party_type(doctype, txt, searchfield, start, page_len, filters):
    result = []
            
    if not filters.get("project"):
            return result

    result = frappe.db.sql("""
            select distinct party_type
            from `tabBOQ`
            where project = '{project}'
            union all
            select distinct party_type
            from `tabSubcontract`
            where project = '{project}'
    """.format(project=filters.get("project")))
            
    return result

@frappe.whitelist()
def get_project_party(doctype, txt, searchfield, start, page_len, filters):
    result = []
            
    if not filters.get("project") or not filters.get("party_type"):
            return result

    result = frappe.db.sql("""
            select distinct party
            from `tabBOQ`
            where project = '{project}'
            and party_type = '{party_type}'
            union all
            select distinct party
            from `tabSubcontract`
            where project = '{project}'
            and party_type = '{party_type}'
    """.format(project=filters.get("project"), party_type=filters.get("party_type")))
            
    return result


# Following code commented by SHIV on 2019/06/18
'''
@frappe.whitelist()
def get_mb_list(project, boq_name, entry_name):
    if entry_name == "dummy":
            entry_name = None

    if boq_name == "dummy":
            boq_name = None
            
    result = frappe.db.sql("""
            select *
            from `tabMB Entry`
            where project = %s
            and docstatus = 1
            and total_balance_amount > 0
            and boq = ifnull(%s,boq)
            and name = ifnull(%s,name)
            """, (project, boq_name, entry_name), as_dict=True)

    return result
'''

# Following code added by SHIV on 2019/06/18
@frappe.whitelist()
def get_mb_list(project, party_type, party):
    result = frappe.db.sql("""
            select *
            from `tabMB Entry`
            where project = '{project}'
            and docstatus = 1
            and party_type = '{party_type}'
            and party = '{party}'
            and total_balance_amount > 0
            """.format(project=project, party_type=party_type, party=party), as_dict=True)

    return result

# ADDED BY PHUNTSHO TO UPDATE THE PAYMENT STATUS
@frappe.whitelist()
def get_payment_entry(doc_name, total_amount, project, party, party_type):
    """ see if there exist a payment entry submitted for the project invoice """
    payment_entry = """
            SELECT
                    sum(paid_amount) as total_amount, 
                    name
            FROM
                    `tabProject Payment`
            WHERE   
                    docstatus = 1 and
                    project = '{name}' and 
                    party_type = '{type}' and 
                    party = '{party}'
            """.format(name=project, type=party_type, party=party)

    payment_entry = frappe.db.sql(payment_entry, as_dict=1)
    
    if (len(payment_entry) >= 1 and payment_entry[0].total_amount > 0):
            if flt(total_amount) < 0: total_amount = -1 * (flt(total_amount))
            
    if round(flt(payment_entry[0].total_amount), 2) == round(flt(total_amount), 2):
        frappe.db.set_value("Project Invoice", doc_name, "payment_status", "Paid")
        return ("Paid")
    else:
        frappe.db.set_value("Project Invoice", doc_name, 'payment_status', "Partially Paid")
        return ("Partially Paid")
    # else:
    #     frappe.db.set_value("Project Invoice", doc_name, 'payment_status', "Not Paid")
    return ("Not Paid")


