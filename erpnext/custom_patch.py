from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe import msgprint
from frappe.utils import rounded, flt, cint, now, nowdate, getdate, get_datetime,now_datetime
from frappe.utils.data import date_diff, add_days, get_first_day, get_last_day, add_years
#from erpnext.hr.hr_custom_functions import get_month_details, get_company_pf, get_employee_gis, get_salary_tax, update_salary_structure
from erpnext.hr.hr_custom_functions import get_month_details, get_salary_tax
from datetime import timedelta, date
from erpnext.custom_utils import get_branch_cc, get_branch_warehouse, prepare_gl
from erpnext.accounts.utils import make_asset_transfer_gl
from datetime import datetime
import os
import subprocess
from erpnext.accounts.doctype.imprest_receipt.imprest_receipt import get_opening_balance, update_dependencies

def update_mr_cc():
        li = []
        count = 0
        neg = 0
        for a in frappe.db.sql(""" select name, branch from `tabMaterial Request` """, as_dict = 1):
                cc  = frappe.db.sql(""" select name from `tabCost Center` where branch = "{0}" """.format(a.branch), as_dict = 1)
                if cc:
                        frappe.db.sql(""" update `tabMaterial Request` set cost_center = "{0}" where name = "{1}" 
                                """.format(cc[0].name, a.name))
                        count += 1
                        print count, "updating {0}".format(a.name)
                else:
                        li.append(a.branch)
                        neg += 1
        print neg, "cost center not found {0}".format(li)

def update_po_cc():
        li = []
        count = 0
        neg = 0
        for a in frappe.db.sql(""" select name, branch from `tabPurchase Order` """, as_dict = 1):
                cc  = frappe.db.sql(""" select name from `tabCost Center` where branch = "{0}" """.format(a.branch), as_dict = 1)
                if cc:
                        frappe.db.sql(""" update `tabPurchase Order` set cost_center = "{0}" where name = "{1}" """.format(cc[0].name, a.name))
                        count += 1
                        print count, "updating {0}".format(a.name)
                else:
                        li.append(a.branch)
                        neg += 1
        print neg, "cost center not found {0}".format(li)

def update_cus():
	count = 0
        for a in frappe.db.sql(""" select name, issued_to from `tabAsset` """, as_dict = 1):
		if a.issued_to not in ('GYAL20441'):
			issued_to = frappe.get_doc("Employee", a.issued_to).employee_name
			frappe.db.sql(""" update `tabAsset` set employee_name  = "{0}" where name = '{1}'""".format(issued_to, a.name))
			count += 1
			print count, a.name, issued_to

def update_parent_cc():
	li = frappe.db.sql(""" select branch, name from `tabPurchase Order`""", as_dict =1)
	for a in li:
		if a.branch not in ('Commandant Residence (NS-B)'):
			cc = frappe.get_doc("Cost Center", {'branch': a.branch})
			parent = cc.parent_cost_center
			if cc.is_group:
				parent = cc.name
			frappe.db.sql(""" update `tabPurchase Order` set parent_cc = '{0}' where name = '{1}'
			""".format(parent, a.name))

def dash_test():
	import jwt
	import time

	METABASE_SITE_URL = "https://erp.ns.bt/metabase"
	METABASE_SECRET_KEY = "8e8db02d3fdc1c5ae4252b4b9cdc036c9050f7c86659fce6ba043f7bcfe833d4"

	payload = {
	  "resource": {"dashboard": 10},
	  "params": {
	    
	  }
	}
	token = jwt.encode(payload, METABASE_SECRET_KEY, algorithm="HS256")

	iframeUrl = METABASE_SITE_URL + "/embed/dashboard/" + token + "#theme=night&bordered=true&titled=true"
	print(iframeUrl)


def update_aa():
	for a in frappe.db.sql(""" select name from `tabSalary Slip` where employment_type = 'GCE' and fiscal_year = '2021' and month = '05'""", as_dict = 1):
		frappe.db.sql(""" delete from `tabSalary Detail` where parent = '{0}'""".format(a.name))
		print a.name

def update_impp():
	for a in frappe.db.sql(""" select name from `tabImprest Recoup` where name = 'IMPP2023000120'""", as_dict =1):
		doc = frappe.get_doc("Imprest Recoup", a.name)
		#doc.post_receipt_entry()
		#update_dependencies(doc.branch, doc.imprest_type, doc.entry_date)
                #doc.post_gl_entry()
                #doc.consume_budget()
		doc.make_gl_entry()
		frappe.db.commit()
		print a.name

def update_tc():
	for a in frappe.db.sql(""" select name from `tabTravel Claim` where name = 'TC201100055'""", as_dict =1):
		doc = frappe.get_doc("Travel Claim", a.name)
		doc.post_journal_entry()
		frappe.db.commit()
		print "Journal  is submitted"

def update_iip():
	for a in frappe.db.sql(""" select name, equipment from `tabPOL` where equipment = 'EQUIP210016'""", as_dict =1):
		doc = frappe.get_doc("POL", a,name)
		eq = frappe.get_doc("Equipment", a.equipment)
		frappe.db.sql(""" update `tabPOL` set equipment_number '{0}' , equipment_type = '{1}', 
			fuel_book = '{2}', equipment_category = '{2}' where name = '{3}'
		""".format(eq.equipment_number, eq.equipment_type, eq.fuelbook, eq.equipment_category, a.name)) 
def update_iipol():
	count = 1
	for a in frappe.db.sql(""" select name from `tabIssue POL` where branch = 'GA-Khotokha' and pol_type = '100167' 
			and docstatus = 1""", as_dict = 1):
		dat = frappe.db.sql(""" select name from `tabPOL Entry` where branch = 'GA-Khotokha' and 
			pol_type = '100167' and type = 'Issue' and reference_type = 'Issue POL' 
			and docstatus = 1 and reference_name = '{0}'""".format(a.name, as_dict = 1))
		if not dat:
			doc = frappe.get_doc("Issue POL", a.name)
			con = frappe.new_doc("POL Entry")
			con.flags.ignore_permissions = 1
			con.equipment = doc.tanker
			con.pol_type = doc.pol_type
			con.branch = doc.branch
			con.date = doc.posting_date
			con.posting_time = doc.posting_time
			con.qty = doc.total_quantity
			con.reference_type = "Issue POL"
			con.reference_name = doc.name
			con.type = "Issue"
			con.is_opening = 0
			con.submit()
			count += 1
			print count

