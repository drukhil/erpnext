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
from erpnext.assets.doctype.asset.depreciation import make_depreciation_entry
from frappe.utils import today
import os
import subprocess

def get_wrong_data():
	for a in frappe.db.sql("""
						select credit, party, party_type,  against_voucher, voucher_no, voucher_type
						from `tabGL Entry` 
						where account="Debtor-others - CDCL"
						and against_voucher!="" and against_voucher is NOT NULL
						and credit > 0
						and voucher_type!="Payment Entry"
					""", as_dict=True):
		for b in frappe.db.sql("""
						select name, party, party_type, debit, voucher_no, voucher_type from `tabGL Entry`
						where voucher_no="{}"
						and account="Debtor-others - CDCL"
					""".format(a.against_voucher), as_dict=True):
			if a.party != b.party:
				print(a.voucher_type, a.voucher_no,  b.voucher_type, b.voucher_no,  a.credit, b.debit, a.party, b.party)
		
def update_against_voucher():
	for a in frappe.db.sql("""
							select h.name, h.invoice_jv, h.payment_jv, i.parent
							from `tabHire Charge Invoice` h, `tabMechanical Payment Item` i
							where h.name=i.reference_name
							and h.invoice_jv!="" and h.invoice_jv is NOT NULL
						""", as_dict=True):
		if frappe.db.exists("Journal Entry", a.invoice_jv):
			for b in frappe.db.sql("""select name, against_voucher, against_voucher_type, 
										debit
										from `tabGL Entry`
										where account="Debtor-others - CDCL"
										and against_voucher='{}'
										and voucher_no="{}"	
									""".format(a.name, a.parent), as_dict=True):
				frappe.db.sql("""update `tabGL Entry` set against_voucher_type='Journal Entry', against_voucher='{}' 
								where name='{}'
							""".format(a.invoice_jv, b.name))
				print(b.name, b.against_voucher, a.invoice_jv)
	frappe.db.commit()


def party_correction():
	i=0
	for a in frappe.db.sql("""
					select name, voucher_no, voucher_type, party, party_type
					from `tabGL Entry`
					where party="State Trading Corporation of Bhutan Limited ( Spare Parts, Tyre & Tube)"
				""", as_dict=True):
		if a.voucher_type=="Payment Entry":
			doc = frappe.get_doc(a.voucher_type, a.voucher_no)
			if doc.party == "State Trading Corporation of Bhutan Limited ( Spare Parts, Tyre & Tube)":
				print("Within PE " + str(doc.name) + " Party : "+ str(doc.party))
				frappe.db.sql("update `tabPayment Entry` set party='State Trading Corporation of Bhutan Limited' where name='{}'".format(a.voucher_no))
		elif a.voucher_type == "Journal Entry":
			for b in frappe.db.sql("""select name, party from `tabJournal Entry Account` 
									where parent="{}"  and 
									party = "State Trading Corporation of Bhutan Limited ( Spare Parts, Tyre & Tube)"
								""".format(a.voucher_no), as_dict=True):
					print("Within JE  " + str(b.party) + "Name: " + str(b.name))
					frappe.db.sql("update `tabJournal Entry Account` set party='State Trading Corporation of Bhutan Limited' where name='{}'".format(b.name))
		i+=1
		print(i, a.name, a.voucher_no)
		frappe.db.sql("update `tabGL Entry` set party='State Trading Corporation of Bhutan Limited' where name='{}'".format(a.name))
	#frappe.db.commit()

		

def correction_of_stock_entries():
	import csv
	with open('/home/kinley/erp/apps/stock_update.csv') as f:
		data = csv.reader(f)
		r=0
		bal=82950.00
		for row in data:
			if r > 0:
				name=row[0].decode('utf-8')
				doc = frappe.get_doc("Stock Ledger Entry", name)
				stock_value= flt(doc.valuation_rate * flt(row[1]),2)
				if doc.actual_qty > 0:
					diff_value=flt(doc.actual_qty * doc.incoming_rate,2)
				else:
					diff_value=flt(doc.actual_qty * doc.valuation_rate,2)
				print(doc.name,row[1],doc.valuation_rate,stock_value,diff_value)
				'''
				frappe.db.sql("""update `tabStock Ledger Entry` set stock_value='{}', 
									qty_after_transaction='{}', 
									stock_value_difference='{}'
								where name='{}' """.format(stock_value, row[1], diff_value, doc.name))
				'''
			r+=1
		#frappe.db.commit()

def delete_dep_asset():
	'''
	for a in ("JEDE230801227","JEDE230801226","JEDE230801225","JEDE230801224","JEDE230801223","JEDE230801222","JEDE230801221","JEDE230801220","JEDE230801219","JEDE230801218","JEDE230801217","JEDE230801216","JEDE230801215","JEDE230801214","JEDE230801213","JEDE230801212","JEDE230801211","JEDE230801210","JEDE230801209","JEDE230801208","JEDE230801207","JEDE230801206","JEDE230801205","JEDE230801204","JEDE230801203","JEDE230801202","JEDE230801201"):
		#for a in frappe.db.sql("select reference, reference_name from `tabJournal Entry Account` where parent='{}'".format(a)):
		if frappe.db.exists("Depreciation Schedule", {"journal_entry":a}):
			for b in frappe.db.sql("select name from `tabDepreciation Schedule` where journal_entry='{}'".format(a), as_dict=True):
				frappe.db.sql("update `tabDepreciation Schedule` set journal_entry='' where name='{}'".format(b.name))

		frappe.db.sql("update `tabJournal Entry Account` set reference_type='', reference_name='' where parent='{}'".format(a))
		frappe.db.commit()
		doc = frappe.get_doc("Journal Entry", a)
		doc.cancel()
		print("Cancelled JE ", a)
	'''
	for a in ("ASSET230800007","ASSET230800006","ASSET230800005","ASSET230800004","ASSET230800003","ASSET230800002","ASSET230700013","ASSET230700012","ASSET230700011","ASSET230700010","ASSET230700009","ASSET230700008","ASSET230700007","ASSET230700006","ASSET230700005","ASSET230700004"):
		doc = frappe.get_doc("Asset",a)
		if doc.purchase_date == "2023-08-01":
			print(a)
			frappe.db.sql("delete from `tabDepreciation Schedule` where parent='{}'".format(a))
			frappe.db.commit()
		doc.save()
		frappe.db.sql("update `tabAsset` set docstatus=1 where name ='{}'".format(a))
		frappe.db.commit()

