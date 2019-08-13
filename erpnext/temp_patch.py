from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import msgprint
from frappe.utils import flt, cint, now
from frappe.utils.data import get_first_day, get_last_day, add_years, date_diff, today, get_first_day, get_last_day
#from erpnext.hr.hr_custom_functions import get_month_details, get_company_pf, get_employee_gis, get_salary_tax, update_salary_structure
from erpnext.hr.hr_custom_functions import get_month_details, get_salary_tax
import collections

# Advance GL not posted
def post_ta_advance():
	#doc = frappe.get_doc("Travel Authorization", "TA190700130-1")
	doc = frappe.get_doc("Travel Authorization", "TA190700135")
	doc.check_advance()

# Following method created by SHIV on 2019/06/27
def generate_pol_gls():
        counter = 0
        for i in frappe.db.sql("select * from `tabPOL` p where p.posting_date >= '2019-01-01' and p.docstatus = 1 and not exists(select 1 from `tabGL Entry` gle where gle.voucher_type = 'POL' and gle.voucher_no = p.name) order by timestamp(p.posting_date, p.posting_time)", as_dict=True):
                counter += 1
                print counter, i.name, i.posting_date, i.posting_time
                doc = frappe.get_doc('POL', i.name)
                doc.make_gl_entries(repost_future_gle=False)

# Following method created by SHIV on 2019/06/27
def generate_issuepol_gls():
        counter = 0
        for i in frappe.db.sql("select * from `tabIssue POL` p where p.posting_date >= '2019-01-01' and p.docstatus = 1 and not exists(select 1 from `tabGL Entry` gle where gle.voucher_type = 'Issue POL' and gle.voucher_no = p.name) order by timestamp(p.posting_date, p.posting_time)", as_dict=True):
                counter += 1
                print counter, i.name, i.posting_date, i.posting_time
                doc = frappe.get_doc('Issue POL', i.name)
                doc.make_gl_entries(repost_future_gle=False)

'''
# update stock reconciliation items with proper balances from stock ledger for missing items
def update_sr_with_sl_missing_items(update="No"):
        from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for
        
        def create_backup_tables():
                # create backup tables
                tables = ["Stock Reconciliation Item"]
                for t in tables:
                        frappe.db.sql("create table if not exists maintenance.`tab{0}_backup` as select t.*, t.modified as backup from `tab{0}` as t where 1=2".format(t))

        def create_backup_data(key,value):
                # take data backup
                frappe.db.sql("insert into maintenance.`tabStock Reconciliation_backup` select t.*, now() from `tabStock Reconciliation` as t where name = '{0}'".format(key))
                for i in value:
                        frappe.db.sql("insert into maintenance.`tabStock Reconciliation Item_backup` select t.*, now() from `tabStock Reconciliation Item` as t where name = '{0}'".format(i.sr_name))

        
        items = frappe.db.sql("""
                select
                        sr.name as voucher_no,
                        sri.name as sr_name,
                        sri.item_code, sri.warehouse,
                        sr.posting_date,
                        sr.posting_time as posting_time_orig,
                        time(sr.posting_time-interval 1 second) as posting_time,
                        sri.current_qty, sri.qty,
                        sri.current_valuation_rate, sri.valuation_rate,
                        ((ifnull(sri.qty,0)*ifnull(sri.valuation_rate,0))-(ifnull(sri.current_qty,0)*ifnull(sri.current_valuation_rate,0))) as sr_amount
                from `tabStock Reconciliation Item` sri, `tabStock Reconciliation` sr
                where sr.name = sri.parent
                and sr.docstatus = 1
                and not exists(select 1
                                from `tabStock Ledger Entry` sle
                                where sle.voucher_no = sri.parent
                                and sle.item_code = sri.item_code)
                and abs(((ifnull(sri.qty,0)*ifnull(sri.valuation_rate,0))-(ifnull(sri.current_qty,0)*ifnull(sri.current_valuation_rate,0)))) > 0 
                order by sr.name, sri.item_code, sri.warehouse
        """, as_dict=True)

        if items:
                create_backup_tables()
                items_dict = frappe._dict()
                for i in items:
                        items_dict.setdefault(i.voucher_no,[]).append(i)

                counter = 0
                for key, value in items_dict.iteritems():
                        #create_backup_data(key, value)
                        diff_amount = 0
                        print key

                        # update current_qty, current_valuation_rate in Stock Reconciliation Item
                        for i in value:
                                counter += 1
                                balance = frappe._dict(get_stock_balance_for(i.item_code, i.warehouse, i.posting_date, i.posting_time))
                                print "\t",counter,i
                                print "\t",counter,balance
                                query = "update `tabStock Reconciliation Item` set current_qty={qty}, current_valuation_rate={rate} where name='{name}'".format(name=i.sr_name,qty=flt(balance.get("qty")), rate=flt(balance.get("rate")))
                                print "\t***",counter,query
                                if update.lower() == "yes":
                                        frappe.db.sql(query)
'''