def update_project_entry():
        #for a in frappe.db.sql(""" select name from `tabTarget Entry Sheet`""", as_dict = 1):
        for a in frappe.db.sql(""" select name from `tabAchievement Entry Sheet`""", as_dict = 1):
                #doc = frappe.get_doc("Target Entry Sheet", a.name)
                doc = frappe.get_doc("Achievement Entry Sheet", a.name)
                print a.name
                doc.save()

def update_operator():
	doc = frappe.get_doc("Muster Roll Employee", '12003000958')
	row = doc.append ("internal_work_history",{})
	row.branch  = "GA-Pemathang"
	row.cost_center = "GA-Pemathang - GYALSUNG"
	row.from_date = '2020-03-01'
	row.save()

def update_ot():
        count = 0
        for a in frappe.db.sql(""" select name from `tabProcess Overtime Payment`""", as_dict = 1):
                doc = frappe.get_doc("Process Overtime Payment", a.name)
                ot_account = frappe.db.get_single_value("HR Accounts Settings", "overtime_account")
                frappe.db.sql(""" update `tabProcess Overtime Payment` set ot_account = '{0}' where name = '{1}'""".format(ot_account, doc.name))
                print a.name, count
		
def update_pro():
        for a in frappe.db.sql(""" select name, physical_progress_weightage from `tabProject` where is_group = 1""", as_dict = 1):
                frappe.db.sql(""" update `tabProject` set parent_weightage = {0} where parent_project = "{1}" """.format(a.physical_progress_weightage, a.name))
                print a.name


def validate_proj():
	count = 0
	for a in frappe.db.sql(""" select name from `tabProject`""", as_dict = 1):
		doc = frappe.get_doc("Project", a.name)
		count += 1
		doc.save()
		print count, a.name

def update_la():
        count = 0
        for a in frappe.db.sql(""" select name, employee from `tabLeave Allocation` where docstatus = 1""", as_dict = 1):
                emp = frappe.get_doc("Employee", a.employee).employment_type
                frappe.db.sql(""" update `tabLeave Allocation` set employee_type = '{0}' where name = '{1}'""".format(emp, a.name))
                count += 1
                print a.name, count

def update_ipol():
	import csv
        with open('/home/frappe/erp/ipol.csv','r') as f:
                data = csv.reader(f)
                count = 1
                for row in data:
			dat = frappe.db.sql(""" select name from `tabPOL Entry` where branch = 'GA-Jamtsholing' and 
				pol_type = '100167' and type = 'Issue' and reference_type = 'Issue POL' 
				and docstatus = 1 and reference_name = '{0}'""".format(row[0], as_dict = 1))
			if not dat:
				doc = frappe.get_doc("Issue POL", row[0])
				con = frappe.new_doc("POL Entry")
				con.flags.ignore_permissions = 1
				con.equipment = doc.tanker
				con.pol_type = doc.pol_type
				con.branch = doc.branch
				con.date = doc.posting_date
				con.posting_time = doc.posting_time
				con.qty = doc.total_quantity
				con.reference_type = "Issue POL"
				con.reference_name = doc.name
				con.type = "Issue"
				con.is_opening = 0
				con.submit()
				count += 1 
				print count
	
def update_dsa():
	for a in ("TA210300019", "TA210200042", "TA210200041"):
		doc = frappe.get_doc("Travel Authorization", a)
		doc.set_dsa_rate()

def update_la():
        count = 0
        for a in frappe.db.sql(""" select name, employee from `tabLeave Allocation` where docstatus = 1""", as_dict = 1):
                emp = frappe.get_doc("Employee", a.employee).employment_type
                frappe.db.sql(""" update `tabLeave Allocation` set employee_type = '{0}' where name = '{1}'""".format(emp, a.name))
                count += 1
                print a.name, count


def update_budget_tot():
	count = 1
	for a in frappe.db.sql(""" select name from `tabBudget` where actual_total = '' and docstatus = 1""", as_dict = 1):
		doc = frappe.get_doc("Budget", a.name)
		doc.validate()
		doc.submit()
		count += 1
		print count, a.name

def update_project():
	for a in frappe.db.sql(""" select name from `tabProject` """, as_dict = 1, debug = 1):
		doc = frappe.get_doc("Project", a.name)
		doc.save()
		doc.submit()
		print a.name

'''def update_progress():
	count = 1
	for a in frappe.db.sql(""" select name, physical_progress_weightage from `tabProject` where is_group = 1""", as_dict = 1):
		frappe.db.sql(""" update `tabProject` set parent_weightage = {0} where name = '{1}'
		""".format(a.physical_progress_weightage, a.name))
		count += 1 
		print count, a.name
'''
def add_comment():
	count = 0
	for a in frappe.db.sql(""" select name from `tabLeave Allocation` b where b.from_date = '2021-01-01' and b.to_date = '2021-12-31' and b.leave_type = 'Earned Leave' and b.docstatus = 2""", as_dict = 1):
		doc = frappe.get_doc("Leave Allocation", a.name)
		doc.add_comment('Comment', text='Cancelled the Allocation as the system is configured to allocate el on monthly basis')
		count+=1 
		print count, doc.name


def update_musterroll2():
	for a in frappe.db.sql(" select name, cost_center, payment_jv, month, fiscal_year, employee_type from `tabProcess MR Payment` where fiscal_year = '2021' and month = 'Jan'", as_dict = 1):
		
		frappe.db.sql(""" update `tabProcess MR Payment` set docstatus = 0 where name = '{0}'""".format(a.name))
		frappe.db.sql(""" update `tabMR Payment Item` set docstatus = 0 where parent = '{0}'""".format(a.name))
		if a.payment_jv:
			frappe.db.sql(""" delete from `tabJournal Entry` where name = '{0}'""".format(a.payment_jv))
		doc = frappe.get_doc("Process MR Payment", a.name)
		doc.save()
		print  a.name, a.cost_center, a.payment_jv, a.month, a.fiscal_year, a.employee_type