def revert_salary_structure():
	count = 1
	ss = frappe.db.sql("""
		select ss.name, ss.employee, ss.employee_grade, ss.employment_type, ss.employee_group from `tabSalary Structure` ss,
		`tabEmployee` e where e.name = ss.employee
		and e.status = 'Active' and ss.is_active = 'Yes'
    """,as_dict=1)
	if ss:
		for s in ss:
			sal_struct = frappe.get_doc("Salary Structure", s.name)
			if frappe.db.exists("Salary Slip", {"employee": s.employee, "month":'10', "fiscal_year":'2023'}):
				sal_slip = frappe.get_doc("Salary Slip", {"employee": s.employee, "month":'10', "fiscal_year":'2023'})
				if s.employee_group not in ("Temporary", "CPE"):
					basic_pay = 0
					for a in sal_slip.earnings:
						if a.salary_component == "Basic Pay":
							basic_pay = a.amount
					if basic_pay == 0:
						frappe.throw("Basic Pay is 0")
					for e in sal_struct.earnings:
						if e.salary_component == "Basic Pay":
							e.amount = basic_pay
					sal_struct.save(ignore_permissions=1)
					print(str(count)+". "+sal_struct.employee)
					count += 1

def update_salary_structure():
	ss = frappe.db.sql("""
		select ss.name, ss.employee_grade, ss.employment_type, ss.employee_group from `tabSalary Structure` ss,
		`tabEmployee` e where e.name = ss.employee
		and e.status = 'Active' and ss.is_active = 'Yes'
    """,as_dict=1)
	if ss:
		for s in ss:
			sal_struct = frappe.get_doc("Salary Structure", s.name)
			if s.employee_group not in ("Temporary", "CPE"):
				sal_struct.eligible_for_fixed_allowance = 1
				for e in sal_struct.earnings:
					if e.salary_component == "Basic Pay":
						if s.employee_grade in ("M7", "M7 ( Contract )", "O7", "F7", "M6", "M6 (Contract)", "M5", "M4", "M4 Contract", "E3", "E4", "E3 ( Contract )", "E4 ( Contract )", "E2", "CEO"):
							e.amount += e.amount * 0.02
						else:
							e.amount += e.amount * 0.05
						e.amount = math.ceil(e.amount)
						if flt(str(e.amount)[len(str(e.amount))-1]) > 0 and flt(str(e.amount)[len(str(e.amount))-1]) <= 5:
							e.amount = flt(str(e.amount)[0:len(str(e.amount))-1]+"5")
						elif flt(str(e.amount)[len(str(e.amount))-1]) > 5 and flt(str(e.amount)[len(str(e.amount))-1]) <= 9:
							value_to_add = 10 - flt(str(e.amount)[len(str(e.amount))-1])
							e.amount = e.amount + value_to_add
				sal_struct.save(ignore_permissions=1)
				print(sal_struct.employee)

def update_bank_details():
    # for a in frappe.db.sql(""" select t2.name, t2.institution_name, t2.reference_number, t2.bank_account_type, bank_account_no
	# 							from `tabSalary Slip` t1 join `tabSalary Detail` t2
	# 							on t1.name = t2.parent
	# 							where t2.salary_component = "Financial Institution Loan"
	# 							and t1.fiscal_year = '2022' and t1.month='01'
    #                        """, as_dict=True):
	for a in frappe.db.sql(""" select t2.name, t2.institution_name, t2.reference_number, t2.bank_account_type, t2.bank_ac_no
							from `tabSalary Structure` t1 join `tabSalary Detail` t2
							on t1.name = t2.parent
							where t2.salary_component = "Financial Institution Loan"
							and is_active = "Yes"
							""", as_dict=True):
		if a.institution_name == "BOBL":
			acc_type="03"
			bank_name="BOBL"
			bank_ac_no = a.reference_number
		elif a.institution_name == "NPPF":
			acc_type="03"
			bank_name="BOBL"
			bank_ac_no = "101004193"
		else:
			acc_type="04"
			bank_name = a.institution_name
			bank_ac_no = a.reference_number
		frappe.db.sql("update `tabSalary Detail` set bank_name='{}', bank_ac_no='{}', bank_account_type='{}' where name='{}'".format(bank_name, bank_ac_no, acc_type, a.name))
	frappe.db.commit()

def create_dp_from_utility():
	udoc = frappe.get_doc("Utility Bill", "CN202112130042")
	if udoc.direct_payment:
		print("Direct Payment Already created for Utility Bill No.".format(udoc.name))
		return
	doc = frappe.new_doc("Direct Payment")
	doc.branch = udoc.branch
	doc.cost_center = udoc.cost_center
	doc.posting_date = udoc.posting_date
	doc.payment_type = "Payment"
	doc.tds_percent = udoc.tds_percent
	doc.tds_account = udoc.tds_account
	doc.credit_account = udoc.expense_account
	doc.utility_bill = str(udoc.name)
	doc.remarks = "Utility Bill Payment " + str(udoc.name)
	doc.status = "Completed"
	if udoc.item:
		count_child = 0
		for a in udoc.item:
			if a.create_direct_payment:
				if a.invoice_amount > 0 and a.payment_status == "Success":
					doc.append("item", {
							"party_type": "Supplier",
							"party": a.party,
							"account": a.debit_account,
							"amount": a.invoice_amount,
							"invoice_no": a.invoice_no,
							"invoice_date": a.invoice_date,
							"tds_applicable": a.tds_applicable,
							"taxable_amount": a.invoice_amount,
							"tds_amount": a.tds_amount,
							"net_amount": a.net_amount,
							"payment_status": "Payment Successful"
						})
					count_child +=1
		if count_child > 0:
			doc.submit()
	if doc.name:
		frappe.db.sql("Update `tabUtility Bill` set direct_payment = '{}' where name = '{}'".format(doc.name, udoc.name))
		frappe.db.commit()
		print("Direct Payment created and submitted for this Utility Bill {}".format(udoc.name))

# def copy_party_to_consolidation():
#     for d in frappe.db.sql('''
#                            select voucher_no, account, name,consolidation_party
#                            from `tabGL Entry` where voucher_type = 'Sales Invoice' and (consolidation_party is null or consolidation_party ='')
#                            ''',as_dict=True):
#         exp_acc = ''
#         if not d.consolidation_party:
# 			# if d.account == 'Stock received but Not billed - CDCL':
# 			# 	item_code = frappe.db.get_value('Purchase Invoice Item',{'parent':d.voucher_no},['item_code'])
# 			# 	exp_acc = frappe.db.get_value('Item',item_code,['expense_account'])
# 				# print('item code : '+ item_code + ' acc : '+exp_acc)
# 			party = frappe.db.get_value('Sales Invoice',d.voucher_no,['customer'])
# 			print('name : '+ d.name +'party : '+party)
# 			frappe.db.sql('''
# 						update `tabGL Entry` set consolidation_party_type = 'Customer', 
# 						consolidation_party = "{}",
# 						exact_expense_acc = "{}"
# 						where name = "{}"
# 						'''.format(party,exp_acc,d.name))
  