# update stock reconciliation items with proper balances from stock ledger
def update_sr_with_sl(update="No"):
        from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for
        
        def create_backup_tables():
                # create backup tables
                tables = ["Stock Reconciliation","Stock Reconciliation Item"]
                for t in tables:
                        frappe.db.sql("create table if not exists maintenance.`tab{0}_backup` as select t.*, t.modified as backup from `tab{0}` as t where 1=2".format(t))

        def create_backup_data(key,value):
                # take data backup
                frappe.db.sql("insert into maintenance.`tabStock Reconciliation_backup` select t.*, now() from `tabStock Reconciliation` as t where name = '{0}'".format(key))
                for i in value:
                        frappe.db.sql("insert into maintenance.`tabStock Reconciliation Item_backup` select t.*, now() from `tabStock Reconciliation Item` as t where name = '{0}'".format(i.sr_name))

        
        items = frappe.db.sql("""
                select x.voucher_no, x.item_code, x.warehouse,
                        max(posting_date) as posting_date,
                        max(posting_time) as posting_time,
                        max(x.sr_name) as sr_name,
                        max(x.sl_name) as sl_name,
                        sum(ifnull(x.sr_amount,0)) as sr_amount_tot,
                        sum(ifnull(x.sl_amount,0)) as sl_amount_tot
                from
                (
                select 	
                        sri.parent as voucher_no, 
                        sri.item_code,
                        sri.warehouse,
                        sr.posting_date,
                        time(sr.posting_time-interval 1 second) as posting_time,
                        sri.name as sr_name,
                        "" as sl_name,
                        ((ifnull(sri.qty,0)*ifnull(sri.valuation_rate,0))-(ifnull(sri.current_qty,0)*ifnull(sri.current_valuation_rate,0))) as sr_amount,
                        0 as sl_amount
                from `tabStock Reconciliation Item` sri, `tabStock Reconciliation` sr
                where sr.name = sri.parent
                and sr.name like 'SR%'
                union all
                select 
                        voucher_no as voucher_no,
                        item_code,
                        warehouse,
                        "" posting_date,
                        "" posting_time,
                        "" as sr_name,
                        name as sl_name,
                        0 as sr_amount,
                        stock_value_difference as sl_amount
                from `tabStock Ledger Entry`
                where voucher_no like 'SR%'
                ) as x
                group by x.voucher_no, x.item_code, x.warehouse
                having count(*) = 2 and abs(sr_amount_tot-sl_amount_tot) > 1
        """, as_dict=True)

        if items:
                create_backup_tables()
                items_dict = frappe._dict()
                for i in items:
                        items_dict.setdefault(i.voucher_no,[]).append(i)

                counter = 0
                for key, value in items_dict.iteritems():
                        create_backup_data(key, value)
                        diff_amount = 0
                        print key

                        # update current_qty, current_valuation_rate in Stock Reconciliation Item
                        for i in value:
                                balance = frappe._dict(get_stock_balance_for(i.item_code, i.warehouse, i.posting_date, i.posting_time))
                                print "\t",i
                                print "\t",balance
                                query = "update `tabStock Reconciliation Item` set current_qty={qty}, current_valuation_rate={rate} where name='{name}'".format(name=i.sr_name,qty=balance.qty, rate=balance.rate)
                                print "\t***",query
                                if update.lower() == "yes":
                                        frappe.db.sql(query)

                        # update difference_amount in Stock Reconciliation
                        diff_amount = frappe.db.sql("select sum(stock_value_difference) as tot_stock_value_difference from `tabStock Ledger Entry` where voucher_no='{0}'".format(key), as_dict=False)[0][0]
                        print "diff_amount",diff_amount
                        query = "update `tabStock Reconciliation` set difference_amount={diff_amount} where name = '{name}'".format(name=key,diff_amount=diff_amount)
                        print "***",query
                        if update.lower() == "yes":
                                frappe.db.sql(query)
                                
def test():
	for d in frappe.get_all("Payment Entry Deduction", ["name","amount"], {"parent":"PEJV190400003-2"}):
		print d.name, d.amount