def update_musterroll1():
	count = 1
	for a in frappe.db.sql(" select parent, rate_per_day, rate_per_hour from `tabMusterroll` order by parent, from_date asc", as_dict = 1):
		doc = frappe.get_doc("Muster Roll Employee", a.parent)
		if doc.status == 'Active':
			doc.db_set("project", '')
			doc.db_set("rate_per_day", a.rate_per_day)
			doc.db_set("rate_per_hour", flt(a.rate_per_day)/8)
			count += 1
			#doc.save()
			print count, doc.name, a.parent, a.rate_per_day, a.rate_per_hour

def travel_advance():
	doc = frappe.get_doc("Travel Authorization", 'TA201200016-2')
	doc.check_advance()
	print doc.name

def update_mrr():
        for a in frappe.db.sql(""" select name from `tabMuster Roll Employee`""", as_dict = 1):
                rate = frappe.db.sql(""" select rate_per_day from `tabMusterroll` where parent = '{0}' and docstatus <= 1 order by from_date desc limit 1""".format(a.name), as_dict = 1)
                doc = frappe.get_doc("Muster Roll Employee", a.name)
                doc.db_set("rate_per_day", rate[0].rate_per_day)
                print doc.name

def cancel_ipol():
	count = 0
	for a in frappe.db.sql(""" select name from `tabIssue POL` where cost_center in ('Jamtsholing - GYALSUNG', 'GA-Jamtsholing - GYALSUNG') and docstatus <= 1 order by posting_date desc""", as_dict =1):
		doc = frappe.get_doc("Issue POL", a.name)
		doc.db_set("docstatus", 2)
		count += 1
		doc.add_comment('Comment', text='Cancelled As there is issue while cancelling from Fleet Manager/DPM account') 
		print a.name, count

def update_ipol_branch():
	count = 0
	for a in frappe.db.sql(""" select equipment, name from `tabPOL Issue Report Item`""", as_dict = 1):
		doc = frappe.get_doc("Equipment", a.equipment).branch
		frappe.db.sql(""" update `tabPOL Issue Report Item` set equipment_branch = '{0}' where name = '{1}'""".format(doc, a.name))
		count += 1 
		print a.name , count


def update_pol_branch():
	count = 0
	for a in frappe.db.sql(""" select name, equipment from `tabPOL`""", as_dict = 1):
		eq = frappe.get_doc("Equipment", a.equipment).branch
		frappe.db.sql(""" update `tabPOL` set equipment_branch = '{0}' where name = '{1}'""".format(eq, a.name))
		count +=1 
		print a.name, count
		
		

def update_asset_details():
	count = 0
	for a in frappe.db.sql(" select name, issued_to from `tabAsset Issue Details`", as_dict = 1):
		emp = frappe.get_doc("Employee", a.issued_to).employee_name
		frappe.db.sql(""" update `tabAsset Issue Details` set issued_to_name = "{0}" where name = '{1}'""".format(emp, a.name), debug = 1)
		count += 1
		print a.name, count

def ipol():
	doc = frappe.get_doc("Issue POL", 'IPOL230700228')
	doc.submit()
	print doc.name

def submit_imprest():
	doc = frappe.get_doc("Imprest Recoup", 'IMPP2023000167')
	doc.submit()
	print doc.name

def ipol1():
	import csv
        with open('/home/frappe/erp/ipol.csv','r') as f:
                data = csv.reader(f)
                count = 1
                for row in data:
			doc = frappe.get_doc("Issue POL", row[0])
			doc.submit()
			#doc.cancel()
			print doc.name

def rpol():
	pol = ["POL230700358"]
	for a in pol:
		doc = frappe.get_doc("POL", a)
		doc.submit()
		print (a)

def ss():
	ss = ["GYAL22111/SSL/202203/00019"]
	for a in ss:
		doc = frappe.get_doc("Salary Slip", a)
		doc.save()
		print (a)

def submit_se():
	doc = frappe.get_doc("Stock Entry", "SEMI23064657")
	doc.submit()
	print doc.name

def submit_ca():
	doc = frappe.get_doc("Cost Appropriation", "CA2023000053")
	doc.submit()
	frappe.db.commit()
	print (doc.name)

def cancel_se():
	doc = frappe.get_doc("Stock Entry", "SEMI23075690")
	doc.cancel()
	frappe.db.commit()
	print (doc.name)

def submit_je():
	doc = frappe.get_doc("Journal Entry", "JEJV230800417")
	doc.submit()
	frappe.db.commit()
	print (doc.name)

def cancel_je():
	doc = frappe.get_doc("Journal Entry", "JEBP230700130")
	doc.cancel()
	frappe.db.commit()
	print (doc.name)

def submit_pr():
	doc = frappe.get_doc("Purchase Receipt", "PRSM22050115")
	doc.cancel()
	print doc.name

def save_sm():
	doc = frappe.get_doc("Supplier Monitoring", "SMT220001")
	doc.save()
	print doc.name

def cancel_pi():
	doc = frappe.get_doc("Purchase Invoice", "PISM23080222")
	doc.cancel()
	frappe.db.commit()
	print(doc.name)

def cancel_exp_allocation():
	doc = frappe.get_doc("Expense Allocation", "EA2023000444")
	doc.cancel()
	frappe.db.commit()
	print(doc.name)

def submit_la():
	doc = frappe.get_doc("Leave Application", "LAP221200224")
	doc.submit()
	print doc.name

def email_test():
	recipients = 'jairajrai@gyalsunginfra.bt'
	subject = "testing"
	doc = frappe.get_doc("Material Request", 'MRMR20120018')
	message = """Dear Sir/Madam, <br>  {0} has requested you to verify the Material Request <b> {1}. Check ERP System for More Info. </b> <br> Thank You""".format(frappe.get_doc("User", doc.owner).full_name, str(frappe.get_desk_link("Material Request", doc.name)))
	frappe.sendmail(recipients=recipients, sender=None, subject=subject, message=message)
	print "message sent"

def update_requested_by():
	count = 0
	for a in frappe.db.sql(""" select name, owner from `tabMaterial Request`""", as_dict = 1):
		user = frappe.get_doc("Employee", {'user_id': a.owner})
		frappe.db.sql(""" update `tabMaterial Request` set requested_by = "{0}({1})" where owner = '{2}' and name = '{3}'
				""".format(user.employee_name, user.designation, a.owner, a.name), debug = 1)
		count += 1
		print a.name, count

	