# def update_timesheet_docstatus_for_completed_project():
# 	for a in frappe.db.sql("""
# 		select a.timesheet 
# 		from
# 			(select t.name as timesheet
# 				from `tabProject` p inner join `tabTimesheet` t 
# 				on t.project = p.name where p.status = 'Completed' 
# 				and t.docstatus = 0) a
# 	""",as_dict=1):
# 		frappe.db.sql("""
# 			update `tabTimesheet` set docstatus=1 where name = '{}'
# 		""".format(a.timesheet))

# def boq_update():
#     for d in frappe.db.sql("""
#                            select name, total_amount from `tabBOQ`
#                            """,as_dict=1):
#         frappe.db.sql("""
#                       update `tabBOQ` set latest_amount = {} where name = '{}'
#                       """.format(d.total_amount,d.name))
# def update_dp():
# 	i = 0
# 	for a in frappe.db.sql("select debit_account, credit_account, payment_type, name, invoice_no, invoice_date from `tabDirect Payment`", as_dict=True):
# 		if a.payment_type == "Payment":
# 			account = a.debit_account
# 		else:
# 			account = a.credit_account
# 		if a.name != "DPAY1901011":
# 			frappe.db.sql("update `tabDirect Payment Item` set account = '{}',  invoice_date='{}', docstatus = 1 where parent = '{}'".format(account, a.invoice_date, a.name))
# 			frappe.db.commit()
# 		i += 1
# 		print(str(a.name) + " and Count : " + str(i))

# def remove_gl_party():
# 	i  = 1
# 	for a in frappe.db.sql("""select g.name, g.party, g.party_type, g.account, a.account_type
# 						from `tabGL Entry` g, `tabAccount` a 
# 						where g.account = a.name and 
# 						a.account_type NOT IN ('Receivable', 'Payable')
# 						and length(g.party) > 0
# 						""", as_dict=True):
# 		#frappe.db.sql("update `tabGL Entry` set party = '', party_type = '' where name = '{}'".format(a.name))
# 		#frappe.db.commit()
# 		print("Done" + str(i) + " | " +str(a.name) +" | " + str(a.account) + " | " + str(a.party) + "|"+ str(a.account_type))
# 		i+=1

# def asset_depreciate():
# 	# make_depreciation_entry("ASSET171101184", today())
# 	for d in frappe.db.sql("""
# 		select DISTINCT(journal_entry) from `tabDepreciation Schedule`
# 	""",as_dict=True):
# 		je = frappe.get_value("Journal Entry",{"name":d.journal_entry},"name")
# 		if not je and d.journal_entry:
# 			print(d.journal_entry,' ',je)

# def update_design():
# 	for a in frappe.db.sql("select  employee, designation, employee_subgroup from `tabEmployee` where employee = 'CDCL9401003'", as_dict=True):
# 		for b in frappe.db.sql("select name, employee, designation, grade from `tabTravel Claim` where name = 'CDCL9401003'", as_dict = True):
# 			if a.designation != b.designation:
# 				print("TC Desig: " + b.designation + "EM Design :" + a.designation)

# def update_ta_tc():
# 	for a in frappe.db.sql("select name, employee, employee_name, ta from `tabTravel Claim` where name in ('TC180400029','TC180600209','TC181000204','TC181000205','TC190300191','TC190400026','TC190400095','TC190500013','TC190500098','TC190500160','TC190600017','TC190600096','TC190700098','TC190700181','TC190800137','TC190900013','TC190900014','TC190900109')", as_dict=True):
# 		for b in frappe.db.sql("select name from `tabTravel Authorization` where name = '{}'".format(a.ta), as_dict=True):
# 			frappe.db.sql("update `tabTravel Authorization` set employee ='CDCL0403002' where name = '{}'".format(b.name))
# 			frappe.db.sql("update `tabTravel Claim` set employee = 'CDCL0403002' where name = '{}'".format(a.name))
# 			print(str(a.name) + " and " + str(b.name))
		

# def update_le():
# 	count = 0
# 	for a in frappe.db.sql("""
# 			select name, employee, from_date from `tabLeave Allocation` where 
# 			cl_balance + carry_forwarded_leaves + new_leaves_allocated != total_leaves_allocated - encashed_days and docstatus = 1 and leave_type = 'Earned Leave' and from_date >= '2020-01-01'
# 		""", as_dict = 1):
		
# 		frappe.db.sql("""
# 			update `tabLeave Allocation` set total_leaves_allocated = new_leaves_allocated + carry_forwarded_leaves + encashed_days + cl_balance where name = '{0}'""".format(a.name))
		
# 		for b in frappe.db.sql(""" select name from `tabLeave Allocation` where employee = '{0}' and from_date > '{1}' order by from_date asc""".format(a.employee, a.from_date), as_dict =1): 
# 			d = frappe.get_doc('Leave Allocation', b.name)
# 			d.save()
# 			d.submit()
# 			count += 1
# 			print b.name, count

# def submit_ta():
# 	doc = frappe.get_doc("Travel Authorization", "TA210400049")
# 	doc.submit()
# 	print doc.advance_amount

# def depreciate_assets():
#         count = 0
#         for a in frappe.db.sql("""
#                 select a.name, a.value_after_depreciation-1 as value_after_depreciation,  
#                 (select b.accumulated_depreciation_amount from `tabDepreciation Schedule` b where b.parent = a.name 
#         and b.journal_entry is not null order by b.idx desc limit 1) as accumulated_depreciation_amount from `tabAsset` a
#         where a.asset_sub_category = 'Semi Permanent Structure' and a.docstatus =1 and 
#         a.name = 'ASSET171100066'""", as_dict = 1):
#                 'ASSET190600028-1'
#                 '''doc = frappe.get_doc("Asset", a.name)
#                 amt = 42285.76 + a.accumulated_depreciation_amount
#                 row = doc.append ("schedules",{})
#                 row.schedule_date = today()
#                 row.depreciation_amount  = flt(42285.75)
#                 row.depreciation_income_tax = flt(42285.75)
#                 row.accumulated_depreciation_amount = amt
#                 row.accumulated_depreciation_income_tax = amt
#                 row.save()
#                 row.submit()
#                 make_depreciation_entry(a.name, today())
#                 count += 1'''
#                 print a.name, count

# def update_travel():
# 	import csv
# 	with open('/home/kinley/erp/travel.csv') as f:
# 		data = csv.reader(f)
# 		for row in data:
# 			print("Employee ID :" + str(row[0]) + " Travel Claim : " + str(row[2]))
# 			ta = frappe.db.get_value("Travel Claim", row[2], "ta")
			