# Following method created by SHIV on 2019/04/15
# This method will add entry to `tabSalary Slip Item` where ever it is missing
def add_ssl_item():
        ssl = frappe.db.sql("""
                select *
                from `tabSalary Slip` as ss
                where salary_structure is not null
                and start_date is not null
                and end_date is not null
                and not exists(select 1
                                from `tabSalary Slip Item` as ssi
                                where ssi.parent = ss.name)
                order by fiscal_year, month
        """, as_dict=True)
        counter = 0
        for i in ssl:
                counter += 1
                working_days = date_diff(i.end_date, i.start_date) + 1
                doc = frappe.get_doc("Salary Slip", i.name)
                row = doc.append("items", {})
                row.salary_structure    = i.salary_structure
                row.from_date           = i.start_date
                row.to_date             = i.end_date
                row.total_days_in_month = working_days
                row.working_days        = working_days
                row.save()
                print counter, i.name, i.fiscal_year, i.month

def cancel_ssl(pfiscal_year, pmonth):
        counter = 0
        for s in frappe.db.sql("select name from `tabSalary Slip` where fiscal_year='{0}' and month = '{1}' and docstatus=1".format(pfiscal_year, pmonth), as_dict=True):
                counter += 1
                print counter, s.name
                doc = frappe.get_doc("Salary Slip", s.name)
                doc.cancel()
        print "Total",counter


def analyze():
        qry = """
                select table_name
                from information_schema.tables t
                where t.table_schema = database()
                and engine = 'InnoDB'
                and lower(t.table_name) not like '%bkup%'
                and lower(t.table_name) not like '%bkp%'
        """

        counter = 0
        for i in frappe.db.sql(qry, as_dict=True):
                counter += 1
                print counter, i.table_name,'analyze table `{0}`'.format(i.table_name)
                frappe.db.sql('analyze table `{0}`'.format(i.table_name))
        
def check_pk():
        pri_qry = """
                select table_name
                from information_schema.tables t
                where t.table_schema = '4915427b5860138f'
                and lower(t.table_name) not like '%bkup%'
                and lower(t.table_name) not like '%bkp%'
                and not exists(
                        select 1
                        from information_schema.columns c
                        where c.table_schema = t.table_schema
                        and c.table_name = t.table_name
                        and c.column_key = 'PRI'
                )
        """
        for i in frappe.db.sql(pri_qry, as_dict=True):
                print i.table_name

def add_employee_internal_work_history_record():
	doc = frappe.get_doc("Muster Roll Employee", "11210002416")
	row = doc.append("internal_work_history",{})
	row.branch = "Wangchhu Zam Construction Project"
	row.cost_center = "Wangchhu Zam Construction Project - CDCL"
	row.from_date = "2019-01-04"
	row.save()
        print 'Done adding rows....'

# Check salary structures for mismatch in total earnings and total deductions
def validate_salary_structure():
	counter = 0
	for sst in frappe.get_all("Salary Structure",fields=["name","employee_name","branch","total_earning","total_deduction"]):
		tot_earnings = tot_deductions = 0

		tot_earnings, tot_deductions = frappe.db.sql("""
			select
				sum(case when parentfield = 'earnings' then ifnull(amount,0) else 0 end) tot_earnings,
				sum(case when parentfield = 'deductions' then ifnull(amount,0) else 0 end) tot_deductions
			from `tabSalary Detail`
			where parenttype = 'Salary Structure'
			and parent = '{0}'
		""".format(sst.name), as_dict=False)[0]
		if flt(sst.total_earning) != flt(tot_earnings) or flt(sst.total_deduction) != flt(tot_deductions):
			counter += 1
			#doc = frappe.get_doc("Salary Structure",sst.name)
			#doc.save()
			print counter,"|",sst.name,"|",sst.employee_name,"|",sst.branch,"|", flt(sst.total_earning)-flt(tot_earnings),"|",flt( sst.total_deduction)-flt(tot_deductions)

# Check salary slips for mismatch in total earnings and total deductions
def validate_salary_slip():
        counter = 0
        for ss in frappe.get_all("Salary Slip", ["name","employee_name","branch","gross_pay","total_deduction"], {"yearmonth":"201811"}):
                counter += 1
                tot_earnings = tot_deductions = 0

                tot_earnings, tot_deductions = frappe.db.sql("""
                        select
                                sum(case when parentfield = 'earnings' then ifnull(amount,0) else 0 end) tot_earnings,
                                sum(case when parentfield = 'deductions' then ifnull(amount,0) else 0 end) tot_deductions
                        from `tabSalary Detail`
                        where parenttype = 'Salary Slip'
                        and parent = '{0}'
                """.format(ss.name), as_dict=False)[0]
		#print ss.name,ss.gross_pay,tot_earnings,flt(ss.gross_pay)-flt(tot_earnings),ss.total_deduction,tot_deductions,flt(ss.total_deduction)-flt(tot_deductions)
                if flt(ss.gross_pay) != flt(tot_earnings) or flt(ss.total_deduction) != flt(tot_deductions):
                        print counter,"|",ss.name,"|",ss.employee_name,"|",ss.branch,"|", flt(ss.gross_pay)-flt(tot_earnings),"|",flt( ss.total_deduction)-flt(tot_deductions)