def update_ot_acc():
	count = 0
        for b in frappe.db.sql(" select name, branch from `tabProcess Overtime Payment`", as_dict =1):
                expense_bank_account = frappe.get_doc("Branch", b.branch).expense_bank_account
                frappe.db.sql(" update `tabProcess Overtime Payment` set expense_bank_account = '{0}' where name = '{1}'".format(expense_bank_account, b.name))

	count += 1 
	print b.name, count

def update_ot_cc():
        for b in frappe.db.sql(" select name, employee, branch from `tabOvertime Application`", as_dict = 1):
                doc = frappe.get_doc("Overtime Application", b.name)
                #cc = frappe.get_doc("Cost Center", {'branch': b.branch}).name
                cc = frappe.get_doc("Employee", b.employee).bank_name
                doc.db_set("bank_name", cc)
                print doc.name, cc

def update_dfg_housing():
	count = 0
	for a in frappe.db.sql("select name from `tabDFG Housing`", as_dict = 1):
		doc = frappe.get_doc("DFG Housing", a.name)
		doc.on_update_after_submit()
		count += 1

		print a.name, count


def update_tds():
        count = 0
        for a in frappe.db.sql("""
                select name, account from `tabTDS Remittance` where docstatus = 1""", as_dict = 1):
                branch = frappe.db.get_value("Branch", {'expense_bank_account': a.account}, "name")
                cost_center = frappe.get_doc("Cost Center", {'branch': branch}).name
                gl = frappe.db.sql(""" select name from `tabGL Entry` where voucher_type = 'TDS Remittance' and voucher_no = '{0}'
                """.format(a.name), as_dict = 1)
                for b in gl:
                        frappe.db.sql(""" update `tabGL Entry` set cost_center = '{0}' where name = '{1}' and voucher_type = 'TDS Remittance' and voucher_no = '{2}'""".format(cost_center, b.name, a.name))
                
		count += 1
        	print count, a.name

def upload_att():
        import csv
        with open('/home/frappe/erp/att1.csv','r')as f:
                data = csv.reader(f)
                count = 1
                for row in data:
                        doc = frappe.new_doc("Attendance")
                        doc.branch = 'NS-Head Office'
                        doc.company = 'GYALSUNG INFRA'
                        doc.employee = row[0]
                        doc.employee_name = row[1]
                        doc.status = row[3]
                        doc.att_date = row[2]
                        doc.save()
                        doc.submit()
                        count += 1
                        print count, doc.name, doc.att_date

def update_cc():
	for a in frappe.db.sql("select name from `tabCost Center` where modified >= '2020-10-23'", as_dict = 1):
		activity_code = a.name[0:4] + '0'
		activity_sub_code = a.name[0:5]
		
		frappe.db.sql(""" update `tabCost Center` set activity_code = '{0}', activity_sub_code = '{1}' where name = '{2}'
			""".format(activity_code, activity_sub_code, a.name))
		print type(activity_code), activity_code, activity_sub_code, a.name

def update_pe():
        for b in frappe.db.sql("""
                select pe.name from `tabPayment Entry` pe, `tabPayment Entry Deduction` ped where ped.parent = pe.name and pe.docstatus = 1""", as_dict = 1):
                doc = frappe.get_doc("Payment Entry", b.name)
                loss_and_gain = sum([flt(d.amount) for d in doc.get("deductions")])
                frappe.db.sql("""
                        update `tabPayment Entry` set loss_and_gain = {0} where name = '{1}'""".format(loss_and_gain, b.name))
                print b.name


def update_tci():
	for a in ('TC200800017', 'TC200800022', 'TC200800019', 'TC200800018'):
		doc = frappe.get_doc("Travel Claim Item", {'parent': a}).name
		doc.reload()

 
def update_branch():
	count = 0
	for d in frappe.db.sql(" select name, branch from `tabEmployee` where status = 'Active'", as_dict =1):
		doc = frappe.get_doc("Employee Internal Work History", {"parent": d.name})
		frappe.db.sql(" update `tabEmployee Internal Work History` set branch = '{0}' where parent = '{1}'".format(d.branch, d.name))
		count += 1
		print count


def update_cid_ss():
	count = 0
        for a in frappe.db.sql("select e.name, e.passport_number from tabEmployee e  where e.name = (select employee from `tabSalary Slip` s where e.name =s.employee)", as_dict=1):
        	ss =frappe.get_doc("Salary Slip", {"employee" : a.name})
	        frappe.db.sql("update `tabSalary Slip` set cid = '{0}' where employee = '{1}' and docstatus = 1" .format(a.passport_number, a.name))
		count += 1
		print count

def update_emp():
	count = 0
	for emp in frappe.db.sql(" select name from `tabEmployee` where employment_type = 'GCE' and status = 'Active'", as_dict = True):
		sal_doc = frappe.get_doc("Salary Structure", {'employee': emp.name})
		# emp_doc = frappe.get_doc("Employee", emp.name)
		# emp_doc.save()
		#frappe.db.sql(" update `tabSalary Structure` set employee = '{0}' where employee = '{0}'".format(emp_doc.name, emp.name))
		sal_doc.save()
		count += 1
		print count, sal_doc.name

def save_ss():
	count = 0
	for ss in frappe.db.sql(" select name from `tabSalary Structure` where is_active = 'Yes'", as_dict = True):
		doc = frappe.get_doc("Salary Structure", ss.name)
		doc.save()
		count += 1

		print ss.name, count
	
def update_oap():
	count = 0
	for a in frappe.db.sql(" select name from `tabOpen Air Prisoner` where status = 'Active'", as_dict = True):
		doc = frappe.get_doc("Open Air Prisoner", a.name)
		doc.save()
		count += 1

		print a.name, count


def update_mr():
	doc = frappe.get_doc("Process MR Payment", 'MRP220600007')
	doc.submit()
	print doc.name
	



def check_stock_gl():
	for a in frappe.db.sql("select name, branch from `tabStock Entry` where docstatus = 1 and name = 'SEMI19030600'", as_dict=1):
		try:
			cc = get_branch_cc(a.branch)
			sed = frappe.db.sql("select name from `tabStock Entry Detail` where parent = %s and cost_center != %s", (a.name, cc))
			if sed:
				print(a.name)
				frappe.db.sql("update `tabStock Entry Detail` set cost_center = %s where parent = %s", (cc, a.name))
				frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
				doc = frappe.get_doc("Stock Entry", a.name)
				doc.make_gl_entries()
		except:
			cc = "Dummy"

