'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
2.0		  SHIV		                   28/11/2017         get_user_info method included.
2.0               SHIV                             02/02/2018         added function nvl()
									* This function return if the arg1 is not null,
									else return arg2.
2.0               SHIV                             03/22/2018         added functon get_prev_doc()
									* This function can be used globally to fetch
									previous database record by passing arguments
									like DocType, DocName, ListOf Columns to be fetched.
2.0.190225        SHIV                             25/02/2018         * cancel_draft_doc()
									* code of `Leave Application` added
		Birendra                        25/02/2021              based on branch condition added in get_user_info                                                                      
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe import msgprint
from frappe.utils import flt, cint, nowdate, getdate, formatdate
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils.data import get_first_day, get_last_day, add_years
from frappe.desk.form.linked_with import get_linked_doctypes, get_linked_docs
from frappe.model.naming import getseries

#function to get the difference between two dates
@frappe.whitelist()
def get_date_diff(start_date, end_date):
	if start_date is None:
		return 0
	elif end_date is None:
		return 0
	else:
		return frappe.utils.data.date_diff(end_date, start_date) + 1;

##
# Check for future dates in transactions
##
def check_future_date(date):
	if not date:
		frappe.throw("Date Argument Missing")
	if getdate(date) > getdate(nowdate()):
		frappe.throw("Posting for Future Date is not Permitted")

##
# Get cost center from branch
##
def get_branch_cc(branch):
	if not branch:
		frappe.throw("No Branch Argument Found")
	cc = frappe.db.get_value("Cost Center", {"branch": branch, "is_disabled": 0, "is_group": 0}, "name")
	if not cc:
		frappe.throw(str(branch) + " is not linked to any cost center brother")
	return cc

##
# Rounds to the nearest 5 with precision of 1 by default
##
def round5(x, prec=1, base=0.5):
	return round(base * round(flt(x)/base), prec)

##
# If the document is linked and the linked docstatus is 0 and 1, return the first linked document
##
def check_uncancelled_linked_doc(doctype, docname):
	linked_doctypes = get_linked_doctypes(doctype)
	linked_docs = get_linked_docs(doctype, docname, linked_doctypes)
	for docs in linked_docs:
		for doc in linked_docs[docs]:
			if doc['docstatus'] < 2:
				frappe.throw("There is an uncancelled " + str(frappe.get_desk_link(docs, doc['name']))+ " linked with this document")

def get_year_start_date(date):
	return str(date)[0:4] + "-01-01"

def get_year_end_date(date):
	return str(date)[0:4] + "-12-31"

# Ver 2.0 Begins, following method added by SHIV on 28/11/2017
@frappe.whitelist()
def get_user_info(user=None, employee=None, cost_center=None, branch=None):
	info = {}
	
	#cost_center,branch = frappe.db.get_value("Employee", {"user_id": user}, ["cost_center", "branch"])

	if employee:
		# Nornal Employee
		cost_center = frappe.db.get_value("Employee", {"name": employee}, "cost_center")
		branch      = frappe.db.get_value("Employee", {"name": employee}, "branch")

		# GEP Employee
		if not cost_center:
			cost_center = frappe.db.get_value("GEP Employee", {"name": employee}, "cost_center")
			branch      = frappe.db.get_value("GEP Employee", {"name": employee}, "branch")

		# MR Employee
		if not cost_center:
			cost_center = frappe.db.get_value("Muster Roll Employee", {"name": employee}, "cost_center")
			branch      = frappe.db.get_value("Muster Roll Employee", {"name": employee}, "branch")
		
	elif user:
		# Normal Employee
		cost_center = frappe.db.get_value("Employee", {"user_id": user}, "cost_center")
		branch      = frappe.db.get_value("Employee", {"user_id": user}, "branch")

		# GEP Employee
		if not cost_center:
			cost_center = frappe.db.get_value("GEP Employee", {"user_id": user}, "cost_center")
			branch      = frappe.db.get_value("GEP Employee", {"user_id": user}, "branch")

		# MR Employee
		if not cost_center:
			cost_center = frappe.db.get_value("Muster Roll Employee", {"user_id": user}, "cost_center")
			branch      = frappe.db.get_value("Muster Roll Employee", {"user_id": user}, "branch")
	elif branch:
		cost_center = frappe.db.get_value("Cost Center", {"branch": branch}, "name")
		# branch      = frappe.db.get_value("Employee", {"user_id": user}, "branch")

		# GEP Employee
		if not cost_center:
			cost_center = frappe.db.get_value("GEP Employee", {"user_id": user}, "cost_center")
			branch      = frappe.db.get_value("GEP Employee", {"user_id": user}, "branch")

		# MR Employee
		if not cost_center:
			cost_center = frappe.db.get_value("Muster Roll Employee", {"user_id": user}, "cost_center")
			branch      = frappe.db.get_value("Muster Roll Employee", {"user_id": user}, "branch")
			
	warehouse   = frappe.db.get_value("Cost Center", cost_center, "warehouse")
	approver    = frappe.db.get_value("Approver Item", {"cost_center": cost_center}, "approver")
	customer    = frappe.db.get_value("Customer", {"cost_center": cost_center}, "name")

	info.setdefault('cost_center', cost_center)
	info.setdefault('branch', branch)
	info.setdefault('warehouse', warehouse)
	info.setdefault('approver',approver)
	info.setdefault('customer', customer)
	
	#return [cc, wh, app, cust]
	return info
