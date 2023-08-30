# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
2.0		  SHIV		                   30/04/2018         Original Version
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, get_datetime, get_url, nowdate, now_datetime

class ImprestReceipt(Document):
	def validate(self):
                self.validate_defaults()
                self.update_defaults()
                self.update_amounts()
                self.validate_amounts()

        def on_submit(self):
                for t in frappe.get_all("Imprest Receipt", ["name"], {"branch": self.branch, "imprest_type": self.imprest_type, "entry_date":("<",self.entry_date),"docstatus":0}):
                        msg = '<b>Reference# : <a href="#Form/Imprest Receipt/{0}">{0}</a></b>'.format(t.name)
                        frappe.throw(_("Found unclosed entries. Previous entries needs to be either closed or cancelled in order to determine opening balance for the current transaction.<br>{0}").format(msg),title="Invalid Operation")
                update_dependencies(self.branch, self.imprest_type, self.entry_date)                
        
        def on_cancel(self):
                update_dependencies(self.branch, self.imprest_type, self.entry_date)

        def validate_defaults(self):
                if frappe.db.get_value("Branch Imprest Item", {"parent": self.branch, "imprest_type": self.imprest_type}, "imprest_status") == "Closed":
                        frappe.throw(_("Entries are not permitted for the closed imprest type <b>`{0}`</b>.").format(self.imprest_type), title="Imprest closed")
        
        def update_defaults(self):
                # Update entry_date
                #if not self.entry_date:
                if not self.get_db_value("entry_date"):
                        self.entry_date = now_datetime()
                
        def update_amounts(self):
                opening_balance = get_opening_balance(self.branch, self.imprest_type, self.name, self.entry_date)

                if flt(opening_balance) != flt(self.opening_balance):
                        #frappe.msgprint(_("Opening balance has been changed from Nu.{0}/- to Nu.{1}/-").format(flt(self.opening_balance),flt(opening_balance)),title="Change in values")
                        self.opening_balance = flt(opening_balance)

                self.receipt_amount  = flt(self.amount)
                self.purchase_amount = 0.0
                self.closing_balance = flt(self.opening_balance)+flt(self.receipt_amount)
        
	def validate_amounts(self):
                if flt(self.opening_balance) < 0:
                        frappe.throw("Opening balance cannot be a negative value.",title="Invalid Data")
                elif flt(self.amount) < 0:
                        frappe.throw("Receipt amount cannot be a negative value.",title="Invalid Data")
                elif not self.amount:
                        frappe.throw("Receipt amount cannot be empty.",title="Invalid Data")
                        
                # Validate against imprest limit set under branch
                imprest_limit = frappe.db.get_value("Branch Imprest Item", {"parent": self.branch, "imprest_type": self.imprest_type}, "imprest_limit")

                if not imprest_limit:
                        frappe.throw("Please set imprest limit for the branch.", title="Insufficient Balance")
                else:
                        if flt(self.closing_balance,2) > flt(imprest_limit,2):
                                frappe.throw(_("Closing balance cannot exceed imprest limit Nu.{0}/-.").format(flt(imprest_limit)),title="Invalid Data")


def update_dependencies(branch = None, imprest_type = None, entry_date = None):
        # Update dependent transactions
        trans_list      = []
        imprest_limit   = frappe.db.get_value("Branch Imprest Item", {"parent": branch, "imprest_type": imprest_type}, "imprest_limit")

        if not imprest_limit:
                frappe.throw("Please set imprest limit for the branch.", title="Insufficient Balance")

        trans = frappe.db.sql("""
                        select
                                x.doctype,
                                x.name,
                                x.imprest_type,
                                x.entry_date,
                                x.opening_balance,
                                x.receipt_amount,
                                x.purchase_amount,
                                x.closing_balance
                        from
                        (
                        select
                                'Imprest Receipt' as doctype,
                                imprest_type,
                                name,
                                cast(entry_date as char) as entry_date,
                                opening_balance,
                                receipt_amount,
                                purchase_amount,
                                closing_balance
                        from `tabImprest Receipt`
                        where branch = '{0}'
                        and imprest_type = '{2}'
                        and entry_date > '{1}'
                        and docstatus != 2
                        union all
                        select
                                'Imprest Recoup' as doctype,
                                imprest_type,
                                name,
                                cast(entry_date as char) as entry_date,
                                opening_balance,
                                receipt_amount,
                                purchase_amount,
                                closing_balance
                        from `tabImprest Recoup`
                        where branch = '{0}'
                        and imprest_type = '{2}'
                        and entry_date > '{1}'
                        and docstatus != 2
                        ) as x
                        order by x.entry_date
        """.format(branch, entry_date, imprest_type), as_dict=1)

        for t in trans:
                opening_balance = get_opening_balance(branch, t.imprest_type, t.name, t.entry_date)
                closing_balance = flt(opening_balance)+flt(t.receipt_amount)-flt(t.purchase_amount)
                if flt(closing_balance) < 0.0:
                        msg = '<br><b>Reference# : <a href="#Form/{1}/{0}">{0}</a></b>'.format(t.name,t.doctype)
                        frappe.throw(_("Insufficient opening balance for dependent <b>{1}</b> transaction. {0}").format(msg,t.doctype),title="<div style='color: red'>Insufficient Balance</div>")
                elif flt(closing_balance) > flt(imprest_limit):
                        msg = '<br><b>Reference# : {1} <a href="#Form/{1}/{0}">{0}</a></b>'.format(t.name,t.doctype)
                        frappe.throw(_("Closing balance cannot exceed imprest limit Nu.{0}/-. {1}").format(imprest_limit,msg),title="Invalid Data")
                else:
                        trans_list.append({
                                        "doctype"         : t.doctype,
                                        "name"            : t.name,
                                        "entry_date"      : t.entry_date,
                                        "opening_balance" : flt(opening_balance),
                                        "receipt_amount"  : flt(t.receipt_amount),
                                        "purchase_amount" : flt(t.purchase_amount),
                                        "closing_balance" : flt(closing_balance)
                        })

        for tl in trans_list:
                doc = frappe.get_doc(tl['doctype'], tl['name'])
                doc.update({
                                "opening_balance" : tl['opening_balance'],
                                "receipt_amount"  : tl['receipt_amount'],
                                "purchase_amount" : tl['purchase_amount'],
                                "closing_balance" : tl['closing_balance']
                })
                doc.flags.ignore_feed = True
                doc.save(ignore_permissions = True)

@frappe.whitelist()
def get_opening_balance(branch = None, imprest_type = None, docname = None, entry_date = None):
        entry_date = entry_date if entry_date else now_datetime()
        result = frappe.db.sql("""
                        select sum(amount)
                        from
                        (
                                select ifnull(receipt_amount,0) amount
                                from `tabImprest Receipt`
                                where branch = '{0}'
                                and imprest_type = '{3}'
                                and name != '{1}'
                                and entry_date < '{2}'
                                and docstatus = 1
                                union all
                                select -1*ifnull(purchase_amount,0) amount
                                from `tabImprest Recoup`
                                where branch = '{0}'
                                and imprest_type = '{3}'
                                and name != '{1}'
                                and entry_date < '{2}'
                                and docstatus = 1
                        ) as x
        """.format(branch, docname, entry_date, imprest_type), debug = 1)

        if result:
                return result[0][0]
        else:
                return 0.0