def update_gl_stock_2019():
	for a in frappe.db.sql("select name from `tabStock Entry` where name = 'SEMT18070012'", as_dict=1):
		print(str(a.name))
		self = frappe.get_doc("Stock Entry", a.name)
		self.make_gl_entries()

def test_get_branch():
	for a in frappe.db.sql("select name from `tabStock Entry` where docstatus = 1 and purpose = 'Material Transfer' and posting_date between '2019-01-01' and '2019-12-31' and name = 'SEMT19010037'", as_dict=1):
		print(a.name)
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
		doc = frappe.get_doc("Stock Entry", a.name)
		doc.make_gl_entries()

def update_wh_branch():
        counter =0
        for t in frappe.get_all("Warehouse", ["name", "branch"]):
                if not frappe.db.exists("Warehouse Branch", {"parent" :t.name }):
                        counter +=1
                        print counter, t.name
                        doc = frappe.get_doc("Warehouse", t.name)
                        row = doc.append ("items",{})
                        row.branch  = t.branch
                        row.save()
                        print t
        print 'dona saving .........'


def asset_test():
	for a in frappe.db.sql("select name, asset_category, opening_accumulated_depreciation as oad from tabAsset where asset_category = 'Machinery & Equipment(10 Years)' and docstatus = 1 and status not in ('Scrapped', 'Sold')", as_dict=1):
		accu_ar = frappe.db.sql("""select
                	gl.accumulated_depreciation_amount as ac
                        from `tabDepreciation Schedule` gl, tabAsset ass
                        where gl.parent = ass.name
                        and gl.schedule_date <= '2018-12-31'
                        and gl.docstatus = 1
			and ass.name = '{0}'
                        and gl.journal_entry is not null 
			order by gl.schedule_date desc limit 1""".format(a.name), as_dict=1)
		opening = a.oad
		if accu_ar:
			opening = accu_ar[0].ac
		
		gl_acc = frappe.db.sql("select name, sum(credit) as cr, sum(debit) as dr from `tabGL Entry` where account like '%Depreciation -Machinery & Equipment(10 Years) - CDCL' and voucher_type not in ('Asset Movement', 'Bulk Asset Transfer') and posting_date < '2019-01-01' and against_voucher = '{0}'".format(a.name), as_dict=1)
		gl_open = 1 
		if gl_acc:
			gl_open = gl_acc[0].cr
	
		if not gl_open:	
			gl_open = 1
		if flt(opening) - flt(gl_open) > 1 or flt(opening) - flt(gl_open) < -1:
			print str(a.name) + " ==> " + str(opening) + " : " + str(gl_open)

def change_pol_cc():
	for a in frappe.db.sql("select distinct  voucher_no from `tabGL Entry` where account = 'Clearing Account - CDCL' and posting_date > '2018-12-31';", as_dict=1):
		pol = frappe.get_doc("POL", a.voucher_no)
		print(pol.equipment_warehouse)
		frappe.db.sql("update `tabGL Entry` set account = %s where voucher_no = %s", (pol.equipment_warehouse, a.voucher_no))

def update_musterroll():
	MR = frappe.db.sql("select rate_per_day, rate_per_hour, joining_date, name from `tabMuster Roll Employee`;", as_dict=1)
	counter = 0
        for i in MR:
                counter += 1
                
                doc = frappe.get_doc("Muster Roll Employee", i.name)
                row = doc.append("musterroll", {})
                row.rate_per_day    = i.rate_per_day
                row.rate_per_hour           = i.rate_per_hour
                row.from_date             = i.joining_date
                row.save()
def change_dn():
	for a in frappe.db.sql("select name, branch from `tabDelivery Note` where docstatus = 1 and posting_date > '2018-12-31'", as_dict=1):
		cc = get_branch_cc(a.branch)
		print(cc)
		frappe.db.sql("update `tabDelivery Note Item` set cost_center = %s where parent = %s", (cc, a.name))
		frappe.db.sql("update `tabGL Entry` set cost_center = %s where voucher_no = %s", (cc, a.name))

def change_si():
	for a in frappe.db.sql("select name, branch from `tabSales Invoice` where docstatus = 0 and posting_date > '2018-12-31'", as_dict=1):
		cc = get_branch_cc(a.branch)
		print(cc)
		frappe.db.sql("update `tabSales Invoice Item` set cost_center = %s where parent = %s", (cc, a.name))
		frappe.db.sql("update `tabGL Entry` set cost_center = %s where voucher_no = %s", (cc, a.name))

def change_cc():
	for a in frappe.db.sql("select name, branch from `tabStock Entry` where docstatus = 0 and posting_date > '2018-12-31'", as_dict=1):
		cc = get_branch_cc(a.branch)
		print(cc)
		frappe.db.sql("update `tabStock Entry Detail` set cost_center = %s where parent = %s", (cc, a.name))
		frappe.db.sql("update `tabGL Entry` set cost_center = %s where voucher_no = %s", (cc, a.name))
		"""for b in frappe.db.sql("select cost_center from `tabGL Entry` where voucher_no = %s and cost_center != %s", (a.name, cc), as_dict=1)
			print()
		"""
def update_bank():
	for a in frappe.db.sql("select id_card, bank, account_no, designation from `tabMuster Roll Employee", as_dict=1):
		bank1 =a.bank
		account = a.account_no
		designation1= a.designation
		frappe.db.sql("update `tabMR Payment Item` set bank = %s, account_no = %s, designation = %s where id_card = %s", (bank1, account, designation1, a.id_card))

def get_cc():
	print(frappe.defaults.get_defaults().cost_center)

def get_diff_asset():
        for a in frappe.db.sql("select name, asset_category, asset_account from tabAsset where docstatus = 1", as_dict=1):
                as_acc = frappe.db.get_value("Asset Category Account", {"parent": a.asset_category}, "fixed_asset_account")
                if as_acc != a.asset_account:
                        print(str(a.name) + "   :  " + str(as_acc) + "  ==> " + str(a.asset_account))


def update_equipment():
        els = frappe.db.sql("select name from tabEquipment", as_dict=1)
        for a in els:
                print a.name
                doc = frappe.get_doc("Equipment", a.name)
                doc.save()
                frappe.db.commit()