# def update_asset_depreciation():
# 	import csv
# 	with open('/home/kinley/erp/asset_for_depreciation.csv','r')as f:
# 		data = csv.reader(f)
# 		for row in data:
# 			for a in frappe.db.sql("""select name, schedule_date, parent
#                       		from `tabDepreciation Schedule`
#                       		where schedule_date > now()
#                       		and parent = '{}'""".format(row[0]), as_dict=True):
            
#             			frappe.db.sql("update `tabDepreciation Schedule` set schedule_date=now() where name ='{0}'".format(a.name))
#             			print("Changed schedule date for asset : " + row[0] + " Schedule Date: " + str(a.schedule_date))
			
# def update_mr():
# 	doc = frappe.get_doc("Process MR Payment", 'MRP200200016')
# 	print doc.name
# 	doc.save(ignore_permissions = True)



# def check_stock_gl():
# 	for a in frappe.db.sql("select name, branch from `tabStock Entry` where docstatus = 1 and name = 'SEMI19030600'", as_dict=1):
# 		try:
# 			cc = get_branch_cc(a.branch)
# 			sed = frappe.db.sql("select name from `tabStock Entry Detail` where parent = %s and cost_center != %s", (a.name, cc))
# 			if sed:
# 				print(a.name)
# 				frappe.db.sql("update `tabStock Entry Detail` set cost_center = %s where parent = %s", (cc, a.name))
# 				frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
# 				doc = frappe.get_doc("Stock Entry", a.name)
# 				doc.make_gl_entries()
# 		except:
# 			cc = "Dummy"

# def update_gl_stock_2019():
# 	for a in frappe.db.sql("select name from `tabStock Entry` where name = 'SEMT18120032'", as_dict=1):
# 		print(str(a.name))
# 		self = frappe.get_doc("Stock Entry", a.name)
# 		self.make_gl_entries()

# def test_get_branch():
# 	for a in frappe.db.sql("select name from `tabStock Entry` where docstatus = 1 and purpose = 'Material Transfer' and posting_date between '2019-01-01' and '2019-12-31' and name = 'SEMT19010037'", as_dict=1):
# 		print(a.name)
# 		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
# 		doc = frappe.get_doc("Stock Entry", a.name)
# 		doc.make_gl_entries()

# def update_wh_branch():
#         counter =0
#         for t in frappe.get_all("Warehouse", ["name", "branch"]):
#                 if not frappe.db.exists("Warehouse Branch", {"parent" :t.name }):
#                         counter +=1
#                         print counter, t.name
#                         doc = frappe.get_doc("Warehouse", t.name)
#                         row = doc.append ("items",{})
#                         row.branch  = t.branch
#                         row.save()
#                         print t
#         print 'dona saving .........'


# def asset_test():
# 	for a in frappe.db.sql("select name, asset_category, opening_accumulated_depreciation as oad from tabAsset where asset_category = 'Machinery & Equipment(10 Years)' and docstatus = 1 and status not in ('Scrapped', 'Sold')", as_dict=1):
# 		accu_ar = frappe.db.sql("""select
#                 	gl.accumulated_depreciation_amount as ac
#                         from `tabDepreciation Schedule` gl, tabAsset ass
#                         where gl.parent = ass.name
#                         and gl.schedule_date <= '2018-12-31'
#                         and gl.docstatus = 1
# 			and ass.name = '{0}'
#                         and gl.journal_entry is not null 
# 			order by gl.schedule_date desc limit 1""".format(a.name), as_dict=1)
# 		opening = a.oad
# 		if accu_ar:
# 			opening = accu_ar[0].ac
		
# 		gl_acc = frappe.db.sql("select name, sum(credit) as cr, sum(debit) as dr from `tabGL Entry` where account like '%Depreciation -Machinery & Equipment(10 Years) - CDCL' and voucher_type not in ('Asset Movement', 'Bulk Asset Transfer') and posting_date < '2019-01-01' and against_voucher = '{0}'".format(a.name), as_dict=1)
# 		gl_open = 1 
# 		if gl_acc:
# 			gl_open = gl_acc[0].cr
	
# 		if not gl_open:	
# 			gl_open = 1
# 		if flt(opening) - flt(gl_open) > 1 or flt(opening) - flt(gl_open) < -1:
# 			print str(a.name) + " ==> " + str(opening) + " : " + str(gl_open)

# def change_pol_cc():
# 	for a in frappe.db.sql("select distinct  voucher_no from `tabGL Entry` where account = 'Clearing Account - CDCL' and posting_date > '2018-12-31';", as_dict=1):
# 		pol = frappe.get_doc("POL", a.voucher_no)
# 		print(pol.equipment_warehouse)
# 		frappe.db.sql("update `tabGL Entry` set account = %s where voucher_no = %s", (pol.equipment_warehouse, a.voucher_no))

# def update_musterroll():
# 	MR = frappe.db.sql("select rate_per_day, rate_per_hour, joining_date, name from `tabMuster Roll Employee`;", as_dict=1)
# 	counter = 0
#         for i in MR:
#                 counter += 1
                
#                 doc = frappe.get_doc("Muster Roll Employee", i.name)
#                 row = doc.append("musterroll", {})
#                 row.rate_per_day    = i.rate_per_day
#                 row.rate_per_hour           = i.rate_per_hour
#                 row.from_date             = i.joining_date
#                 row.save()
# def change_dn():
# 	for a in frappe.db.sql("select name, branch from `tabDelivery Note` where docstatus = 1 and posting_date > '2018-12-31'", as_dict=1):
# 		cc = get_branch_cc(a.branch)
# 		print(cc)
# 		frappe.db.sql("update `tabDelivery Note Item` set cost_center = %s where parent = %s", (cc, a.name))
# 		frappe.db.sql("update `tabGL Entry` set cost_center = %s where voucher_no = %s", (cc, a.name))

# def change_si():
# 	for a in frappe.db.sql("select name, branch from `tabSales Invoice` where docstatus = 0 and posting_date > '2018-12-31'", as_dict=1):
# 		cc = get_branch_cc(a.branch)
# 		print(cc)
# 		frappe.db.sql("update `tabSales Invoice Item` set cost_center = %s where parent = %s", (cc, a.name))
# 		frappe.db.sql("update `tabGL Entry` set cost_center = %s where voucher_no = %s", (cc, a.name))

