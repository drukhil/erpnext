# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, cint, validate_email_add, today, add_years, date_diff, nowdate
from frappe.utils.data import get_first_day, get_last_day, add_days

class ForeignLabourer(Document):
	def validate(self):
		self.check_status()
		self.populate_work_history()

	def check_status(self):
                # Disabling Foreign Labourer record after status change to "Left"
		if self.status == "Left" and self.date_of_separation:
                        self.docstatus = 1

	# Following method introducted by SHIV on 04/10/2017
        def populate_work_history(self):
                if not self.internal_work_history:
                        self.append("internal_work_history",{
                                                "branch": self.branch,
                                                "cost_center": self.cost_center,
                                                "from_date": self.date_of_joining,
                                                "owner": frappe.session.user,
                                                "creation": nowdate(),
                                                "modified_by": frappe.session.user,
                                                "modified": nowdate()
                        })
                else:                        
                        # Fetching previous document from db
                        prev_doc = frappe.get_doc(self.doctype,self.name)
                        self.date_of_transfer = self.date_of_transfer if self.date_of_transfer else today()
                        
                        if (getdate(self.date_of_joining) != prev_doc.date_of_joining) or \
                           (self.status == 'Left' and self.date_of_separation) or \
                           (self.cost_center != prev_doc.cost_center):
                                for wh in self.internal_work_history:
                                        # For change in date_of_joining
                                        if (getdate(self.date_of_joining) != prev_doc.date_of_joining):
                                                if (getdate(prev_doc.date_of_joining) == getdate(wh.from_date)):
                                                        wh.from_date = self.date_of_joining

                                        # For change in date_of_separation, cost_center
                                        if (self.status == 'Left' and self.date_of_separation):
                                                if not wh.to_date:
                                                        wh.to_date = self.date_of_separation
                                                elif prev_doc.date_of_separation:
                                                        if (getdate(prev_doc.date_of_separation) == getdate(wh.to_date)):
                                                                wh.to_date = self.date_of_separation
                                        elif (self.cost_center != prev_doc.cost_center):
                                                if getdate(self.date_of_transfer) > getdate(today()):
                                                        frappe.throw(_("Date of transfer cannot be a future date."),title="Invalid Date")      
                                                elif not wh.to_date:
                                                        if getdate(self.date_of_transfer) < getdate(wh.from_date):
                                                                frappe.throw(_("Row#{0} : Date of transfer({1}) cannot be beyond current effective entry.").format(wh.idx,self.date_of_transfer),title="Invalid Date")
                                                                
                                                        wh.to_date = wh.from_date if add_days(getdate(self.date_of_transfer),-1) < getdate(wh.from_date) else add_days(self.date_of_transfer,-1)
                                                
                        if (self.cost_center != prev_doc.cost_center):
                                self.append("internal_work_history",{
                                                "branch": self.branch,
                                                "cost_center": self.cost_center,
                                                "from_date": self.date_of_transfer,
                                                "owner": frappe.session.user,
                                                "creation": nowdate(),
                                                "modified_by": frappe.session.user,
                                                "modified": nowdate()
                                })
                        elif not self.internal_work_history:
                                self.append("internal_work_history",{
                                                        "branch": self.branch,
                                                        "cost_center": self.cost_center,
                                                        "from_date": self.date_of_joining,
                                                        "owner": frappe.session.user,
                                                        "creation": nowdate(),
                                                        "modified_by": frappe.session.user,
                                                        "modified": nowdate()
                                })