def check_ds():
	#for a in frappe.db.sql("select b.name as ass_name, a.schedule_date as dep_date, a.name, b.residual_value, b.expected_value_after_useful_life as ev, b.gross_purchase_amount as gross, b.value_after_depreciation as vad, a.accumulated_depreciation_amount as ada, a.depreciation_amount as da from `tabDepreciation Schedule` a, tabAsset b where a.parent = b.name and b.docstatus = 1 and a.journal_entry is null and b.status in ('Partially Depreciated', 'Submitted') and residual_value > 0 order by b.name, a.schedule_date", as_dict=1):
	for a in frappe.db.sql("select b.name as ass_name, a.schedule_date as dep_date, a.name, b.residual_value, b.expected_value_after_useful_life as ev, b.gross_purchase_amount as gross, b.value_after_depreciation as vad, a.accumulated_depreciation_amount as ada, a.depreciation_amount as da from `tabDepreciation Schedule` a, tabAsset b where a.parent = b.name and b.docstatus = 1 and a.journal_entry is null and b.status in ('Partially Depreciated', 'Submitted') and residual_value > 0 and a.accumulated_depreciation_amount > (b.gross_purchase_amount - b.residual_value - b.expected_value_after_useful_life) order by b.name, a.schedule_date", as_dict=1):
		new_accu = rounded(flt(a.gross) - flt(a.residual_value) - flt(a.ev), 2)
		new_dep = rounded(flt(a.ada) - new_accu, 2)
		print(str(a.ass_name) + " ==> " + str(a.dep_date) + " : " + str(new_dep))
		frappe.db.sql("update `tabDepreciation Schedule` set depreciation_amount = %s, accumulated_depreciation_amount = %s where name = %s", (new_dep, new_accu, a.name))

def delete_ds():
	for a in frappe.db.sql("select a.name as dname from `tabDepreciation Schedule` a, tabAsset b where a.parent = b.name and b.docstatus = 1 and a.journal_entry is null and b.value_after_depreciation = b.expected_value_after_useful_life;", as_dict=1):
		frappe.db.sql("delete from `tabDepreciation Schedule` where name = %s", a.dname)

def import_asset():
	lines = [line.rstrip('\n') for line in open('/home/kinley/erp/asset_file.csv')]
	for line in lines:
		a = line.split(",")
		print(a[0])
		frappe.db.sql("update tabAsset set residual_value = %s, value_after_depreciation = %s where name = %s", (a[1], 1, a[0]))

def adjust_residual():
	for a in frappe.db.sql("select name, value_after_depreciation as vad, residual_value as rv, expected_value_after_useful_life as ev from tabAsset where value_after_depreciation < 0 and docstatus = 1", as_dict=1):
		val = str(rounded(flt(a.rv) + flt(a.vad) - flt(a.ev), 2))
		frappe.db.sql("update tabAsset set residual_value = %s and value_after_depreciation = %s where name = %s", (val, a.ev, a.name))
		print(str(a.name) + "  :  " + str(rounded(flt(a.rv) + flt(a.vad) - flt(a.ev), 2)))

def pass_open_accu():
	for a in frappe.db.sql("select name, creation from tabAsset where opening_accumulated_depreciation > 0 and purchase_date >= '2018-01-01' and docstatus = 1 order by creation", as_dict=1):
		print(a.name)
		doc = frappe.get_doc("Asset", a.name)
		doc.make_opening_accumulated_gl_entry()

def adjust_direct_con():
	for a in frappe.db.sql("select name from tabPOL where direct_consumption = 1 and docstatus = 1 and posting_date > '2018-03-31'", as_dict=1):
		print(a.name)
		self = frappe.get_doc("POL", a.name)

		if self.hiring_warehouse:
			wh = self.hiring_warehouse
		else:
			wh = self.equipment_warehouse
		wh_account = frappe.db.get_value("Account", {"account_type": "Stock", "warehouse": wh}, "name")
		if not wh_account:
			frappe.throw(str(wh) + " is not linked to any account.")
		cl_account = "Clearing Account - CDCL"

		map_rate = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": a.name, "actual_qty": ["<", 0]}, "valuation_rate")
		map_amount = flt(map_rate) * flt(self.qty)

		if self.hiring_cost_center:
			cc = self.hiring_cost_center
		else:
			cc = get_branch_cc(self.equipment_branch)

		gl_entries = []

                gl_entries.append(
                        prepare_gl(self, {"account": wh_account,
                                         "debit": flt(self.total_amount),
                                         "debit_in_account_currency": flt(self.total_amount),
                                         "cost_center": cc,
                                        })
                        )

                gl_entries.append(
                        prepare_gl(self, {"account": cl_account,
                                         "credit": flt(self.total_amount),
                                         "credit_in_account_currency": flt(self.total_amount),
                                         "cost_center": cc,
                                        })
                        )

                gl_entries.append(
                        prepare_gl(self, {"account": cl_account,
                                         "debit": flt(map_amount),
                                         "debit_in_account_currency": flt(map_amount),
                                         "cost_center": cc,
                                        })
                        )

                gl_entries.append(
                        prepare_gl(self, {"account": wh_account,
                                         "credit": flt(map_amount),
                                         "credit_in_account_currency": flt(map_amount),
                                         "cost_center": cc,
                                        })
                        )
		
                from erpnext.accounts.general_ledger import make_gl_entries
		make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=False)

def adjust_sr():
	#for a in frappe.db.sql("select name from `tabStock Reconciliation` a where docstatus = 1 and posting_date between '2018-01-01' and '2018-12-31' and not exists (select 1 from `tabGL Entry` where voucher_no = a.name)", as_dict=1):
	print("Starting")
	frappe.db.sql("delete from `tabGL Entry` where voucher_no = 'SR/000053'")
	doc = frappe.get_doc("Stock Reconciliation", 'SR/000053')
	doc.make_gl_entries()
	print("DONE")

