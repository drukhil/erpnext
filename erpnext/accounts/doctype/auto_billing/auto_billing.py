# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt, nowdate, cint, today

class AutoBilling(Document):
	def validate(self):
		self.items = []
		for a in self.get_period_date_ranges():
			self.append("items", {
			"schedule_date": getdate(a),
			"ref_doc": self.ref_doc,
			"ref_name": self.ref_name,
			"posted": 0
			})
	
		self.calculate_total()	

	def calculate_total(self):
		total = 0.0
		for a in self.get("items"):
			a.amount = frappe.get_doc(a.ref_doc, a.ref_name).amount
			total += flt(a.amount)
		self.total_amount = total
				
	def on_submit(self):
		self.make_auto_entries()

	def get_period_date_ranges(self):
                from dateutil.relativedelta import relativedelta
                from_date, to_date = getdate(self.from_date), getdate(self.to_date)
		schedule_date = ''
                increment = {
                        "Monthly": 1,
                }.get("Monthly",1)

                periodic_daterange = []
                for dummy in range(1, 53, increment):
              		period_end_date = from_date + relativedelta(months=increment, days=-1)

                        if period_end_date > to_date:
                                period_end_date = to_date
                        if period_end_date == to_date:
                                break
			schedule_date = from_date + relativedelta(day = 25)
			periodic_daterange.append(schedule_date)
			from_date = period_end_date + relativedelta(days=1)
                return periodic_daterange


def post_billing_entries(date=None):
        if not date:
                date = today()
        for bills in get_billing_list(date):
                make_auto_entries(bills.ref_doc, bills.ref_name, bills.user, date)
		frappe.db.commit()

def get_billing_list(date):
        return frappe.db.sql("""select b.name as child, a.user as user, b.ref_doc as ref_doc, b.ref_name as ref_name from 
			`tabAuto Billing` a, `tabAuto Billing Schedule` b where a.name = b.parent and a.docstatus < 1 
			and b.schedule_date <= '{0}' and b.posted = 0 """.format(date), as_dict = 1)

def make_auto_entries(ref_doc, ref_name, user, date):
	sample_doc = frappe.get_doc(ref_doc, ref_name)
	new_doc = frappe.copy_doc(sample_doc)
	new_doc.posting_date = date
	new_doc.invoice_date = date
	new_doc.invoice_no = ''
	new_doc.insert()
	new_doc.posted_by = frappe.session.user
	new_doc.posting_date = nowdate()
	new_doc.document = new_doc.name
	if user:
		subject = 'Auto Billing'
		message = """Dear Sir/Madam, <br>
			     A new {0} is created, kindly verify and process further. """
		try:
			frappe.sendmail(recipients=user, sender=None, subject=subject, message=message)
		except:
			pass