# Ver 2.0 Ends

##
# Cancelling draft documents
##
@frappe.whitelist()
def cancel_draft_doc(doctype, docname):
	doc = frappe.get_doc(doctype, docname)
	if doc.docstatus == 1:
		frappe.throw(_("Document Cancellation is not allowed for submitted document"), title="Operation not permitted")
	if doctype == "Leave Application":    ##### Ver 2.0.190225 added by SHIV
		if doc.get("workflow_state") not in ("Draft","Rejected") and frappe.session.user not in (doc.get("leave_approver"),"Administrator"):
			frappe.throw(_("Only leave approver <b>{0}</b> ( {1} ) can cancel this document.").format(doc.leave_approver_name, doc.leave_approver), title="Operation not permitted")
		
	doc.db_set("docstatus", 2)
	
	# Updating Child tables docstatus to 2
	meta = frappe.get_meta(doctype)
	if not meta.issingle:
		if not meta.istable:
			for df in meta.get_table_fields():
				frappe.db.sql("""update `tab{0}` set docstatus=2 where parent='{1}'""".format(df.options,docname))

	if frappe.db.exists("Workflow", doctype):
		wfs = frappe.db.get_values("Workflow Document State", {"parent":doctype, "doc_status": 2}, "state", as_dict=True)
		doc.db_set("workflow_state", wfs[0].state if len(wfs) == 1 else "Cancelled")

	if doctype in ["Process MR Payment","Leave Application","Material Request","Purchase invoice", "Sales Invoice", "Journal Entry", "Direct Payment", "Payment Entry", "HSD Payment", "Mechanical Payment"]:
			doc.db_set("status", "Cancelled")
	elif doctype == "Travel Claim":
		if doc.ta:
			ta = frappe.get_doc("Travel Authorization", doc.ta)
			ta.db_set("travel_claim", None)
	elif doctype == "Job Card":
		br = frappe.get_doc("Break Down Report", doc.break_down_report)
		br.db_set("job_card", None)
	else:
		pass

	'''
	if doctype == "Material Request":
		doc.db_set("status", "Cancelled")
		doc.db_set("workflow_state", "Cancelled")
	elif doctype == "Travel Claim":
		if doc.ta:
			ta = frappe.get_doc("Travel Authorization", doc.ta)
			ta.db_set("travel_claim", None)
	elif doctype == "Imprest Recoup":
		doc.db_set("workflow_state", "Cancelled")
	elif doctype == "Imprest Receipt":
		doc.db_set("workflow_state", "Cancelled")
	elif doctype == "Job Card":
		br = frappe.get_doc("Break Down Report", doc.break_down_report)
		br.db_set("job_card", None)
	elif doctype == "Overtime Application":
		doc.db_set("workflow_state", "Cancelled")
	elif doctype == "Fund Requisition":
		doc.db_set("workflow_state", "Cancelled")
	elif doctype == "Leave Application":
		doc.db_set("workflow_state", "Cancelled")
	elif doctype == "Leave Encashment":
		doc.db.set("workflow_state", "Cancelled")
	else:
		pass
	'''        

##
#  nvl() function added by SHIV on 02/02/2018
##
def nvl(val1, val2):
	return val1 if val1 else val2

##
# generate and get the receipt number
##
def generate_receipt_no(doctype, docname, branch, fiscal_year):
	if doctype and docname:
		abbr = frappe.db.get_value("Branch", branch, "abbr")
		if not abbr:
			frappe.throw("Set Branch Abbreviation in Branch Master Record")
		name = str("CDCL/" + str(abbr) + "/" + str(fiscal_year) + "/")
		current = getseries(name, 4)
		doc = frappe.get_doc(doctype, docname)
		doc.db_set("money_receipt_no", current)
		doc.db_set("money_receipt_prefix", name)