# def change_cc():
# 	for a in frappe.db.sql("select name, branch from `tabStock Entry` where docstatus = 0 and posting_date > '2018-12-31'", as_dict=1):
# 		cc = get_branch_cc(a.branch)
# 		print(cc)
# 		frappe.db.sql("update `tabStock Entry Detail` set cost_center = %s where parent = %s", (cc, a.name))
# 		frappe.db.sql("update `tabGL Entry` set cost_center = %s where voucher_no = %s", (cc, a.name))
# 		"""for b in frappe.db.sql("select cost_center from `tabGL Entry` where voucher_no = %s and cost_center != %s", (a.name, cc), as_dict=1)
# 			print()
# 		"""
# def update_bank():
# 	for a in frappe.db.sql("select id_card, bank, account_no, designation from `tabMuster Roll Employee", as_dict=1):
# 		bank1 =a.bank
# 		account = a.account_no
# 		designation1= a.designation
# 		frappe.db.sql("update `tabMR Payment Item` set bank = %s, account_no = %s, designation = %s where id_card = %s", (bank1, account, designation1, a.id_card))

# def get_cc():
# 	print(frappe.defaults.get_defaults().cost_center)

# def get_diff_asset():
#         for a in frappe.db.sql("select name, asset_category, asset_account from tabAsset where docstatus = 1", as_dict=1):
#                 as_acc = frappe.db.get_value("Asset Category Account", {"parent": a.asset_category}, "fixed_asset_account")
#                 if as_acc != a.asset_account:
#                         print(str(a.name) + "   :  " + str(as_acc) + "  ==> " + str(a.asset_account))


# def update_equipment():
#         els = frappe.db.sql("select name from tabEquipment", as_dict=1)
#         for a in els:
#                 print a.name
#                 doc = frappe.get_doc("Equipment", a.name)
#                 doc.save()
#                 frappe.db.commit()

# def check_ds():
# 	#for a in frappe.db.sql("select b.name as ass_name, a.schedule_date as dep_date, a.name, b.residual_value, b.expected_value_after_useful_life as ev, b.gross_purchase_amount as gross, b.value_after_depreciation as vad, a.accumulated_depreciation_amount as ada, a.depreciation_amount as da from `tabDepreciation Schedule` a, tabAsset b where a.parent = b.name and b.docstatus = 1 and a.journal_entry is null and b.status in ('Partially Depreciated', 'Submitted') and residual_value > 0 order by b.name, a.schedule_date", as_dict=1):
# 	for a in frappe.db.sql("select b.name as ass_name, a.schedule_date as dep_date, a.name, b.residual_value, b.expected_value_after_useful_life as ev, b.gross_purchase_amount as gross, b.value_after_depreciation as vad, a.accumulated_depreciation_amount as ada, a.depreciation_amount as da from `tabDepreciation Schedule` a, tabAsset b where a.parent = b.name and b.docstatus = 1 and a.journal_entry is null and b.status in ('Partially Depreciated', 'Submitted') and residual_value > 0 and a.accumulated_depreciation_amount > (b.gross_purchase_amount - b.residual_value - b.expected_value_after_useful_life) order by b.name, a.schedule_date", as_dict=1):
# 		new_accu = rounded(flt(a.gross) - flt(a.residual_value) - flt(a.ev), 2)
# 		new_dep = rounded(flt(a.ada) - new_accu, 2)
# 		print(str(a.ass_name) + " ==> " + str(a.dep_date) + " : " + str(new_dep))
# 		frappe.db.sql("update `tabDepreciation Schedule` set depreciation_amount = %s, accumulated_depreciation_amount = %s where name = %s", (new_dep, new_accu, a.name))

# def delete_ds():
# 	for a in frappe.db.sql("select a.name as dname from `tabDepreciation Schedule` a, tabAsset b where a.parent = b.name and b.docstatus = 1 and a.journal_entry is null and b.value_after_depreciation = b.expected_value_after_useful_life;", as_dict=1):
# 		frappe.db.sql("delete from `tabDepreciation Schedule` where name = %s", a.dname)

# def import_asset():
# 	lines = [line.rstrip('\n') for line in open('/home/kinley/erp/asset_file.csv')]
# 	for line in lines:
# 		a = line.split(",")
# 		print(a[0])
# 		frappe.db.sql("update tabAsset set residual_value = %s, value_after_depreciation = %s where name = %s", (a[1], 1, a[0]))

# def adjust_residual():
# 	for a in frappe.db.sql("select name, value_after_depreciation as vad, residual_value as rv, expected_value_after_useful_life as ev from tabAsset where value_after_depreciation < 0 and docstatus = 1", as_dict=1):
# 		val = str(rounded(flt(a.rv) + flt(a.vad) - flt(a.ev), 2))
# 		frappe.db.sql("update tabAsset set residual_value = %s and value_after_depreciation = %s where name = %s", (val, a.ev, a.name))
# 		print(str(a.name) + "  :  " + str(rounded(flt(a.rv) + flt(a.vad) - flt(a.ev), 2)))

# def pass_open_accu():
# 	for a in frappe.db.sql("select name, creation from tabAsset where opening_accumulated_depreciation > 0 and purchase_date >= '2018-01-01' and docstatus = 1 order by creation", as_dict=1):
# 		print(a.name)
# 		doc = frappe.get_doc("Asset", a.name)
# 		doc.make_opening_accumulated_gl_entry()

# def adjust_direct_con():
# 	for a in frappe.db.sql("select name from tabPOL where direct_consumption = 1 and docstatus = 1 and posting_date > '2018-03-31'", as_dict=1):
# 		print(a.name)
# 		self = frappe.get_doc("POL", a.name)

# 		if self.hiring_warehouse:
# 			wh = self.hiring_warehouse
# 		else:
# 			wh = self.equipment_warehouse
# 		wh_account = frappe.db.get_value("Account", {"account_type": "Stock", "warehouse": wh}, "name")
# 		if not wh_account:
# 			frappe.throw(str(wh) + " is not linked to any account.")
# 		cl_account = "Clearing Account - CDCL"

# 		map_rate = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": a.name, "actual_qty": ["<", 0]}, "valuation_rate")
# 		map_amount = flt(map_rate) * flt(self.qty)

# 		if self.hiring_cost_center:
# 			cc = self.hiring_cost_center
# 		else:
# 			cc = get_branch_cc(self.equipment_branch)

# 		gl_entries = []

#                 gl_entries.append(
#                         prepare_gl(self, {"account": wh_account,
#                                          "debit": flt(self.total_amount),
#                                          "debit_in_account_currency": flt(self.total_amount),
#                                          "cost_center": cc,
#                                         })
#                         )

#                 gl_entries.append(
#                         prepare_gl(self, {"account": cl_account,
#                                          "credit": flt(self.total_amount),
#                                          "credit_in_account_currency": flt(self.total_amount),
#                                          "cost_center": cc,
#                                         })
#                         )

#                 gl_entries.append(
#                         prepare_gl(self, {"account": cl_account,
#                                          "debit": flt(map_amount),
#                                          "debit_in_account_currency": flt(map_amount),
#                                          "cost_center": cc,
#                                         })
#                         )