def check_it():
	for a in frappe.db.sql("select a.name, b.warehouse  from `tabDelivery Note` a, `tabDelivery Note Item` b where a.name = b.parent and a.docstatus = 1 and a.posting_date > '2017-12-31'", as_dict=1):
		stock = frappe.db.sql("select sum(actual_qty * valuation_rate) as amount from `tabStock Ledger Entry` where voucher_no = %s", a.name, as_dict=1)
		if stock[0]['amount']:
			try:
				stock = rounded(stock[0]['amount'] * -1, 2)
			except:
				frappe.throw(str(stock))
		else:
			stock = 0

		wh_account = frappe.db.get_value("Account", {"account_type": "Stock", "warehouse": a.warehouse}, "name")

		gl = frappe.db.sql("select credit from `tabGL Entry` where account = %s and voucher_no = %s", (wh_account, a.name), as_dict=1)
		if gl:
			gl = gl[0]['credit']
		else:
			gl = 0

		diff = flt(stock) - flt(gl)	
	
		if diff > 0.5 or diff < -0.5:
			print(str(a.name) + "  : " + str(stock) + " ==> " + str(gl))
			#frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
			#doc = frappe.get_doc("Issue POL", a.name)
			#doc.update_stock_gl_ledger(1, 0)

def adjust_it():
	name = "IPOL180500322"
	frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", name)
	doc = frappe.get_doc("Issue POL", name)
	doc.update_stock_gl_ledger(1, 0)

def get_stats():
        filename = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = '/home/kinley/erp/logs/stats/top'+filename+'.log'
        values  = []
        
        with open(filename, "w") as outfile:
                subprocess.call("top -b -n1", shell=True, stdout=outfile)

        with open(filename) as infile:
                counter = 0
                start   = 999
                
                for line in infile:
                        counter += 1
                        record   = ()
                        if counter > start:
                                record = tuple([
                                        str(filename).strip(),
                                        line[:5].strip(),
                                        line[5:14].strip(),
                                        line[14:18].strip(),
                                        line[18:22].strip(),
                                        line[22:30].strip(),
                                        line[30:37].strip(),
                                        line[37:44].strip(),
                                        line[44:46].strip(),
                                        line[46:52].strip(),
                                        line[52:57].strip(),
                                        line[57:67].strip(),
                                        line[67:len(line)].strip(),
                                        str(frappe.session.user).strip(),
                                        str(now_datetime()).strip()
                                ])
                                values.append(str(record))
                        else:
                                if line[:5].strip() == "PID":
                                        start = counter
        if len(values) > 0:
                qry = """
                        insert into maintenance.stats(filename,pid,user,pr,ni,virt,res,shr,s,
                                cpu,mem,time,command,owner,creation)
                        values {0}
                """

                try:
                        sql = qry.format(",".join(values))
                        frappe.db.sql(sql)
                except Exception, e:
                        frappe.throw(_("{0}").format(str(e)))
        print filename

def adjust_pr_entry():
	for a in frappe.db.sql("select name from `tabPurchase Receipt` where name in ('PRCO18110243', 'PRCO18070032')", as_dict=1):
		print(str(a.name))
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
		doc = frappe.get_doc("Purchase Receipt", a.name)
		doc.make_gl_entries()

	"""for a in frappe.db.sql("select distinct parent from `tabPurchase Receipt Item` where parent in ('PRCO18050290', 'PRCO18110238')", as_dict=1):
		print(str(a.parent))
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.parent)
		doc = frappe.get_doc("Purchase Receipt", a.parent)
		doc.make_gl_entries()"""

def adjust_se_entry():
	for a in frappe.db.sql("select distinct parent from `tabStock Entry Detail` where parent in ('PRCO18050290','SEMI18060781','SEMT18060017','PRCO18070032','PRCO18110238','PRCO18110243','SEMI18121376','SEMI18121378','SEMI18121380')", as_dict=1):
		print(str(a.parent))
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.parent)
		doc = frappe.get_doc("Stock Entry", a.parent)
		doc.make_gl_entries()

def update_increments_jan2019():
	err_count = 0
	for i in frappe.db.sql("select * from maintenance.update_increments where ifnull(flag,0) = 0", as_dict=True):
		if not frappe.db.exists("Salary Increment", {'fiscal_year': '2019', 'month': '01', 'employee': i.employee}):
			err_count += 1
			print i.sno, i.employee, i.remarks, i.increment_amount, i.flag

	if err_count:
		print 'ERROR: Unable to update increments due to above listed employees not having increments.'
		return False

	# Updating increments
	for i in frappe.db.sql("select * from maintenance.update_increments where ifnull(flag,0) = 0", as_dict=True):
		doc = frappe.get_doc("Salary Increment", {'fiscal_year': '2019', 'month': '01', 'employee': i.employee, 'docstatus': 0})
		print doc.name
		if i.remarks == "NO_INCREMENT":
			try:
				doc.remarks = 'No increment as per the excel sheet provided in ticket#1265'
				doc.increment = 0
				doc.new_basic = flt(doc.old_basic)
				doc.save()
				frappe.db.sql("update maintenance.update_increments set flag=1 where employee='{0}'".format(i.employee))
				print i.employee,'NO_INCREMENT'
			except Exception, e:
				print i
				frappe.throw(_("ERROR: While updating for NO_INCREMENT. {0}").format(e))
		elif i.remarks == "PRORATED":
			try:
				doc.remarks = 'Prorated as per the excel sheet provided in ticket#1265'
				doc.increment = flt(i.increment_amount)
				doc.new_basic = flt(doc.old_basic)+flt(i.increment_amount)
				doc.save()
				frappe.db.sql("update maintenance.update_increments set flag=1 where employee='{0}'".format(i.employee))
				print i.employee,'PRORATED'
			except Exception, e:
				print i
				frappe.throw(_("ERROR: While updating for PRORATED. {0}").format(e))
		else:
			print i
			frappe.throw(_("No matching record found for the excel sheet records provided"))

def update_consumed_budget_direct_payment():
        ml = frappe.db.sql("select p.name as name, p.posting_date as posting_date, p.cost_center as cost_center, p.debit_account as budget_account, p.amount as amount  from `tabDirect Payment` p where p.payment_type='payment' and journal_entry == "" p.name not in (select po_no from `tabConsumed Budget`)", as_dict=1)
        for a in ml:
                dc = frappe.new_doc("Committed Budget")
                dc.account = a.budget_account
                dc.cost_center = a.cost_center
                dc.po_no = a.name
                dc.po_date = a.posting_date
                dc.amount = a.amount
                dc.poi_name = a.name
                dc.date = a.posting_date
                dc.flags.ignore_permissions=1
                dc.submit()

                cb = frappe.new_doc("Consumed Budget")
                cb.account = a.budget_account
                cb.cost_center = a.cost_center
                cb.po_no = a.name
                cb.po_date = a.posting_date
                cb.amount = a.amount
                cb.pii_name = a.name,
                cb.com_ref = dc.name,
                cb.date = a.posting_date
                cb.flags.ignore_permissions=1
                cb.submit()
			