def adjust_leave_encashment():
        les = frappe.db.sql("select name, encashed_days, employee from `tabLeave Encashment` where docstatus = 1 and application_date between %s and %s", ('2017-01-01', '2017-12-31'), as_dict=True)
        for le in les:
                print(str(le.name))
                allocation = frappe.db.sql("select name, to_date from `tabLeave Allocation` where docstatus = 1 and employee = %s and leave_type = 'Earned Leave' order by to_date desc limit 1", (le.employee), as_dict=True)
                obj = frappe.get_doc("Leave Allocation", allocation[0].name)
                obj.db_set("leave_encashment", le.name)
                obj.db_set("encashed_days", (le.encashed_days))
                obj.db_set("total_leaves_allocated", (flt(obj.total_leaves_allocated) - flt(le.encashed_days)))

def get_date():
	print(now())
def update_ss():
	sss = frappe.db.sql("select name from `tabSalary Structure`", as_dict=True)
	for ss in sss:
		doc = frappe.get_doc("Salary Structure", ss)
		doc.save()

def update_customer():
	ccs = frappe.db.sql("select name from `tabCost Center` where is_group != 1", as_dict=True)
	for cc in ccs:
		obj = frappe.get_doc("Cost Center", cc)
		print(cc)
		obj.save()

def update_employee():
	emp_list = frappe.db.sql("select name from tabEmployee", as_dict=True)
	for emp in emp_list:
		print(emp.name)
		edoc = frappe.get_doc("Employee", emp)
		branch = frappe.db.get_value("Cost Center", edoc.cost_center, "branch")
		if branch:
			edoc.branch = branch
			edoc.save()
		else:
			frappe.throw("No branch for " + str(edoc.cost_center) + " for " + str(emp))

def give_admin_access():
	reports = frappe.db.sql("select name from tabReport", as_dict=True)
	for r in reports:
		role = frappe.new_doc("Report Role")
		role.parent = r.name
		role.parenttype = "Report"
		role.parentfield = "roles"
		role.role = "Administrator"
		role.save()		

def save_equipments():
	for a in frappe.db.sql("select name from tabEquipment", as_dict=True):
		doc = frappe.get_doc("Equipment", a.name)
		print(str(a))
		doc.save()

def submit_ss():
	ss = frappe.db.sql("select name from `tabSalary Structure`", as_dict=True)
	for s in ss:
		doc = frappe.get_doc("Salary Structure", s.name)
		for a in doc.earnings:
			if a.salary_component == "Basic Pay":
				print(str(doc.employee) + " ==> " + str(a.amount))
				update_salary_structure(doc.employee, flt(a.amount), s.name)
				break
		#doc.save()

def create_users():
	emp = frappe.db.sql("select name, company_email from tabEmployee where status = 'Active'", as_dict=True)
	if emp:
		for e in emp:
			print(str(e.name))
			doc = frappe.new_doc("User")
			doc.enabled = 1
			doc.email = e.company_email
			doc.first_name = "Test"
			doc.new_password = "CDCL!2017"
			doc.save()
		
			role = frappe.new_doc("UserRole")
			role.parent = doc.name
			role.role = "Employee"
			role.parenttype = "User"
			role.save()
			doc.save()
			em = frappe.get_doc("Employee", e.name)	
			em.user_id = doc.name
			em.save()
		print("DONE")

def submit_assets():
	list = frappe.db.sql("select name from tabAsset where docstatus = 0", as_dict=True)
	if list:
		num = 0
		for a in list:
			num = num + 1
			doc = frappe.get_doc("Asset", a.name)
			doc.submit()
			print(str(a.name))
			if cint(num) % 100 == 0:
				frappe.db.commit()
		print("DONE")

def give_permission():
	users = frappe.db.sql("select name from tabUser", as_dict=True)
	for u in users:
		if u.name in ['admins@cdcl.bt', 'proco@cdcl.bt', 'accounts@cdcl.bt', 'project@cdcl.bt', 'maintenance@cdcl.bt', 'fleet@cdcl.bt', 'sales@cdcl.bt','stock@cdcl.bt', 'hr@cdcl.bt','tashi.dorji775@bt.bt', 'sonam.zangmo@bt.bt', 'siva@bt.bt', 'jigme@bt.bt', 'dorji2392@bt.bt', 'sangay.dorji2695@bt.bt', 'lhendrup.dorji@bt.bt']:
			for branch in frappe.db.sql("select name from tabBranch", as_dict=True):
				#if branch == 'Lingmethang':
				frappe.permissions.add_user_permission("Branch", branch.name, u.name)
			print("DONE")	
		print(str(u))

