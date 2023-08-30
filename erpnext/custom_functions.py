from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import msgprint
from frappe.utils import flt, cint, nowdate, getdate, date_diff
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils.data import get_first_day, get_last_day, add_years
from frappe.desk.form.linked_with import get_linked_doctypes, get_linked_docs
from frappe.model.naming import getseries

def check_pending_approvers():
	#Material Request
	mrs = frappe.db.sql("select name, approver, transaction_date as date from `tabMaterial Request` where workflow_state = 'Waiting Approval'", as_dict=True)
	sorted_list = segregrate(mrs)
	for a in sorted_list:
		send_email(a, sorted_list[a], "Material Request")

	#Travel Authorization	
	mrs = frappe.db.sql("select name, supervisor as approver, creation as date from `tabTravel Authorization` where docstatus = 0 and document_status != 'Rejected'", as_dict=True)
	sorted_list = segregrate(mrs)
	for a in sorted_list:
		send_email(a, sorted_list[a], "Travel Authorization")

	mrs = frappe.db.sql("select name, supervisor as approver, creation as date from `tabTravel Claim` where docstatus = 0 and supervisor_approval = 0 and workflow_state not like '%Rejected%'", as_dict=True)
	sorted_list = segregrate(mrs)
	for a in sorted_list:
		send_email(a, sorted_list[a], "Travel Claim")

	mrs = frappe.db.sql("select name, leave_approver as approver, creation as date from `tabLeave Application` where docstatus = 0 and workflow_state != 'Rejected'", as_dict=True)
	sorted_list = segregrate(mrs)
	for a in sorted_list:
		send_email(a, sorted_list[a], "Leave Application")

def segregrate(master_set):
	doc_list = {}
	for a in master_set:
		if not cint(date_diff(nowdate(), a.date)) % 3:
			if doc_list.has_key(a.approver):
				doc_list[a.approver].append(a.name)
			else:
				doc_list[a.approver] = [] 
				doc_list[a.approver].append(a.name)
	return doc_list

def send_email(email = None, doc_list = None, doctype = None):
	message = "The following " + str(doctype) + " has been waiting your approval: <br />"
	num = 1
	subject = str(doctype) + " Pending your Approval"

	for a in doc_list:
		message += str(num) + "  <a href='https://erp.ns.bt/desk#Form/"+str(doctype)+"/"+str(a)+"'>" + str(a) + "</a> <br />" 
		num = num + 1
	message += "<br /><br />"
	try:
		frappe.sendmail(recipients=email, sender=None, subject=subject, message=message)
	except:
		pass