#                 gl_entries.append(
#                         prepare_gl(self, {"account": wh_account,
#                                          "credit": flt(map_amount),
#                                          "credit_in_account_currency": flt(map_amount),
#                                          "cost_center": cc,
#                                         })
#                         )
		
#                 from erpnext.accounts.general_ledger import make_gl_entries
# 		make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=False)

# def adjust_sr():
# 	#for a in frappe.db.sql("select name from `tabStock Reconciliation` a where docstatus = 1 and posting_date between '2018-01-01' and '2018-12-31' and not exists (select 1 from `tabGL Entry` where voucher_no = a.name)", as_dict=1):
# 	print("Starting")
# 	frappe.db.sql("delete from `tabGL Entry` where voucher_no = 'SR/000053'")
# 	doc = frappe.get_doc("Stock Reconciliation", 'SR/000053')
# 	doc.make_gl_entries()
# 	print("DONE")

# def check_it():
# 	for a in frappe.db.sql("select a.name, b.warehouse  from `tabDelivery Note` a, `tabDelivery Note Item` b where a.name = b.parent and a.docstatus = 1 and a.posting_date > '2017-12-31'", as_dict=1):
# 		stock = frappe.db.sql("select sum(actual_qty * valuation_rate) as amount from `tabStock Ledger Entry` where voucher_no = %s", a.name, as_dict=1)
# 		if stock[0]['amount']:
# 			try:
# 				stock = rounded(stock[0]['amount'] * -1, 2)
# 			except:
# 				frappe.throw(str(stock))
# 		else:
# 			stock = 0

# 		wh_account = frappe.db.get_value("Account", {"account_type": "Stock", "warehouse": a.warehouse}, "name")

# 		gl = frappe.db.sql("select credit from `tabGL Entry` where account = %s and voucher_no = %s", (wh_account, a.name), as_dict=1)
# 		if gl:
# 			gl = gl[0]['credit']
# 		else:
# 			gl = 0

# 		diff = flt(stock) - flt(gl)	
	
# 		if diff > 0.5 or diff < -0.5:
# 			print(str(a.name) + "  : " + str(stock) + " ==> " + str(gl))
# 			#frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
# 			#doc = frappe.get_doc("Issue POL", a.name)
# 			#doc.update_stock_gl_ledger(1, 0)

# def adjust_it():
# 	name = "IPOL180500322"
# 	frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", name)
# 	doc = frappe.get_doc("Issue POL", name)
# 	doc.update_stock_gl_ledger(1, 0)

# def get_stats():
#         filename = datetime.now().strftime("%Y%m%d%H%M%S")
#         filename = '/home/kinley/erp/logs/stats/top'+filename+'.log'
#         values  = []
        
#         with open(filename, "w") as outfile:
#                 subprocess.call("top -b -n1", shell=True, stdout=outfile)

#         with open(filename) as infile:
#                 counter = 0
#                 start   = 999
                
#                 for line in infile:
#                         counter += 1
#                         record   = ()
#                         if counter > start:
#                                 record = tuple([
#                                         str(filename).strip(),
#                                         line[:5].strip(),
#                                         line[5:14].strip(),
#                                         line[14:18].strip(),
#                                         line[18:22].strip(),
#                                         line[22:30].strip(),
#                                         line[30:37].strip(),
#                                         line[37:44].strip(),
#                                         line[44:46].strip(),
#                                         line[46:52].strip(),
#                                         line[52:57].strip(),
#                                         line[57:67].strip(),
#                                         line[67:len(line)].strip(),
#                                         str(frappe.session.user).strip(),
#                                         str(now_datetime()).strip()
#                                 ])
#                                 values.append(str(record))
#                         else:
#                                 if line[:5].strip() == "PID":
#                                         start = counter
#         if len(values) > 0:
#                 qry = """
#                         insert into maintenance.stats(filename,pid,user,pr,ni,virt,res,shr,s,
#                                 cpu,mem,time,command,owner,creation)
#                         values {0}
#                 """

#                 try:
#                         sql = qry.format(",".join(values))
#                         frappe.db.sql(sql)
#                 except Exception, e:
#                         frappe.throw(_("{0}").format(str(e)))
#         print filename

# def adjust_pr_entry():
# 	for a in frappe.db.sql("select name from `tabPurchase Receipt` where name in ('PRCO18110243', 'PRCO18070032')", as_dict=1):
# 		print(str(a.name))
# 		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
# 		doc = frappe.get_doc("Purchase Receipt", a.name)
# 		doc.make_gl_entries()

# 	"""for a in frappe.db.sql("select distinct parent from `tabPurchase Receipt Item` where parent in ('PRCO18050290', 'PRCO18110238')", as_dict=1):
# 		print(str(a.parent))
# 		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.parent)
# 		doc = frappe.get_doc("Purchase Receipt", a.parent)
# 		doc.make_gl_entries()"""

# def adjust_se_entry():
# 	for a in frappe.db.sql("select distinct parent from `tabStock Entry Detail` where parent in ('PRCO18050290','SEMI18060781','SEMT18060017','PRCO18070032','PRCO18110238','PRCO18110243','SEMI18121376','SEMI18121378','SEMI18121380')", as_dict=1):
# 		print(str(a.parent))
# 		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.parent)
# 		doc = frappe.get_doc("Stock Entry", a.parent)
# 		doc.make_gl_entries()

# def update_increments_jan2019():
# 	err_count = 0
# 	for i in frappe.db.sql("select * from maintenance.update_increments where ifnull(flag,0) = 0", as_dict=True):
# 		if not frappe.db.exists("Salary Increment", {'fiscal_year': '2019', 'month': '01', 'employee': i.employee}):
# 			err_count += 1
# 			print i.sno, i.employee, i.remarks, i.increment_amount, i.flag

# 	if err_count:
# 		print 'ERROR: Unable to update increments due to above listed employees not having increments.'
# 		return False

# 	# Updating increments
# 	for i in frappe.db.sql("select * from maintenance.update_increments where ifnull(flag,0) = 0", as_dict=True):
# 		doc = frappe.get_doc("Salary Increment", {'fiscal_year': '2019', 'month': '01', 'employee': i.employee, 'docstatus': 0})
# 		print doc.name
# 		if i.remarks == "NO_INCREMENT":
# 			try:
# 				doc.remarks = 'No increment as per the excel sheet provided in ticket#1265'
# 				doc.increment = 0
# 				doc.new_basic = flt(doc.old_basic)
# 				doc.save()
# 				frappe.db.sql("update maintenance.update_increments set flag=1 where employee='{0}'".format(i.employee))
# 				print i.employee,'NO_INCREMENT'
# 			except Exception, e:
# 				print i
# 				frappe.throw(_("ERROR: While updating for NO_INCREMENT. {0}").format(e))
# 		elif i.remarks == "PRORATED":
# 			try:
# 				doc.remarks = 'Prorated as per the excel sheet provided in ticket#1265'
# 				doc.increment = flt(i.increment_amount)
# 				doc.new_basic = flt(doc.old_basic)+flt(i.increment_amount)
# 				doc.save()
# 				frappe.db.sql("update maintenance.update_increments set flag=1 where employee='{0}'".format(i.employee))
# 				print i.employee,'PRORATED'
# 			except Exception, e:
# 				print i
# 				frappe.throw(_("ERROR: While updating for PRORATED. {0}").format(e))
# 		else:
# 			print i
# 			frappe.throw(_("No matching record found for the excel sheet records provided"))