##
# Post earned leave on the first day of every month
##
def post_earned_leaves():
	date = add_years(frappe.utils.nowdate(), 1)
	start = get_first_day(date);
	end = get_last_day(date);
	
	employees = frappe.db.sql("select name, employee_name from `tabEmployee` where status = 'Active' and employment_type in (\'Regular\', \'Contract\')", as_dict=True)
	for e in employees:
		la = frappe.new_doc("Leave Allocation")
		la.employee = e.name
		la.employee_name = e.employee_name
		la.leave_type = "Casual Leave"
		la.from_date = str(start)
		la.to_date = str(end)
		la.carry_forward = cint(0)
		la.new_leaves_allocated = flt(10)
		la.submit()
		
#Create asset received entries for asset balance
def createAssetEntries():
	frappe.db.sql("delete from `tabAsset Received Entries`")
	receipts = frappe.db.sql("select pr.posting_date, pr.name, pri.item_code, pri.qty from `tabPurchase Receipt` pr,  `tabPurchase Receipt Item` pri  where pr.docstatus = 1 and pri.docstatus = 1 and pri.parent = pr.name", as_dict=True)
	for a in receipts:
		item_group = frappe.db.get_value("Item", a.item_code, "item_group")
		if item_group and item_group == "Fixed Asset":
			ae = frappe.new_doc("Asset Received Entries")
			ae.item_code = a.item_code
			ae.qty = a.qty
			ae.received_date = a.posting_date
			ae.ref_doc = a.name
			ae.submit()

# create consumed and committed budget
def budget():
	deleteExisting()
	commitBudget();
	consumeBudget();
	adjustBudgetJE()

def deleteExisting():
	print("Deleting existing data")
	frappe.db.sql("delete from `tabCommitted Budget`")
	frappe.db.sql("delete from `tabConsumed Budget`")

##
# Commit Budget
##
def commitBudget():
	print("Committing budgets from PO")
	orders = frappe.db.sql("select name from `tabPurchase Order` where docstatus = 1", as_dict=True)
	for a in orders:
		order = frappe.get_doc("Purchase Order", a['name'])
		for item in order.get("items"):
			account_type = frappe.db.get_value("Account", item.budget_account, "account_type")
			if account_type in ("Fixed Asset", "Expense Account"):
				consume = frappe.get_doc({
					"doctype": "Committed Budget",
					"account": item.budget_account,
					"cost_center": item.cost_center,
					"po_no": order.name,
					"po_date": order.transaction_date,
					"amount": item.amount,
					"item_code": item.item_code,
					"date": frappe.utils.nowdate()})
				consume.submit()


##
# Commit Budget
##
def adjustBudgetJE():
	print("Committing and consuming from JE")
	entries = frappe.db.sql("select name from `tabGL Entry` where voucher_type='Journal Entry' and (against_voucher_type != 'Asset' or against_voucher_type is null)", as_dict=True)
	for a in entries:
		gl = frappe.get_doc("GL Entry", a['name'])
		account_type = frappe.db.get_value("Account", gl.account, "account_type")
		
		if account_type in ("Fixed Asset", "Expense Account"):
			commit = frappe.get_doc({
					"doctype": "Committed Budget",
					"account": gl.account,
					"cost_center": gl.cost_center,
					"po_no": gl.voucher_no,
					"po_date": gl.posting_date,
					"amount": gl.debit - gl.credit,
					"item_code": "",
					"date": frappe.utils.nowdate()})
			commit.submit()
			
			consume = frappe.get_doc({
					"doctype": "Consumed Budget",
					"account": gl.account,
					"cost_center": gl.cost_center,
					"po_no": gl.voucher_no,
					"po_date": gl.posting_date,
					"amount": gl.debit - gl.credit,
					"item_code": "",
					"com_ref": gl.voucher_no,
					"date": frappe.utils.nowdate()})
			consume.submit()