##
#  get_prev_doc() function added by SHIV on 03/22/2018
##
@frappe.whitelist()
def get_prev_doc(doctype,docname,col_list=""):
	if col_list:
		return frappe.db.get_value(doctype,docname,col_list.split(","),as_dict=1)
	else:
		return frappe.get_doc(doctype,docname)

##
# Prepre the basic stock ledger 
##
def prepare_sl(d, args):
	sl_dict = frappe._dict({
		"item_code": d.pol_type,
		"warehouse": d.warehouse,
		"posting_date": d.posting_date,
		"posting_time": d.posting_time,
		'fiscal_year': get_fiscal_year(d.posting_date, company=d.company)[0],
		"voucher_type": d.doctype,
		"voucher_no": d.name,
		"voucher_detail_no": d.name,
		"actual_qty": 0,
		"stock_uom": d.stock_uom,
		"incoming_rate": 0,
		"company": d.company,
		"batch_no": "",
		"serial_no": "",
		"project": "",
		"is_cancelled": d.docstatus==2 and "Yes" or "No"
	})

	sl_dict.update(args)
	return sl_dict

##
# Prepre the basic accounting ledger 
##
def prepare_gl(d, args):
	"""this method populates the common properties of a gl entry record"""
	gl_dict = frappe._dict({
		'company': d.company,
		'posting_date': d.posting_date,
		'fiscal_year': get_fiscal_year(d.posting_date, company=d.company)[0],
		'voucher_type': d.doctype,
		'voucher_no': d.name,
		'remarks': d.remarks,
		'debit': 0,
		'credit': 0,
		'debit_in_account_currency': 0,
		'credit_in_account_currency': 0,
		'is_opening': "No",
		'party_type': None,
		'party': None,
		'project': ""
	})
	gl_dict.update(args)

	return gl_dict

##
# Check budget availability in the budget head
##
def check_budget_available(cost_center, budget_account, transaction_date, amount, throw_error=True):
	if str(frappe.db.get_value("Account", budget_account, "budget_check")) == "Ignore":
		return
	budget_amount = frappe.db.sql("select b.action_if_annual_budget_exceeded as action, ba.budget_check, ba.budget_amount from `tabBudget` b, `tabBudget Account` ba where b.docstatus = 1 and ba.parent = b.name and ba.account=%s and b.cost_center=%s and b.fiscal_year = %s", (budget_account, cost_center, str(transaction_date)[0:4]), as_dict=True)
	error= []
	# frappe.throw(format(query))
	#action = frappe.db.sql("select action_if_annual_budget_exceeded as action from tabBudget where docstatus = 1 and cost_center = \'" + str(cost_center) + "\' and fiscal_year = " + str(transaction_date)[0:4] + " ", as_dict=True)
	if budget_amount and budget_amount[0].action == "Ignore":
		return 
	else:
		if budget_amount and budget_amount[0].budget_check == "Ignore":
			return
		if budget_amount:
			committed = frappe.db.sql("select SUM(cb.amount) as total from `tabCommitted Budget` cb where cb.cost_center=%s and cb.account=%s and cb.po_date between %s and %s", (cost_center, budget_account, str(transaction_date)[0:4] + "-01-01", str(transaction_date)[0:4] + "-12-31"), as_dict=True)
			consumed = frappe.db.sql("select SUM(cb.amount) as total from `tabConsumed Budget` cb where cb.cost_center=%s and cb.account=%s and cb.po_date between %s and %s", (cost_center, budget_account, str(transaction_date)[0:4] + "-01-01", str(transaction_date)[0:4] + "-12-31"), as_dict=True)
			if consumed and committed:
				if consumed[0].total > committed[0].total:
					committed = consumed
			if committed:
				total_consumed_amount = flt(committed[0].total) + flt(amount)
				if flt(budget_amount[0].budget_amount) < flt(total_consumed_amount):
					error.append("Not enough budget in <b>" + str(budget_account) + "</b> under <b>" + str(cost_center) + "</b>. Budget exceeded by <b>" + str(flt(total_consumed_amount) - flt(budget_amount[0].budget_amount)) + "</b>")
		else:
			error.append("There is no budget in <b>" + str(budget_account) + "</b> under <b>" + str(cost_center) + "</b>")

	if len(error) > 0:
		if throw_error:
			frappe.throw(_("{0}").format("<br>".join(error)), title="Insufficient Budget")
		else:
			return error[0]
	else:
		return

@frappe.whitelist()
def get_cc_warehouse(branch):
	cc = get_branch_cc(branch)
	wh = frappe.db.get_value("Cost Center", cc, "warehouse")
	return {"cc": cc, "wh": wh}	