# def update_consumed_budget_direct_payment():
#         ml = frappe.db.sql("select p.name as name, p.posting_date as posting_date, p.cost_center as cost_center, p.debit_account as budget_account, p.amount as amount  from `tabDirect Payment` p where p.payment_type='payment' and journal_entry == "" p.name not in (select po_no from `tabConsumed Budget`)", as_dict=1)
#         for a in ml:
#                 dc = frappe.new_doc("Committed Budget")
#                 dc.account = a.budget_account
#                 dc.cost_center = a.cost_center
#                 dc.po_no = a.name
#                 dc.po_date = a.posting_date
#                 dc.amount = a.amount
#                 dc.poi_name = a.name
#                 dc.date = a.posting_date
#                 dc.flags.ignore_permissions=1
#                 dc.submit()

#                 cb = frappe.new_doc("Consumed Budget")
#                 cb.account = a.budget_account
#                 cb.cost_center = a.cost_center
#                 cb.po_no = a.name
#                 cb.po_date = a.posting_date
#                 cb.amount = a.amount
#                 cb.pii_name = a.name,
#                 cb.com_ref = dc.name,
#                 cb.date = a.posting_date
#                 cb.flags.ignore_permissions=1
#                 cb.submit()
			
# def update_consumed_budget():
#         ml = frappe.db.sql("select p.name as name, p.posting_date as posting_date, p.cost_center as cost_center, i.budget_account as budget_account, i.amount as amount  from `tabImprest Recoup` p, `tabImprest Recoup Item` i where p.name = i.parent and p.docstatus = 1 and p.name not in (select po_no from `tabConsumed Budget`)", as_dict=1)
#         for a in ml:
#                 dc = frappe.new_doc("Committed Budget")
#                 dc.account = a.budget_account
#                 dc.cost_center = a.cost_center
#                 dc.po_no = a.name
#                 dc.po_date = a.posting_date
#                 dc.amount = a.amount
#                 dc.poi_name = a.name
#                 dc.date = a.posting_date
#                 dc.flags.ignore_permissions=1
#                 dc.submit()

#                 cb = frappe.new_doc("Consumed Budget")
#                 cb.account = a.budget_account
#                 cb.cost_center = a.cost_center
#                 cb.po_no = a.name
#                 cb.po_date = a.posting_date
#                 cb.amount = a.amount
#                 cb.pii_name = a.name,
#                 cb.com_ref = dc.name,
#                 cb.date = a.posting_date
#                 cb.flags.ignore_permissions=1
#                 cb.submit()


# def test():
# 	print("IN TEST")

# def update_dp_gl():
#         for a in frappe.db.sql("select name, posting_date from `tabDirect Payment` where docstatus = 1", as_dict=1):
#                 for b in frappe.db.sql("select name, posting_date from `tabGL Entry` where voucher_no = %s", a.name, as_dict=1):
#                         if b.posting_date != a.posting_date:
#                                 print(str(a.name) + " : " + str(a.posting_date) + " to " + str(b.posting_date))
# 				frappe.db.sql("update `tabGL Entry` set posting_date = %s where name = %s", (a.posting_date, b.name))

# def adjust_asset_sale():
# 	for a in frappe.db.sql("select name, branch from `tabSales Invoice` where naming_series = 'Fixed Asset' and docstatus = 1 and posting_date > '2018-01-01'", as_dict=1):
# 		gl = None
# 		gls = frappe.db.sql("select name from `tabGL Entry` where voucher_no = %s and account = 'Gain or Loss on Sale of Asset - CDCL'", a.name, as_dict=1)
# 		if gls:
# 			gl = gls[0].name
# 		if gl:
# 			cc = get_branch_cc(a.branch)
# 			print(str(a.name) + " : " + str(gl) + " ==> " + str(cc))
# 			frappe.db.sql("update `tabGL Entry` set cost_center = %s where name = %s", (cc, gl))

# def adjust_budget_po():
#         for a in frappe.db.sql("select name, status from `tabPurchase Order` where status = 'Closed' and transaction_date > '2017-12-31' and docstatus = 1", as_dict=1):
#                 print(str(a.name) + " ==> " + str(a.status))
#                 doc = frappe.get_doc("Purchase Order", a.name)
#                 doc.adjust_commit_budget(a.status)

# def cancel_bdr():
# 	#for a in frappe.db.sql("select name from `tabBreak Down Report` b where b.docstatus = 1 and b.date < '2018-12-01' and not exists (select 1 from `tabJob Card` j where j.break_down_report = b.name);", as_dict=1):
# 	for a in frappe.db.sql("select name from `tabBreak Down Report` b where b.docstatus = 1 and b.date < '2018-12-01' and not exists (select 1 from `tabJob Card` j where j.break_down_report = b.name and j.docstatus in (0, 1));", as_dict=1):
# 		print(str(a.name))
# 		doc = frappe.get_doc("Break Down Report", a.name)
# 		doc.cancel()

# """def restore_jc():
# 	for a in frappe.db.sql("select a.name, b.stock_entry from `tabJob Card` a, `tabJob Card Item` b where a.name = b.parent and a.docstatus = 1 and b.stock_entry is not null group by b.stock_entry", as_dict=1):
# 		print(str(a.name) + " ==> " + str(a.stock_entry))
# 		frappe.db.sql("update `tabStock Entry` set job_card = %s where name = %s", (a.name, a.stock_entry))

# def repost_stock_gl():
# 	sr = frappe.db.sql("select a.name from `tabStock Reconciliation` a, `tabStock Reconciliation Item` b where a.name = b.parent and b.item_code = '100452' and a.docstatus = 1", as_dict=1)
# 	for a in sr:
# 		print(a.name)
# 		self = frappe.get_doc("Stock Reconciliation", a.name)
# 		posting_date = str(get_datetime(str(self.posting_date) + ' ' + str(self.posting_time)))
#                 for b in self.items:
#                         self.repost_issue_pol(b, posting_date)
# 		frappe.db.commit()

# def check_pol_gl():
# 	for a in frappe.db.sql("select p.name from tabPOL p, `tabJournal Entry` b where p.jv = b.name and p.docstatus = 1 and b.docstatus = 2 and p.posting_date > '2017-12-31'", as_dict=1):
# 		print(str(a.name))