##
# Commit Budget
##
def consumeBudget():
	print("Consuming budgets from PI")
	invoices = frappe.db.sql("select name from `tabPurchase Invoice` where docstatus = 1", as_dict=True)
	for a in invoices:
		invoice = frappe.get_doc("Purchase Invoice", a['name'])
		for item in invoice.get("items"):
			expense, cost_center = frappe.db.get_value("Purchase Order Item", {"item_code": item.item_code, "cost_center": item.cost_center, "parent": item.purchase_order, "docstatus": 1}, ["budget_account", "cost_center"])
			if expense:
				account_type = frappe.db.get_value("Account", expense, "account_type")
				if account_type in ("Fixed Asset", "Expense Account"):
					po_date = frappe.db.get_value("Purchase Order", item.purchase_order, "transaction_date")
					consume = frappe.get_doc({
						"doctype": "Consumed Budget",
						"account": expense,
						"cost_center": item.cost_center,
						"po_no": invoice.name,
						"po_date": po_date,
						"amount": item.amount,
						"item_code": item.item_code,
						"com_ref": item.purchase_order,
						"date": frappe.utils.nowdate()})
					consume.submit()
	

##
# Update presystem date
##
def updateDate():
	import csv
	with open('/home/frappe/emines/sites/emines.smcl.bt/public/files/myasset.csv', 'rb') as f:
		reader = csv.reader(f)
		mylist = list(reader)
		for i in mylist:
			asset = frappe.get_doc("Asset", i[0])
			asset.db_set("presystem_issue_date", i[1])
			
		print ("DONE")
##
# Sets the initials of autoname for PO, PR, SO, SI, PI, etc
##
def moveConToCom():
	pass
	consumed = frappe.get_all("Consumed Budget")
	to = len(consumed)
	i = 0
	for a in consumed:
		i = i + 1
		d = frappe.get_doc("Consumed Budget", a.name)
		obj = frappe.get_doc({
				"doctype": "Committed Budget",
				"account": d.account,
				"cost_center": d.cost_center,
				"po_no": d.po_no,
				"po_date": d.po_date,
				"amount": d.amount,
				"item_code": d.item_code,
				"date": d.date
			})
		obj.submit()
		d.delete();
		print(str(i * 100 / to))
	print("DONE")

def createConsumed():
	con = frappe.db.sql("select pe.name as name, per.reference_name as pi from `tabPayment Entry Reference` per, `tabPayment Entry` pe where per.parent = pe.name and pe.docstatus = 1 and per.reference_doctype = 'Purchase Invoice' and pe.posting_date between '2017-01-01' and '2017-12-31'", as_dict=True)
	for a in con:
		items = frappe.db.sql("select item_code, cost_center, purchase_order, amount from `tabPurchase Invoice Item`  where docstatus = 1 and parent = \'" + str(a.pi) + "\'", as_dict=True)
		for i in items:
			#con = frappe.db.sql("select name, po_no, amount, docstatus from `tabCommitted Budget` where po_no = \'" + i.purchase_order + "\' and item_code = \'" + i.item_code + "\' and cost_center = \'" + i.cost_center + "\'")
			con = frappe.db.sql("select name, po_no, amount, account from `tabCommitted Budget` where po_no = \'" + i.purchase_order + "\' and item_code = \'" + i.item_code + "\' and cost_center = \'" + i.cost_center + "\' and amount = \'" + str(i.amount) + "\'")
			print(str(a.name))
			if con:
				print(str(con))
			else:
				print("NOT FOUND")
			#print(str(i.purchase_order) + " / " + str(i.item_code) + " / " + str(i.amount))


# /home/frappe/erp bench execute erpnext.custom_patch.grant_permission_all_test
def grant_permission_all_test():
        emp_list = frappe.db.sql("""
                                 select company, branch, name as employeecd, user_id, 'Employee' type
                                 from `tabEmployee`
                                 where user_id is not null
                                 and exists(select 1
                                                from  `tabUser`
                                                where `tabUser`.name = `tabEmployee`.user_id)
                                and name = 'CDCL0403003'
                        """, as_dict=1)

        for emp in emp_list:
                # From Employee Master
                frappe.permissions.remove_user_permission("Company", emp.company, emp.user_id)
                frappe.permissions.remove_user_permission("Branch", emp.branch, emp.user_id)

                frappe.permissions.add_user_permission("Company", emp.company, emp.user_id)
                frappe.permissions.add_user_permission("Branch", emp.branch, emp.user_id)

                frappe.permissions.remove_user_permission(emp.type, emp.employeecd, emp.user_id)
                frappe.permissions.add_user_permission(emp.type, emp.employeecd, emp.user_id)
                
                # From Assign Branch 
                ba = frappe.db.sql("""
                                select branch
                                from `tabBranch Item`
                                where exists(select 1
                                               from `tabAssign Branch`
                                               where `tabAssign Branch`.name = `tabBranch Item`.parent
                                               and   `tabAssign Branch`.user = '{0}')
                        """.format(emp.user_id), as_dict=1)
                

                for a in ba:
                        frappe.permissions.remove_user_permission("Branch", a.branch, emp.user_id)
                        frappe.permissions.add_user_permission("Branch", a.branch, emp.user_id)