@frappe.whitelist()
def get_branch_warehouse(branch):
	cc = get_branch_cc(branch)
	wh = frappe.db.get_value("Cost Center", cc, "warehouse")
	return wh

@frappe.whitelist()
def kick_users():
	from frappe.sessions import clear_all_sessions
	clear_all_sessions()
	frappe.msgprint("Kicked All Out!")

def get_cc_customer(cc):
	customer = frappe.db.get_value("Customer", {"cost_center": cc}, "name")
	if not customer:
		frappe.throw("No Customer found for the Cost Center")
	return customer

def send_mail_to_role_branch(branch, role, message, subject=None):
	if not subject:
		subject = "Message from ERP System"
	users = frappe.db.sql_list("select a.parent from tabUserRole a, tabDefaultValue b where a.parent = b.parent and b.defvalue = %s and b.defkey = 'Branch' and a.role = %s", (branch, role))
	try:
		frappe.sendmail(recipients=users, subject=subject, message=message)
	except:
		pass

def check_account_frozen(posting_date):
	acc_frozen_upto = frappe.db.get_value('Accounts Settings', None, 'acc_frozen_upto')
	if acc_frozen_upto:
		frozen_accounts_modifier = frappe.db.get_value( 'Accounts Settings', None,'frozen_accounts_modifier')
		if getdate(posting_date) <= getdate(acc_frozen_upto) \
				and not frozen_accounts_modifier in frappe.get_roles():
			frappe.throw(_("You are not authorized to add or update entries before {0}").format(formatdate(acc_frozen_upto)))

       
def sendmail(recipent, subject, message, sender=None):
	try:
		frappe.sendmail(recipients=recipent, sender=None, subject=subject, message=message)
	except:
		pass

#
# function get_approver() added by SHIV on 2018/07/27
#
@frappe.whitelist()
def get_approver(doctype=None, employee=None, user_id=None):
	if employee:
		user_id  = frappe.get_value("Employee", employee, "user_id")
	elif user_id:
		employee = frappe.get_value("Employee", {"user_id": user_id}, "name") #CDCL9808002
	approver    = frappe.get_value("Employee", employee, "reports_to") #CDCL1203002
	approver_id = frappe.get_value("Employee", approver, "user_id") #kencho.tshering@cdcl.bt
 
	#Check for Officiating Employeee, if so, replace
	off = frappe.db.sql("""
			select officiate
			from `tabOfficiating Employee`
			where docstatus = 1
			and revoked != 1
			and CURDATE() between from_date and to_date
			and employee = %(employee)s
	""", {"employee": approver}, as_dict=True)
	if off:
		approver    = off[0].officiate	

	# If Supervisor & Approver are the same person
	role_list = frappe.get_roles(user_id)
	if str(doctype) == "Overtime Application":
		if "OT Approver" in role_list:
			approver = employee

	# Final Query
	lists = frappe.db.sql("""
		select user_id,
			employee_name,
			designation
		from tabEmployee
		where name = %(approver)s
	""", {"approver": approver})

	return lists


#
# function get_approver_query() added by SHIV on 2018/07/27
#
@frappe.whitelist()
def approver_query(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("employee"):
		employee = filters.get("employee")
		user_id  = frappe.get_value("Employee", filters.get("employee"), "user_id")
	elif filters.get("user_id"):
		id = filters.get("user_id") #sonam.tshering@cdcl.bt
		employee = frappe.get_value("Employee", {"user_id": id}, "name") #CDCL9808002
		user_id  = filters.get("user_id") #sonam.tshering@cdcl.bt
		
	approver    = frappe.get_value("Employee", employee, "reports_to") #CDCL1203002

	approver_id = frappe.get_value("Employee", approver, "user_id") #kencho.tshering@cdcl.bt

	#Check for Officiating Employeee, if so, replace
	off = frappe.db.sql("""
			select officiate
			from `tabOfficiating Employee`
			where docstatus = 1
			and revoked != 1
			and CURDATE() between from_date and to_date
			and employee = %(employee)s
	""", {"employee": approver}, as_dict=True)
	if off:
		approver    = off[0].officiate	

	# If Supervisor & Approver are the same person
	role_list = frappe.get_roles(user_id)
	if filters.get("doctype") == "Overtime Application":
		if "OT Approver" in role_list:
			approver = employee

	# Final Query
	lists = frappe.db.sql("""
		select user_id,
			employee_name,
			designation
		from tabEmployee
		where name = %(approver)s
	""", {"approver": approver})

	return lists