# def link_pol_je():
# 	docs = frappe.db.sql("select je.reference_name, je.parent from `tabJournal Entry Account` je, tabPOL p where p.name = je.reference_name and je.docstatus = 1 and je.reference_name is not null", as_dict=1)
# 	for d in docs:
# 		frappe.db.sql("update tabPOL set jv = %s where name = %s", (d.parent, d.reference_name))
# 		print(str(d.reference_name) + " ==> " + str(d.parent))

# """

# def test():
# 	import csv
#         with open('/home/kinley/erp/asset_list.csv','r') as f:
# 		data = csv.reader(f)
# 		count = 0
# 		for a in data:
# 			ast = frappe.get_doc("Asset", a[0])
# 			dep = frappe.db.sql(""" select sum(depreciation_amount) as amount from `tabDepreciation Schedule` where parent = '{0}' 
# 				and journal_entry is not null  group by parent""".format(a[0]), as_dict = 1)
# 			tot = flt(dep[0].amount) + flt(ast.opening_accumulated_depreciation) + flt(ast.residual_value)
# 			# - flt(ast.expected_value_after_useful_life)
# 			value_after_dep = flt(ast.gross_purchase_amount) - flt(tot)
# 			if flt(value_after_dep) > 1:
# 				'''frappe.db.sql(""" update `tabAsset` set disable_depreciation = 0 where name = '{}'""".format(ast.name))
# 				row = ast.append ("schedules",
#                                         {"depreciation_amount":  value_after_dep - 1,
#                                         "schedule_date": today(),
#                                         "depreciation_income_tax": value_after_dep - 1,
#                                         "accumulated_depreciation_amount": flt(dep[0].amount) + flt(ast.opening_accumulated_depreciation) + flt(value_after_dep) - 1,
#                                         "accumulated_depreciation_income_tax":  flt(dep[0].amount) + flt(ast.opening_accumulated_depreciation) + flt(value_after_dep) - 1,
#                                         })
#                                 row.save()
#                                 row.submit()
#                                	make_depreciation_entry(ast.name, today())'''
# 				count +=1 
# 				print ast.name, ast.status, value_after_dep, count

# def update_ad1():
# 	'''for b in frappe.db.sql(""" select a.name, s.schedule_date, s.parent from `tabAsset` a, `tabDepreciation Schedule` s 
# 			where s.schedule_date < '2020-11-30' and ifnull(s.journal_entry, '') = '' and 
# 			a.status not in ('Scrapped', 'Draft', 'Sold') and s.parent = a.name""", as_dict = 1):
# 		print b.parent, b.schedule_date
# 	'''
# 	for b in frappe.db.sql(""" select schedule_date, parent from `tabDepreciation Schedule` where schedule_date = '2020-09-30' and ifnull(journal_entry, '') = ''""", as_dict = 1):
# 		print b.parent, b.schedule_date
 
# def update_ad():
#         import csv
#         with open('/home/kinley/erp/asset_list.csv','r') as f:
#                 data = csv.reader(f)
#                 count = 0
# 		d = []
#                 for row in data:
#                         ast = frappe.get_doc("Asset", row[0])
# 			if ast.value_after_depreciation > 1:
# 				dep_amount = frappe.db.sql(""" select ifnull(sum(ds.depreciation_amount), 0) as dep from `tabDepreciation Schedule` ds where ds.parent = '{0}' group by ds.parent""".format(ast.name), as_dict = 1)
# 				if dep_amount:
# 					dep_amount = dep_amount[0].dep + ast.opening_accumulated_depreciation
# 				else:
# 					dep_amount = ast.opening_accumulated_depreciation

# 				'''dep_sch = frappe.db.sql(""" update `tabDepreciation Schedule`  set schedule_date = '{0}'
# 					where parent = '{1}' and ifnull(journal_entry, '') = ''""".format(getdate(today()), row[0]))'''	
# 				value_after_dep = flt(ast.gross_purchase_amount) - flt(dep_amount) - flt(ast.residual_value) - 1
# 				if flt(value_after_dep) > 1:
# 					row = ast.append ("schedules",
# 					{"depreciation_amount":  value_after_dep,
# 					"schedule_date": today(),
# 					"depreciation_income_tax": value_after_dep,
# 					"accumulated_depreciation_amount": flt(dep_amount) + flt(value_after_dep),
# 					"accumulated_depreciation_income_tax":  flt(dep_amount) + flt(value_after_dep),
# 					})
# 					row.save()
# 					row.submit()
# 					make_depreciation_entry(ast.name, today())
				
# 				#ast.db_set("value_after_depreciation", value_after_dep)
# 				final_dep = frappe.db.sql(""" select name, schedule_date, parent from `tabDepreciation Schedule` where parent = '{0}' and ifnull(journal_entry, '') = '' order by idx desc limit 1""".format(ast.name), as_dict = 1)

# 				'''if final_dep:
# 					if getdate(final_dep[0].schedule_date) <= getdate(today()):
# 						make_depreciation_entry(final_dep[0].parent, getdate(today()))
				
# 				ast.set_status()'''
# 				count +=1 
# 				print ast.name, count, value_after_dep


# def update_sst_payment_methods():
#         counter = 0
#         for i in frappe.db.sql("select * from `tabSalary Component` where field_value is not null", as_dict=True):
#                 counter += 1
#                 print counter, i.name
#                 frappe.db.sql("""
#                         update `tabSalary Structure`
#                         set {0} = '{1}'
#                 """.format(i.field_method, i.payment_method))

#         frappe.db.sql("update `tabSalary Structure` set temporary_transfer_allowance_method = 'Percent' where ifnull(temporary_transfer_allowance,0) > 0 and ifnull(lumpsum_temp_transfer_amount,0) = 0")
#         frappe.db.sql("update `tabSalary Structure` set temporary_transfer_allowance_method = 'Lumpsum' where ifnull(temporary_transfer_allowance,0) = 0 and ifnull(lumpsum_temp_transfer_amount,0) > 0;");
#         print 'Done updating.....'

def update_user_pwd():
	user_list = frappe.db.sql("select name from `tabUser` where name = 'sonam.zangmo@bt.bt'", as_dict=1)
	c = 1
	non_employee = []
	for i in user_list:
		print("NAME '{}':  '{}'".format(c,str(i.name)))
		if not frappe.db.exists("Employee", {"user_id":i.name}):
			non_employee.append({"User ID":i.name, "User Name":frappe.db.get_value("User",i.name,"full_name")})
		ds = frappe.get_doc("User", i.name)
		ds.new_password = 'erp@2023'
		ds.save(ignore_permissions=1)
		c += 1