def grant_permission_all():
        emp_list = frappe.db.sql("""
                                 select company, branch, name as employeecd, user_id, 'Employee' type
                                 from `tabEmployee`
                                 where user_id is not null
                                 and exists(select 1
                                                from  `tabUser`
                                                where `tabUser`.name = `tabEmployee`.user_id)
                                union all
                                select company, branch, name as employeecd, user_id, 'GEP Employee' type
                                 from `tabGEP Employee`
                                 where user_id is not null
                                 and exists(select 1
                                                from  `tabUser`
                                                where `tabUser`.name = `tabGEP Employee`.user_id)
                                union all
                                select company, branch, name as employeecd, user_id, 'Muster Roll Employee' type
                                 from `tabMuster Roll Employee`
                                 where user_id is not null
                                 and exists(select 1
                                                from  `tabUser`
                                                where `tabUser`.name = `tabMuster Roll Employee`.user_id)
                        """, as_dict=1)

        for emp in emp_list:
                # From Employee Master
                frappe.permissions.remove_user_permission("Company", emp.company, emp.user_id)
                frappe.permissions.remove_user_permission("Branch", emp.branch, emp.user_id)

                frappe.permissions.add_user_permission("Company", emp.company, emp.user_id)
                frappe.permissions.add_user_permission("Branch", emp.branch, emp.user_id)

                frappe.permissions.remove_user_permission(emp.type, emp.employeecd, emp.user_id)
                frappe.permissions.add_user_permission(emp.type, emp.employeecd, emp.user_id)
                                                
                # From Assign Branch 
                ba = frappe.db.sql("""
                                select branch
                                from `tabBranch Item`
                                where exists(select 1
                                               from `tabAssign Branch`
                                               where `tabAssign Branch`.name = `tabBranch Item`.parent
                                               and   `tabAssign Branch`.user = '{0}')
                        """.format(emp.user_id), as_dict=1)
                

                for a in ba:
                        frappe.permissions.remove_user_permission("Branch", a.branch, emp.user_id)
                        frappe.permissions.add_user_permission("Branch", a.branch, emp.user_id)

def remove_memelakha_entries():
	# This is done after manually crosschecking, everything is ok
	il = frappe.db.sql("""
		select a.name, b.item_code, count(*), sum(b.qty)
		from `tabStock Entry` a, `tabStock Entry Detail` b
		where a.branch = 'Memelakha Asphalt Plant' 
		and b.parent = a.name
		and a.job_card is null
		and a.name not in ('SECO17100009')
		and a.purpose = 'Material Issue'
		and lower(title) not like '%asphalt%'
		group by a.name, b.item_code
		order by a.name, b.item_code;
		""", as_dict=1)
	
	counter = 0

	for i in il:
		counter += 1
		idoc = frappe.get_doc("Stock Entry", i.name)
		print counter, idoc.name, idoc.docstatus

# 25/12/2017 SHIV, It is observed that parent cost_centers are used in the transaction which is wrong
def check_for_cc_group_entries():
        ex = ['Cost Center','Attendance Tool Others','Budget Reappropriation Tool','Project Overtime Tool', 'Supplementary Budget Tool']

        li = frappe.db.sql("""
                        select g.doctype, g.fieldname, g.table_name
                        from (
                        
                                select
                                        parent as doctype,
                                        fieldname,
                                        'tabDocField' as table_name
                                from `tabDocField` 
                                where (
                                        (fieldtype = 'Link' and options = 'Cost Center')
                                        or
                                        (lower(fieldname) like '%cost%center%' and fieldtype in ('Data','Dynamic Link','Small Text','Long Text','Read Only', 'Text'))
                                        )
                                union all
                                select
                                        dt as doctype,
                                        fieldname,
                                        'tabCustom Field' as table_name
                                from `tabCustom Field` 
                                where (
                                        (fieldtype = 'Link' and options = 'Cost Center')
                                        or
                                        (lower(fieldname) like '%cost%center%' and fieldtype in ('Data','Dynamic Link','Small Text','Long Text','Read Only', 'Text'))
                                        )
                        ) as g
                        where g.doctype not in ({0})
                """.format("'"+"','".join(ex)+"'"), as_dict=1)

        for i in li:
                no_of_rec = 0
                
                counts = frappe.db.sql("""
                                select a.{1} cc, count(*) counts
                                from `tab{0}` as a
                                where a.{1} is not null
                                and exists(select 1
                                                from `tabCost Center` as b
                                                where b.name = a.{1}
                                                and b.is_group = 1)
                                group by a.{1}
                """.format(i.doctype, i.fieldname), as_dict=1)

                '''
                if counts:
                        if counts[0].counts > 0:
                                no_of_rec = counts[0].counts
                                print i.doctype+" ("+i.fieldname+") : "+str(no_of_rec)
                '''

                for c in counts:
                        print i.doctype.ljust(50,' ')+str(":"), c.cc, c.counts
                