def update_consumed_budget():
        ml = frappe.db.sql("select p.name as name, p.posting_date as posting_date, p.cost_center as cost_center, i.budget_account as budget_account, i.amount as amount  from `tabImprest Recoup` p, `tabImprest Recoup Item` i where p.name = i.parent and p.docstatus = 1 and p.name not in (select po_no from `tabConsumed Budget`)", as_dict=1)
        for a in ml:
                dc = frappe.new_doc("Committed Budget")
                dc.account = a.budget_account
                dc.cost_center = a.cost_center
                dc.po_no = a.name
                dc.po_date = a.posting_date
                dc.amount = a.amount
                dc.poi_name = a.name
                dc.date = a.posting_date
                dc.flags.ignore_permissions=1
                dc.submit()

                cb = frappe.new_doc("Consumed Budget")
                cb.account = a.budget_account
                cb.cost_center = a.cost_center
                cb.po_no = a.name
                cb.po_date = a.posting_date
                cb.amount = a.amount
                cb.pii_name = a.name,
                cb.com_ref = dc.name,
                cb.date = a.posting_date
                cb.flags.ignore_permissions=1
                cb.submit()


def test():
	print("IN TEST")

def update_dp_gl():
        for a in frappe.db.sql("select name, posting_date from `tabDirect Payment` where docstatus = 1", as_dict=1):
                for b in frappe.db.sql("select name, posting_date from `tabGL Entry` where voucher_no = %s", a.name, as_dict=1):
                        if b.posting_date != a.posting_date:
                                print(str(a.name) + " : " + str(a.posting_date) + " to " + str(b.posting_date))
				frappe.db.sql("update `tabGL Entry` set posting_date = %s where name = %s", (a.posting_date, b.name))

def adjust_asset_sale():
	for a in frappe.db.sql("select name, branch from `tabSales Invoice` where naming_series = 'Fixed Asset' and docstatus = 1 and posting_date > '2018-01-01'", as_dict=1):
		gl = None
		gls = frappe.db.sql("select name from `tabGL Entry` where voucher_no = %s and account = 'Gain or Loss on Sale of Asset - CDCL'", a.name, as_dict=1)
		if gls:
			gl = gls[0].name
		if gl:
			cc = get_branch_cc(a.branch)
			print(str(a.name) + " : " + str(gl) + " ==> " + str(cc))
			frappe.db.sql("update `tabGL Entry` set cost_center = %s where name = %s", (cc, gl))

def adjust_budget_po():
        for a in frappe.db.sql("select name, status from `tabPurchase Order` where status = 'Closed' and transaction_date > '2017-12-31' and docstatus = 1", as_dict=1):
                print(str(a.name) + " ==> " + str(a.status))
                doc = frappe.get_doc("Purchase Order", a.name)
                doc.adjust_commit_budget(a.status)

def cancel_bdr():
	#for a in frappe.db.sql("select name from `tabBreak Down Report` b where b.docstatus = 1 and b.date < '2018-12-01' and not exists (select 1 from `tabJob Card` j where j.break_down_report = b.name);", as_dict=1):
	for a in frappe.db.sql("select name from `tabBreak Down Report` b where b.docstatus = 1 and b.date < '2018-12-01' and not exists (select 1 from `tabJob Card` j where j.break_down_report = b.name and j.docstatus in (0, 1));", as_dict=1):
		print(str(a.name))
		doc = frappe.get_doc("Break Down Report", a.name)
		doc.cancel()

"""def restore_jc():
	for a in frappe.db.sql("select a.name, b.stock_entry from `tabJob Card` a, `tabJob Card Item` b where a.name = b.parent and a.docstatus = 1 and b.stock_entry is not null group by b.stock_entry", as_dict=1):
		print(str(a.name) + " ==> " + str(a.stock_entry))
		frappe.db.sql("update `tabStock Entry` set job_card = %s where name = %s", (a.name, a.stock_entry))

def repost_stock_gl():
	sr = frappe.db.sql("select a.name from `tabStock Reconciliation` a, `tabStock Reconciliation Item` b where a.name = b.parent and b.item_code = '100452' and a.docstatus = 1", as_dict=1)
	for a in sr:
		print(a.name)
		self = frappe.get_doc("Stock Reconciliation", a.name)
		posting_date = str(get_datetime(str(self.posting_date) + ' ' + str(self.posting_time)))
                for b in self.items:
                        self.repost_issue_pol(b, posting_date)
		frappe.db.commit()

def check_pol_gl():
	for a in frappe.db.sql("select p.name from tabPOL p, `tabJournal Entry` b where p.jv = b.name and p.docstatus = 1 and b.docstatus = 2 and p.posting_date > '2017-12-31'", as_dict=1):
		print(str(a.name))

def link_pol_je():
	docs = frappe.db.sql("select je.reference_name, je.parent from `tabJournal Entry Account` je, tabPOL p where p.name = je.reference_name and je.docstatus = 1 and je.reference_name is not null", as_dict=1)
	for d in docs:
		frappe.db.sql("update tabPOL set jv = %s where name = %s", (d.parent, d.reference_name))
		print(str(d.reference_name) + " ==> " + str(d.parent))
"""


def update_sst_payment_methods():
        counter = 0
        for i in frappe.db.sql("select * from `tabSalary Component` where field_value is not null", as_dict=True):
                counter += 1
                print counter, i.name
                frappe.db.sql("""
                        update `tabSalary Structure`
                        set {0} = '{1}'
                """.format(i.field_method, i.payment_method))

        frappe.db.sql("update `tabSalary Structure` set temporary_transfer_allowance_method = 'Percent' where ifnull(temporary_transfer_allowance,0) > 0 and ifnull(lumpsum_temp_transfer_amount,0) = 0")
        frappe.db.sql("update `tabSalary Structure` set temporary_transfer_allowance_method = 'Lumpsum' where ifnull(temporary_transfer_allowance,0) = 0 and ifnull(lumpsum_temp_transfer_amount,0) > 0;");
        print 'Done updating.....'