# 2018/06/06, Hap Dorji, Sotck Reconciliation entry didn't take effect on stock balance report for SR/000041
# /home/frappe/erp bench execute erpnext.temp_patch.update_stock_reconciliation
def update_stock_reconciliation():
        items = frappe.db.sql("""
                select *
                from `tabStock Ledger Entry`
                where voucher_type = 'Stock Reconciliation'
                and voucher_no = 'SR/000041'
                and docstatus < 2
                order by posting_date, posting_time
        """, as_dict=1)

        upd_counter = 0
        for i in items:
                diff = 0
                prev = frappe.db.sql("""
                        select *
                        from `tabStock Ledger Entry`
                        where warehouse = '{0}'
                        and item_code = '{1}'
                        and posting_date <= '{2}'
                        and posting_time < '{3}'
                        and docstatus < 2
                        order by posting_date desc, posting_time desc
                        limit 1
                """.format(i.warehouse, i.item_code, i.posting_date, i.posting_time), as_dict=1)

                if prev:
                        diff = flt(i.stock_value,5)-flt(prev[0].stock_value,5)
                        print 'F',i.item_code, i.stock_value, prev[0].stock_value, flt(i.stock_value_difference,5), flt(diff,5)
                else:
                        diff = i.stock_value
                        print 'N',i.item_code, i.stock_value, flt(i.stock_value_difference,5), flt(diff,5)

                if flt(i.stock_value_difference,5) != flt(diff,5):
                        print 'updading...'
                        frappe.db.sql("""
                                update `tabStock Ledger Entry`
                                set stock_value_difference = {0}
                                where name = '{1}'
                        """.format(diff, i.name))
                        upd_counter += 1

        print 'Total No.of rows updated: ',upd_counter

#
# Updating ref_doc in `tabReappropriation Details` for transactions prior to introduction of submit button on "Budget Reappropiation" screen
# 2018/06/27
#
def update_budget_reappropriation():
        print 'Creating a dummy reappropriation'
        doc = frappe.new_doc("Budget Reappropiation")
        doc.from_cost_center = "Gelephu - CDCL"
        doc.to_cost_center = "Gelephu - CDCL"
        doc.fiscal_year = "2018"
        doc.save(ignore_permissions=True)
        doc.submit()

def get_monthly_count(from_date, to_date):
    print from_date, to_date
    mcount = {}
    from_month      = str(from_date)[5:7]
    to_month        = str(to_date)[5:7]
    from_year       = str(from_date)[:4]
    to_year         = str(to_date)[:4]
    from_monthyear  = str(from_year)+str(from_month)
    to_monthyear    = str(to_year)+str(to_month)
    
    for y in range(int(from_year), int(to_year)+1):
        m_start = from_month if str(y) == str(from_year) else '01'
        m_end   = to_month if str(y) == str(to_year) else '12'
                            
	print 'Year:',y                            
        for m in range(int(m_start), int(m_end)+1):
	    print 'Month:',m
            key          = str(y)+(str(m).rjust(2,str('0')))
            m_start_date = key[:4]+'-'+key[4:]+'-01'
            m_start_date = from_date if str(y)+str(m).rjust(2,str('0')) == str(from_year)+str(from_month) else m_start_date
            m_end_date   = to_date if str(y)+str(m).rjust(2,str('0')) == str(to_year)+str(to_month) else get_last_day(m_start_date)
	    print str(y)+str(m),str(from_year)+str(from_month),str(to_year)+str(to_month)
	    print m_start_date, m_end_date
            if mcount.has_key(key):
                mcount[key]['local'] += date_diff(m_end_date, m_start_date)+1
            else:
                mcount[key] = {'local': date_diff(m_end_date, m_start_date)+1, 'claimed': 0}                                                

    print collections.OrderedDict(sorted(mcount.items()))
    for k,v in collections.OrderedDict(sorted(mcount.items())).iteritems():
	print k,v

    keys = [k for k in mcount]
    print keys

    format_strings = ','.join(['%s'] * len(mcount))
    print format_strings
    print "VALUES IN ({0})".format(format_strings) % tuple(keys)

