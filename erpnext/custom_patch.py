from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import msgprint
from frappe.utils import flt, cint, now, nowdate, getdate
from frappe.utils.data import date_diff, add_days, get_first_day, get_last_day, add_years
#from erpnext.hr.hr_custom_functions import get_month_details, get_company_pf, get_employee_gis, get_salary_tax, update_salary_structure
from erpnext.hr.hr_custom_functions import get_month_details, get_payroll_settings, get_salary_tax
from datetime import timedelta, date
from erpnext.custom_utils import get_branch_cc, get_branch_warehouse
import csv

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
						if s.employee_subgroup in ("M7", "M7 ( Contract )", "O7", "F7", "M6", "M6 (Contract)", "M5", "M4", "M4 Contract", "E3", "E4", "E3 ( Contract )", "E4 ( Contract )", "E2", "CEO"):
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

# 2022/07/22 BY SHIV
# Someone's silly code deleted components from SST, hence this method is created to recreate those 
#	missing components under SST based on the latest salary slip 2022-06
def sst_create_missing_components(debug=1):
	'''
	1. Found that the malicious code effected only those components who have reference_number value
	2. While restoring from_date, to_date needs to be determined by past salary slips
	'''
	
	def _get_from_date(ref_docname):
		''' get starting day of a components effect '''
		return frappe.db.sql("""select min(from_date) from `tabSalary Detail`
				where ref_docname="{}" """.format(ref_docname))[0][0]
	
	def _get_max_idx(salary_structure, parentfield):
		''' get max idx from salary structure '''
		return frappe.db.sql("""select max(idx) from `tabSalary Detail`
				where parent = "{}" and parentfield = "{}" """.format(salary_structure, parentfield))[0][0]

	def _str(value):
		return '"{}"'.format(value)

	missing = frappe.db.sql("""SELECT sd.*, ssi.salary_structure
				FROM `tabSalary Detail` sd, `tabSalary Slip` ss, `tabSalary Slip Item` ssi
				WHERE ss.yearmonth = '202206'
				AND ss.docstatus = 1
				AND ssi.parent = ss.name
				AND sd.parent = ss.name
				AND sd.reference_number IS NOT NULL
				AND sd.salary_component != 'Other Contribution'
				AND (
					IFNULL(sd.total_deductible_amount,0) = 0
					OR
					(IFNULL(sd.total_deductible_amount,0) > 0 AND IFNULL(sd.total_deductible_amount,0)-IFNULL(sd.total_deducted_amount,0) > 0)
				)
				AND NOT EXISTS(SELECT 1
					FROM `tabSalary Detail` d2
					WHERE d2.name = sd.ref_docname)
				ORDER BY ss.employee, sd.parentfield, sd.idx""", as_dict=True) 
	counter = 0
	for i in missing:
		counter += 1
		from_date 	= _get_from_date(i.ref_docname)
		max_idx 	= _get_max_idx(i.salary_structure, i.parentfield)

		qry = """INSERT INTO `tabSalary Detail`(name, creation, modified, modified_by, owner, docstatus, 
							parent, parentfield, parenttype, idx, default_amount, depends_on_lwp, amount,
							salary_component, from_date, to_date, institution_name, reference_number,
							total_deductible_amount, total_deducted_amount, total_outstanding_amount,
							reference_type, salary_component_type, ref_docname, submission, submitted_by, 
							payment_days, total_days_in_month, working_days, leave_without_pay,
							bank_branch, bank_account_type
							)
						VALUES({}, NOW(), NOW(), "Administrator", "Administrator", 1,
							{}, {}, "Salary Structure", {}, {}, {}, {},
							{}, {}, NULL, {}, {},
							{}, {}, {},
							{}, {}, NULL, NULL, NULL,
							0, 0, 0, {},
							{}, {}
						)
			""".format(_str(i.ref_docname),
					_str(i.salary_structure), _str(i.parentfield), cint(max_idx) + 1, i.default_amount, i.depends_on_lwp, i.amount,
					_str(i.salary_component), _str(from_date) if from_date else "NULL", _str(i.institution_name) if i.institution_name else "NULL", _str(i.reference_number),
					i.total_deductible_amount, i.total_deducted_amount, i.total_outstanding_amount, 
					_str(i.reference_type) if i.reference_type else "NULL", _str(i.salary_component_type) if i.salary_component_type else "NULL", 
					i.leave_without_pay,
					_str(i.bank_branch) if i.bank_branch else "NULL", _str(i.bank_account_type) if i.bank_account_type else "NULL"
			)

		print(qry)
		frappe.db.sql(qry)
		frappe.db.commit()
	print('Total no.of components missing: ', counter)

def sst_refresh_missing_components():
	for d in frappe.db.sql("""select parent from `tabSalary Detail`
				where owner='Administrator' and date(creation)='2022-07-24' """, as_dict=True):
		doc = frappe.get_doc("Salary Structure", d.parent)
		doc.save()
	frappe.db.commit()

def delete_cancelled_sws_members():
	smem = frappe.db.sql("""
		select name from `tabSWS Membership Item` where docstatus = 2
	""", as_dict=1)
	if smem:
		for a in smem:
			frappe.db.sql("""
				delete from `tabSWS Membership Item` where name = '{}'
			""".format(a.name))
			frappe.db.sql("""
				delete from `tabEmployee Family Details` where name = '{}'
			""".format(a.name))
			print(a.name)

def cancel_payment_entry():
	pe = ["PEJV220600081","PEBR220601486"]
	for a in pe:
		doc = frappe.get_doc("Payment Entry",a)
		doc.cancel()
		print(a)


def update_mechanical_payment_tds_rate():
	mp = frappe.db.sql("""
		select name, tds_account from `tabMechanical Payment` where tds_account in ('TDS - 2% - NRDCL','TDS - 3% - NRDCL','TDS - 5% - NRDCL','TDS - 10% - NRDCL');
	""",as_dict=1)
	if mp:
		for a in mp:
			mech_pay = frappe.get_doc("Mechanical Payment",a.name)
			if a.tds_account == "TDS - 2% - NRDCL":
				mech_pay.db_set("tds_rate","2")
			if a.tds_account == "TDS - 3% - NRDCL":
				mech_pay.db_set("tds_rate","3")
			if a.tds_account == "TDS - 5% - NRDCL":
				mech_pay.db_set("tds_rate","5")
			if a.tds_account == "TDS - 10% - NRDCL":
				mech_pay.db_set("tds_rate","10")
			print(str(a.name)+": tds rate set for tds account "+str(a.tds_account))



def update_staff_welfare_ss():
	sd = frappe.db.sql("""
		select a.name, a.parent, b.employee from `tabSalary Detail` a, `tabSalary Slip` b where a.parent = b.name and a.salary_component = 'Staff Welfare Loan'
		and a.reference_type is NULL and b.docstatus = 1
	""", as_dict=1)
	count = 1
	if sd:
		for a in sd:
			ssd = frappe.get_doc("Salary Detail", a.name)
			ssd.db_set("institution_name","NRDCL")
			ssd.db_set("reference_type","Staff Welfare Loan")
			print(str(count)+": "+str(a.employee)+": "+str(a.parent))
			count += 1

def submit_prd_20220211(debug=1):
	li = frappe.db.sql("""select 'Production' as doctype, name as docname
					from `tabProduction`
					where name in (	
						'PRO211202472')
					order by posting_date
				""", as_dict=True)
	counter = 0
	for i in li:
		counter += 1
		doc = frappe.get_doc("Production", i.docname)
		print(counter, i.docname, doc.docstatus)
		if not debug and doc.docstatus == 0:
			try:
				doc.submit()
				print('Submitted...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()
def submit_dn_20220707():
	dn = ['DN22070160']
	for a in dn:
		doc = frappe.get_doc("Delivery Note",a)
		doc.submit()
		print("submitted")

def submit_dn_20220211(debug=1):
	li = frappe.db.sql("""select 'Delivery Note' as doctype, name as docname
					from `tabDelivery Note`
					where name in (
			'DN22015419','DN21072365-1','DN22015253','DN22015252','DN22015250',
			'DN22015249','DN22015247','DN22015246','DN22015243',
			'DN22015242','DN22015241','DN22015239','DN22015238',
			'DN22015236','DN22015234','DN22015233','DN22015231',
			'DN22015230','DN22015227','DN22015223','DN22014672',
			'DN22015187','DN22015186','DN22015183','DN22015182',
			'DN22015181','DN22015178','DN22014381','DN22014374',
			'DN22014373','DN22014380','DN22014379','DN22014378',
			'DN22014377','DN22014376','DN22014375','DN22014372')
			order by posting_date
			""", as_dict=True)
	counter = 0
	for i in li:
		counter += 1
		doc = frappe.get_doc("Delivery Note", i.docname)
		print(counter, i.docname, doc.docstatus)
		if not debug and doc.docstatus == 0:
			try:
				doc.submit()
				print('Submitted...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()

def submit_prd_20220207(debug=1):
	li = frappe.db.sql("""select 'Production' as doctype, name as docname
					from `tabProduction`
					where name in (	
						'PRO220101151')
					order by posting_date
				""", as_dict=True)
	counter = 0
	for i in li:
		counter += 1
		doc = frappe.get_doc("Production", i.docname)
		print(counter, i.docname, doc.docstatus)
		if not debug and doc.docstatus == 0:
			try:
				doc.submit()
				print('Submitted...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()

def submit_dn_20220129(debug=1):
	li = frappe.db.sql("""select 'Delivery Note' as doctype, name as docname
					from `tabDelivery Note`
					where name in (
			'DN21129050','DN21112852','DN22012473','DN21129742','DN21127831','DN21094656','DN21054923','DN22012488',
			'DN21054931','DN21129370','DN22011301','DN21103133-1','DN21127970','DN21127950','DN21126078-2','DN21127506',
			'DN21115481','DN21090980','DN21090975','DN21104632-1','DN21104631-1','DN21128420','DN21128418','DN21128416',
			'DN21128414','DN21128410','DN21083392','DN21128352','DN21128350','DN21103781','DN21103780','DN21103779',
			'DN21103778','DN21103777','DN21103776','DN21103774','DN21103773','DN21103764','DN21103762','DN21103761',
			'DN21103759','DN21103756','DN21103755','DN21103740','DN21103737','DN21103736','DN21103735','DN21103732',
			'DN21091609','DN21091607','DN21091599','DN21091596','DN21091593','DN21090836','DN21090647','DN21090646',
			'DN21090645','DN21090644','DN21090643','DN21090642','DN21090602','DN21090601','DN21090600','DN21090599',
			'DN21090598','DN21090597','DN21090596','DN21090595','DN21090594','DN21090593','DN21090592','DN21090591',
			'DN21090590','DN21090589','DN21090588','DN21090587','DN21090586','DN21090585','DN21090584','DN21090577',
			'DN21090576','DN21090575','DN21084694','DN21084692','DN21084691','DN21084690','DN21084689','DN21084688',
			'DN21084687','DN21084686','DN21084651','DN21084648','DN21084646','DN21084644','DN21084643','DN21084641',
			'DN21084638','DN21084636','DN21084635','DN21084631','DN21084630','DN21084359','DN21084357','DN21084329',
			'DN21084225','DN21084213','DN21084212','DN21084208','DN21084206','DN21084205','DN21084204','DN21084194',
			'DN21084013','DN21083990','DN21083801','DN21083797','DN21083794','DN21083791','DN21083788','DN21083787',
			'DN21083683','DN21083682','DN21083681','DN21083679','DN21083657','DN21083655','DN21083649','DN21083644',
			'DN21083643','DN21083642','DN21083641','DN21083640','DN21083639','DN21083638','DN21083637','DN21083543',
			'DN21083533','DN21083406','DN21083404','DN21083403','DN21083390','DN21083382','DN21083379','DN21083377',
			'DN21083374','DN21083373','DN21083370','DN21083369','DN21083363','DN21083362','DN21083088','DN21083086',
			'DN21083083','DN21083081','DN21083079','DN21083077','DN21083075','DN21083073','DN21083072','DN21081741',
			'DN22010176','DN21129454','DN22014020','DN22014017','DN22014016','DN22011071','DN22011070','DN22011069',
			'DN22011068','DN22011067','DN22011066','DN22011065','DN22011064','DN22011063','DN22011062','DN22011061',
			'DN22011060','DN22011059','DN22011058','DN22011057','DN22011056','DN22011055','DN22011054','DN22011053',
			'DN22011052','DN22011051','DN22011050','DN22011049','DN22011048','DN22011047','DN22011046','DN22011045',
			'DN22011044','DN22011043','DN22011042','DN22011041','DN22011040','DN22011039','DN22011038','DN22011037',
			'DN22011036','DN22011035','DN22011034','DN22011033','DN22011032','DN22011031','DN22011030','DN22011029',
			'DN22011028','DN22011027','DN22011026','DN22011025','DN22011024','DN22011023','DN22011022','DN22011021',
			'DN22011020','DN22011019','DN22011018','DN22011017','DN22011016','DN22011015','DN22011014','DN22011013',
			'DN22011012','DN22011011','DN22011010','DN22011009','DN22011008','DN22011007','DN22011006','DN22011005',
			'DN22011004','DN22011003','DN22011002','DN22011001','DN22011000','DN22010999','DN22010998','DN22010997',
			'DN22010996','DN22010995','DN22010994','DN22010993','DN22010992','DN22010991','DN22010990','DN22010989',
			'DN22010988','DN22010987','DN22010986','DN22010985','DN22010984','DN22010983','DN22010982','DN22010981',
			'DN22010980','DN22010979','DN22010978','DN22010977','DN22010976','DN22010975','DN22010974','DN22010973',
			'DN22010972','DN22010971','DN22010970','DN22010969','DN22010968','DN22010967','DN22010966','DN22010965',
			'DN22010964','DN22010963','DN22010962','DN22010961','DN22010960','DN22010959','DN22010958','DN22010957',
			'DN22010956','DN22010955','DN22010954','DN22010953','DN22010952','DN22010951','DN22010950','DN22010949',
			'DN22010948','DN22010947','DN22010946','DN22010945','DN22010944','DN22010943','DN22010942','DN22010941',
			'DN22010940','DN22010939','DN22010938','DN22010937','DN22010936','DN22010935','DN22010934','DN22010933',
			'DN22010932','DN22010931','DN22010930','DN22010929','DN22010928','DN22010927','DN22010926','DN22010925',
			'DN22010924','DN22010923','DN22010922','DN22010921','DN22010920','DN22010919','DN22010918','DN22010917',
			'DN22010916','DN22010915','DN22010914','DN22010913','DN22010912','DN22010911','DN22010910','DN22010909',
			'DN22010908','DN22010907','DN22010906','DN22010905','DN22010904','DN22010903','DN22010902','DN22010901',
			'DN22010900','DN22010899','DN22010898','DN22010897','DN22010896','DN22010895','DN22010894','DN22010893',
			'DN22010892','DN22010891','DN22010890','DN22010889','DN22010888','DN22010887','DN22010886','DN22010885',
			'DN22010884','DN22010883','DN22010882','DN22010881','DN22010880','DN22010879','DN22010878','DN22010877',
			'DN22010876','DN22010874','DN22010873','DN22010872','DN22010871','DN22010870','DN22010869','DN22010868',
			'DN22010867','DN22010866','DN22010865','DN22010864','DN22010863','DN22010862','DN22010858','DN22010856',
			'DN22010861','DN22010860','DN22010859','DN22010857','DN22010855','DN22010854','DN22010853','DN22010852',
			'DN22010851','DN22010850','DN22010849','DN22010848','DN22010847','DN22010846','DN22010845','DN22010844',
			'DN22010843','DN22010842','DN22010841','DN22010840','DN22010839','DN22010838','DN22010837','DN22010836',
			'DN22010835','DN22010834','DN22010833','DN22010832','DN22010831','DN22010830','DN22010829','DN22010828',
			'DN22010827','DN22010826','DN22010794','DN22010793','DN22010791','DN22010789','DN22010787','DN22010786',
			'DN22010785','DN22010784','DN22010783','DN22010782','DN22010781','DN22010778','DN21129531','DN21129530',
			'DN21129529','DN21129528','DN21129527','DN21129526','DN21129525','DN21129524','DN21129523','DN21129522',
			'DN21129521','DN21129520','DN21129519','DN21129518','DN21129517','DN21129516','DN21129515','DN21129514',
			'DN21129513','DN21129512','DN21129511','DN21129510','DN21129509','DN21129508','DN21129507','DN21129506',
			'DN21129505','DN21129504','DN21129503','DN21129502','DN21129501','DN21129500','DN21129499','DN21129498',
			'DN21129497','DN21129496','DN21129495','DN21129494','DN21129493','DN21129492','DN21129491','DN21129490',
			'DN21129489','DN21129488','DN21129487','DN21129486','DN21129485','DN21129484','DN21129483','DN21129482',
			'DN21129481','DN21129480','DN21129479','DN21129478','DN21129477','DN21129476','DN21129475','DN21129474',
			'DN21129473','DN21129472','DN21129471','DN21129470','DN21129469','DN21129468','DN21129467','DN21129466',
			'DN21129465','DN21129464','DN21129463','DN21129462','DN21129461','DN21129460','DN21129459','DN21129458',
			'DN21129457','DN21129456','DN21129455','DN21128494','DN21128458','DN21128456','DN21128451','DN21128438',
			'DN21128437','DN21128434','DN21128432','DN21128427','DN21123068','DN21123058','DN21110409','DN21082712',
			'DN21082711','DN21082710','DN21082707-1','DN21070753','DN21061079','DN21054935','DN21054064','DN21052602'
					)
					order by posting_date
				""", as_dict=True)
	counter = 0
	for i in li:
		counter += 1
		doc = frappe.get_doc("Delivery Note", i.docname)
		print(counter, i.docname, doc.docstatus)
		if not debug and doc.docstatus == 0:
			try:
				doc.submit()
				print('Submitted...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()

def submit_prd_20220129(debug=1):
	li = frappe.db.sql("""select 'Production' as doctype, name as docname
					from `tabProduction`
					where name in (	
						'PRO220101010', 'PRO220100628', 'PRO220100702', 'PRO220100939', 'PRO220100685',
						'PRO220100617', 'PRO211202021', 'PRO210800931')
					order by posting_date
				""", as_dict=True)
	counter = 0
	for i in li:
		counter += 1
		doc = frappe.get_doc("Production", i.docname)
		print(counter, i.docname, doc.docstatus)
		if not debug and doc.docstatus == 0:
			try:
				doc.submit()
				print('Submitted...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()


def submit_dn_20220119(debug=1):
	li = frappe.db.sql("""select 'Delivery Note' as doctype, name as docname
					from `tabDelivery Note`
					where name in (
						'DN21024792','DN21060026','DN21060027','DN21094615','DN21083280','DN21083281',
						'DN21013043','DN21013044','DN21023401','DN21023402','DN21023837',
						'DN21030203','DN21030204','DN21030528','DN21030491','DN21030492','DN21030754','DN21030755','DN21030756',
						'DN21030758','DN21030707','DN21032846','DN21032845','DN21032844','DN21032843','DN21032842','DN21032841',
						'DN21032837','DN21032840','DN21032836','DN21032835','DN21033840','DN21037736','DN21037735','DN21037734',
						'DN21037733','DN21037732','DN21037730','DN21037729','DN21037727','DN21037725','DN21037723','DN21038118',
						'DN21042634','DN21042602','DN21042595','DN21042627','DN21042628','DN21042629','DN21042630','DN21042632',
						'DN21042639','DN21042598','DN21042599','DN21054729','DN21054730'
					)
					order by posting_date
				""", as_dict=True)
	counter = 0
	for i in li:
		counter += 1
		doc = frappe.get_doc("Delivery Note", i.docname)
		print(counter, i.docname, doc.docstatus)
		if not debug and doc.docstatus == 0:
			try:
				doc.submit()
				print('Submitted...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()

def submit_prd_20220119(debug=1):
	li = frappe.db.sql("""select 'Production' as doctype, name as docname
					from `tabProduction`
					where name in (	
						'PRO210300566','PRO210500532','PRO210500534','PRO210500535','PRO210500536','PRO210500537','PRO210500531','PRO210900312',
						'PRO210800719','PRO210800720','PRO210800721','PRO210800722','PRO211000260','PRO210901158','PRO211201883','PRO211201875',
						'PRO211100437','PRO211100511','PRO211202456','PRO211202458','PRO220100537','PRO211202459','PRO211201380','PRO211201367',
						'PRO211201353','PRO211201352','PRO211201350','PRO211201349','PRO211201336','PRO211201335','PRO211201330','PRO211201328',
						'PRO211201325','PRO211201322','PRO211201321','PRO211201320','PRO211201316','PRO211201309','PRO211201308','PRO211201306',
						'PRO211201304','PRO211201302','PRO211201300','PRO211201296','PRO211201295','PRO211201288','PRO211201285','PRO211201284',
						'PRO211201283','PRO211201280','PRO211201279','PRO211201278','PRO211201276','PRO211201275','PRO220100536','PRO220100538',
						'PRO211202186-1')
					order by posting_date
				""", as_dict=True)
	counter = 0
	for i in li:
		counter += 1
		doc = frappe.get_doc("Production", i.docname)
		print(counter, i.docname, doc.docstatus)
		if not debug and doc.docstatus == 0:
			try:
				doc.submit()
				print('Submitted...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()

# created by SHIV on 2022/01/17
# list for submission mailed by Jamyang, NRDCL
def submit_dn_20220117(debug=1):
	li = frappe.db.sql("""select 'Delivery Note' as doctype, name as docname
					from `tabDelivery Note`
					where name in (
						'DN21129230', 'DN21129290', 'DN21129295', 'DN21129304', 'DN21129313', 'DN21129321', 'DN21129349',
						'DN21129351', 'DN21129354', 'DN21129360', 'DN21129374', 'DN21129387', 'DN21129392', 'DN21129398',
						'DN21129406', 'DN21129418', 'DN21129421', 'DN21129426', 'DN21129429', 'DN21129434', 'DN21129435',
						'DN21013043', 'DN21013044', 'DN21023401', 'DN21023402', 'DN21023837', 'DN21030203', 'DN21030204',
						'DN21030528', 'DN21030491', 'DN21030492', 'DN21030754', 'DN21030755', 'DN21030756', 'DN21030758',
						'DN21030707', 'DN21032846', 'DN21032845', 'DN21032844', 'DN21032843', 'DN21032842', 'DN21032841',
						'DN21032837', 'DN21032840', 'DN21032836', 'DN21032835', 'DN21033840', 'DN21037736', 'DN21037735',
						'DN21037734', 'DN21037733', 'DN21037732', 'DN21037730', 'DN21037729', 'DN21037727', 'DN21037725',
						'DN21037723', 'DN21038118', 'DN21042634', 'DN21042602', 'DN21042595', 'DN21042627', 'DN21042628',
						'DN21042629', 'DN21042630', 'DN21042632', 'DN21042639', 'DN21042598', 'DN21042599', 'DN21054729',
						'DN21054730', 'DN21024792', 'DN21060026', 'DN21060027', 'DN21094615', 'DN21083280', 'DN21083281'
					)
					order by posting_date
				""", as_dict=True)
	counter = 0
	for i in li:
		counter += 1
		doc = frappe.get_doc("Delivery Note", i.docname)
		print(counter, i.docname, doc.docstatus)
		if not debug and doc.docstatus == 0:
			try:
				doc.submit()
				print('Submitted...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()

def submit_prd_20220117(debug=1):
	li = frappe.db.sql("""select 'Production' as doctype, name as docname
					from `tabProduction`
					where name in (	'PRO220100482', 'PRO220100473', 'PRO220100465', 'PRO220100463', 'PRO220100411',
									'PRO210500105', 'PRO210600501', 'PRO220100526')
					order by posting_date
				""", as_dict=True)
	counter = 0
	for i in li:
		counter += 1
		doc = frappe.get_doc("Production", i.docname)
		print(counter, i.docname, doc.docstatus)
		if not debug and doc.docstatus == 0:
			try:
				doc.submit()
				print('Submitted...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()


def copy_party_to_consolidation():
	for d in frappe.db.sql('''
						   select voucher_no, account, name,consolidation_party
						   from `tabGL Entry` where voucher_type = 'Purchase Invoice' and (consolidation_party is null or consolidation_party ='')
						   ''',as_dict=True):
		exp_acc = ''
		if not d.consolidation_party:
			if d.account == 'Stock received but Not billed - CDCL':
				item_code = frappe.db.get_value('Purchase Invoice Item',{'parent':d.voucher_no},['item_code'])
				exp_acc = frappe.db.get_value('Item',item_code,['expense_account'])
				# print('item code : '+ item_code + ' acc : '+exp_acc)
			party = frappe.db.get_value('Purchase Invoice',d.voucher_no,['supplier'])
			print('name : '+ d.name +'party : '+party)
			frappe.db.sql('''
						update `tabGL Entry` set consolidation_party_type = 'Supplier', 
						consolidation_party = "{}",
						exact_expense_acc = "{}"
						where name = "{}"
						'''.format(party,exp_acc,d.name))
						
def submit_sr():
	srl = ['SR/000164']
	for a in srl:
		sr = frappe.get_doc("Stock Reconciliation", a)
		sr.cancel()
		print(a)

def save_ss():
	ss_list = frappe.db.sql("""
		select name from `tabSalary Structure` where is_active = 'Yes'
	""", as_dict = 1)
	for a in ss_list:
		doc = frappe.get_doc("Salary Structure", a.name)
		doc.save(ignore_permissions = 1)
		print(a.name)
#Added by Kinley Dorji to update sle if item was not ticked maintain stock. Please don't remove
# def update_sle():
# 	pr_list = frappe.db.sql("""
# 		 select pri.warehouse, pr.company, pr.name as parent_doc, pri.item_code, pri.stock_uom, pri.name, pri.qty, pr.posting_date, pr.posting_time, pri.rate from `tabPurchase Receipt Item` pri, `tabPurchase Receipt` pr where pr.name = pri.parent and pri.item_code = '500855' and pr.posting_date > '2021-01-01'
# 	""", as_dict=1)

# 	for a in pr_list:
# 		fiscal_year = str(a.posting_date).split("-")[0]
# 		sle = frappe.new_doc("Stock Ledger Entry")
# 		sle.item_code = a.item_code
# 		sle.warehouse = str(a.warehouse)
# 		sle.posting_date = a.posting_date
# 		sle.posting_time = a.posting_time
# 		sle.voucher_type = 'Purchase Receipt'
# 		sle.voucher_no = a.parent_doc
# 		sle.voucher_detail_no = a.name
# 		sle.actual_qty = a.qty
# 		sle.incoming_rate = a.rate
# 		sle.stock_uom = a.stock_uom
# 		sle.qty_after_transaction = a.qty
# 		sle.valuation_rate = a.rate
# 		sle.stock_value = a.rate
# 		sle.stock_value_difference = a.rate
# 		sle.company = a.company
# 		sle.fiscal_year = fiscal_year
# 		sle.save(ignore_permissions=True)
# 		print(a.item_code)





# def update_creator():
# 	mr_list = frappe.db.sql("select owner, name from `tabMaterial Request` where docstatus != 2 and owner != 'Administrator' and (creator is NULL or creator = '')",as_dict=True)
# 	if mr_list:
# 		for a in mr_list:
# 			print(a.owner)
# 			if a.owner != "Administrator":
# 				owner_id = frappe.db.get_value("Employee",{"user_id":a.owner},"name")
# 				owner_name = frappe.db.get_value("Employee",owner_id,"employee_name")
# 				doc = frappe.get_doc("Material Request", a.name)
# 				doc.creator = owner_id
# 				doc.creator_name = owner_name
# 				doc.save(ignore_permissions=True)
# 			print(a.name)

def update_creator():
	ss_list = frappe.db.sql("select name from `tabSalary Structure` where docstatus != 2 and is_active = 'Yes'",as_dict=True)
	if ss_list:
		for a in ss_list:
			ss = frappe.get_doc("Salary Structure", a.name)
			ss.save(ignore_permissions=True)
			print(a.name)


def create_dp_ut():
	for b in frappe.db.sql("""select name, branch, cost_center, posting_date, expense_account
							FROM `tabUtility Bill`
							Where (direct_payment ='' or direct_payment is NULL) 
							and name= 'CN202107120003'""", as_dict=True):
		doc = frappe.new_doc("Direct Payment")
		doc.branch = b.branch
		doc.cost_center = b.cost_center
		doc.posting_date = b.posting_date
		doc.payment_type = "Payment"
		doc.credit_account = b.expense_account
		doc.utility_bill = str(b.name)
		doc.remarks = "Utility Bill Payment " + str(b.name)
		doc.status = "Completed"
		doc.business_activity = "Common"
		count_child = 0
		for a in frappe.db.sql("""select payment_status, create_direct_payment, party, debit_account, invoice_amount, invoice_date, tds_applicable, invoice_amount, tds_amount, net_amount
							from `tabUtility Bill Item`
							where parent = '{}'""".format(b.name), as_dict=True):
			if a.create_direct_payment:
				print(a.invoice_amount, a.payment_status)
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
				print(count_child)
		if count_child > 0:
			doc.submit()
		if doc.name:
			#self.db_set("direct_payment", doc.name)
			frappe.db.set_value("Utility Bill", b.name, "direct_payment", doc.name)
			frappe.msgprint("Direct Payment created and submitted for this Utility Bill")

def update_dp():
	i = 0
	for a in frappe.db.sql("select debit_account, credit_account, payment_type, name, invoice_no, invoice_date from `tabDirect Payment`", as_dict=True):
		if a.payment_type == "Payment":
			if a.debit_account:
				account = a.debit_account
				frappe.db.sql("update `tabDirect Payment Item` set account = '{}',  invoice_date='{}', docstatus = 1 where parent = '{}'".format(account, a.invoice_date, a.name))
		else:
			if a.credit_account:
				account = a.credit_account
				frappe.db.sql("update `tabDirect Payment Item` set account = '{}',  invoice_date='{}', docstatus = 1 where parent = '{}'".format(account, a.invoice_date, a.name))
		frappe.db.commit()
		i += 1
		print(str(a.name) + " and Count : " + str(i))

def ss_from_emp():
	for a in frappe.db.sql("select name, employee_group, employee_subgroup from `tabEmployee` where earlier_id like 'WCCL%'", as_dict=True):
		frappe.db.sql("Update `tabSalary Structure` set employee_group = '{}' where employee ='{}' and is_active = 'Yes'".format(a.employee_group, a.name))
		#frappe.db.sql("Update `tabSalary Structure` set employee_grade = '{}' where employee ='{}' and is_active = 'Yes'".format(a.employee_subgroup, a.name))
		print(str(a.name) + " and " + str(a.employee_group))



def update_customer_order_dn():
	for a in frappe.db.sql("""select d.name, i.against_sales_order, (select customer_order from `tabSales Order` where name = i.against_sales_order) as customer_order from `tabDelivery Note` d, `tabDelivery Note Item` i where d.name = i.parent and d.customer_order is NULL and d.posting_date between '2020-09-14' and '2020-09-17'  and exists (select 1 from `tabSales Order` s where s.name = i.against_sales_order and s.customer_order is not NULL) and d.docstatus = 1""", as_dict=True):
		
		frappe.db.sql("update `tabDelivery Note` set customer_order = '{0}' where name = '{1}'".format(a.customer_order, a.name))

def create_delivery_confirmation():
	i =1
	for a in frappe.db.sql(""" select d.branch, d.name, d.vehicle, d.drivers_name, d.customer, d.creation, d.contact_no, 
				(select customer_order from `tabSales Order` where name = i.against_sales_order) as customer_order,
				(select sum(qty) from `tabDelivery Note Item` where parent = d.name) as total_qty
				from `tabDelivery Note` d, `tabDelivery Note Item` i 
				where d.name = i.parent and d.customer_order is NULL and d.posting_date between '2020-09-14' and '2020-09-17'  
				and not exists(select 1 from `tabDelivery Confirmation` c where c.delivery_note = d.name) 
				and exists (select 1 from `tabSales Order` s where s.name = i.against_sales_order and s.customer_order is not NULL) 
				and d.docstatus = 1;
			""", as_dict=True):
		transport_mode, customer_user = frappe.db.get_value("Customer Order", a.customer_order, ["transport_mode", "user"])
		# Create Delivery Confirmation document
		dc_doc = frappe.new_doc("Delivery Confirmation")
		dc_doc.branch = a.branch
		dc_doc.confirmation_status = "In Transit"
		dc_doc.exit_date_time = a.creation
		dc_doc.delivery_note = a.name
		dc_doc.user = customer_user
		dc_doc.customer = a.customer
		dc_doc.vehicle = a.vehicle
		dc_doc.drivers_name = a.drivers_name
		dc_doc.contact_no = a.contact_no
		dc_doc.customer_order = a.customer_order
		dc_doc.transport_mode = transport_mode
		dc_doc.qty = a.total_qty
		dc_doc.save(ignore_permissions=True)
		dc_doc.submit()

		
		print("count: " + str(a.total_qty) + "Branch : " + str(a.branch) +"mode: " + str(transport_mode) + " , user : " + str(customer_user))
		i=i+1

def update_ss():
	for a in frappe.db.sql(" select name from `tabSalary Structure` where is_active = 'Yes'", as_dict = 1):
		print (a.name)
		doc = frappe.get_doc("Salary Structure", a.name)
		doc.save(ignore_permissions = True)
		


def update_royalty():
	for a in frappe.db.sql("select docstatus, name, po_no from `tabSales Order` where po_no in (select name from `tabProduct Requisition` where supply_rate = 'Concessional Royalty')", as_dict=True):
		frappe.db.sql("Update `tabSales Order` set supply_rate = 'Concessional Royalty' where name = '{0}'".format(a.name))

def update_leave_allocation():
	for a in frappe.db.sql("select name, carry_forwarded_leaves, total_leaves_allocated, employee, leave_encashment, encashed_days from `tabLeave Allocation` where from_date = '2020-01-01' and to_date = '2020-12-31' and docstatus = 1", as_dict=True):
		if a.leave_encashment:
			frappe.db.sql("update `tabLeave Allocation` set carry_forwarded_leaves= '{0}', total_leaves_allocated = '{1}', leave_encashment= '{2}', encashed_days = '{3}' where employee = '{4}' and from_date='2019-12-01' and to_date = '2019-12-31'".format(a.carry_forwarded_leaves, a.total_leaves_allocated, a.leave_encashment, a.encashed_days, a.employee))
		frappe.db.sql("update `tabLeave Allocation` set docstatus = 2 where name = '{0}'".format(a.name))
				
def update_product_requisition1():
	for a in frappe.db.sql("select name, parent, item_code, balance, qty  from `tabProduct Requisition Item` where parent = 'PREQ191970'", as_dict=True):
		balance_qty = 0.00
		so_qty = 0.00
		for b in frappe.db.sql("select soi.qty as qty, soi.item_code as item_code from `tabSales Order` so inner join `tabSales Order Item` soi on so.name = soi.parent where so.docstatus = 1 and so.po_no = '{0}'".format(a.parent), as_dict=True):
			so_qty += flt(b.qty)
		balance_qty = flt(a.qty) - flt(so_qty)
		print("{0} and {1} and {2}".format(balance_qty, a.qty, so_qty))
		frappe.db.sql("update `tabProduct Requisition Item` set balance = '{0}' where name = '{1}'".format(balance_qty, a.name))

def update_product_requisition():
	for i in frappe.db.sql("select name from `tabProduct Requisition`", as_dict=True):
		balance_qty = 0.00
		so_qty = 0.00

		for b in frappe.db.sql("select soi.qty as qty, soi.item_code as item_code from `tabSales Order` so inner join `tabSales Order Item` soi on so.name = soi.parent where so.docstatus = 1 and so.po_no = '{0}'".format(a.parent), as_dict=True):
			so_qty += flt(b.qty)
		balance_qty = flt(a.qty) - flt(so_qty)
		frappe.db.sql("update `tabProduct Requisition Item` set balance = '{0}' where name = '{1}'".format(balance_qty, a.name))

def update_pr():
	for a in frappe.db.sql("select name from `tabProduct Requisition`", as_dict=True):
		delevery_flag = 1
		for b in frappe.db.sql("select name, parent, balance from `tabProduct Requisition Item` where parent = '{0}'".format(a.name), as_dict=True):
			if b.balance > 0:
				delevery_flag = 0
		if delevery_flag == 1:
			frappe.db.sql("update `tabProduct Requisition` set delivered = '1' where name = '{0}'".format(a.name))
	
def check_vehicle():
	listed_vehicle = []
	i = 0
	for a in frappe.db.sql("select name, vehicle_no, drivers_name, common_pool, self_arranged from `tabVehicle` where vehicle_status = 'Active' and (common_pool = 1 or self_arranged = 1) order by creation desc", as_dict=True):
		vehicle = a.vehicle_no
		cond = "upper(vehicle_no)"
		for x in [' ', '+', '-', '(', ')', '/', '#']:
				vehicle = vehicle.replace(x, '')
				cond = "replace({},'{}','')".format(cond, x)
		cond += " = '{}'".format(vehicle)
		if a.name not in listed_vehicle:
			#print(str(i), str(a.vehicle_no), str(a.common_pool), str(a.self_arranged))
			i += 1
			for b in frappe.db.sql("select name, vehicle_no, common_pool, self_arranged from `tabVehicle` where {} and name != '{}'".format(cond, a.name), as_dict=True):
				print(str(i), str(a.vehicle_no), str(a.common_pool), str(a.self_arranged), str(b.vehicle_no), str(b.common_pool), str(b.self_arranged))	
					

def update_lot_stock_entry():
	for a in frappe.db.sql("select name, parent, lot_list from `tabStock Entry Detail` where lot_list is not NULL and lot_list!='' and docstatus = 1", as_dict=1):
		frappe.db.sql("update `tabLot List` set stock_entry = '{0}' where name = '{1}'".format(a.parent, a.lot_list))
		print("Lot No. ===> {0}   Stock Entry ===> {1}".format(a.lot_list, a.parent))

def update_sws_contribution():
		for a in frappe.db.sql("select name, employee, employee_name, employee_grade from `tabSalary Structure`",  as_dict=1):
				sws_amount = frappe.db.get_value("Employee Grade", a.employee_grade, "sws_contribution")
				frappe.db.sql("update `tabSalary Detail` set amount = %s where parent = %s and salary_component = 'SWS'",(sws_amount, a.name))
				print("SS   ===> {0}   === {1} ==== {2} ===> {3}".format(a.name, a.employee_grade, sws_amount, a.employee))


def update_si_location():
		for a in frappe.db.sql("select name, location, delivery_note, parent from `tabSales Invoice Item`", as_dict=1):
				if not a.location:
						location_name = frappe.db.get_value("Delivery Note", a.delivery_note, "location")
						if location_name:
								frappe.db.sql("update `tabSales Invoice` set location = '{0}' where name = '{1}'".format(location_name, a.parent))
								frappe.db.sql("update `tabSales Invoice Item` set location = '{0}' where name = '{1}'".format(location_name, a.name))  


def update_production_reading():
	for a in frappe.db.sql("select i.name as name, i.reading as reading, i.item_group as item_group, i.item_sub_group as sub_group, p.production_type as production_type from `tabProduction` p, `tabProduction Product Item` i where p.name = i.parent and p.docstatus = 1", as_dict=1):
		if a.item_group != "Mineral Products" and a.production_type == "Adhoc":
			if a.sub_group == "Log":
				if a.reading < 5:
					reading_select = "5 ft Below (Log)"
				else:
					reading_select = "5 ft Above (Log)"
			elif a.sub_group == "Pole":
				if a.reading < 6:
					reading_select == "0 - 6 ft (Pole)"
				elif a.reading > 6 and a.reading < 12.1:
					reading_select == "6.1 - 12 ft (Pole)"
				elif a.reading > 12 and a.reading < 17.11:
					reading_select == "12.1 - 17.11 ft (Pole)"
				elif a.reading > 17.11:
					reading_select == "18 ft Above (Pole)"
			frappe.db.sql("Update `tabProduction Product Item` set reading_select = '{0}' where name = '{1}'".format(reading_select, a.name))
		if a.item_group == "Mineral Products":
			frappe.db.sql("Update `tabProduction Product Item` set reading_select = '' where name = '{0}'".format(a.name))
			print("Group :  {3} Name : {0} and reading_select : {1} reading : {2}".format(a.name, reading_select, a.reading, a.item_group))	
			
		 

def update_production_total_qty():
		for a in frappe.db.sql("select name from `tabProduction` where name ='PRO190700014'", as_dict=1):
				raw_item = frappe.db.sql("select sum(qty) as total_qty from `tabProduction Material Item` where parent = '{0}'".format(a.name), as_dict=True)
				production_item = frappe.db.sql("select sum(qty) as total_qty from `tabProduction Product Item` where parent = '{0}'".format(a.name), as_dict=True)
				if raw_item[0]['total_qty'] > 0:
						frappe.db.sql("update `tabProduction` set total_raw_material_qty = '{0}' where name = '{1}'".format( raw_item[0]['total_qty'], a.name))

				if production_item[0]['total_qty'] > 0:
						frappe.db.sql("update `tabProduction` set total_production_qty = '{0}' where name = '{1}'".format(production_item[0]['total_qty'], a.name))
				print("Production ===> {0}  === {1} ==== {2}".format(production_item[0]['total_qty'], a.name, production_item))


def replace_discount_to_additional_amount():
	for a in frappe.db.sql("select name, discount_or_cost_amount from `tabSales Order` where discount_or_cost_amount < 0", as_dict=1):
		add_amount = a.discount_or_cost_amount * -1
		#frappe.db.sql("update `tabSales Order` set additional_cost ='{0}' where name = '{1}'".format(add_amount, a.name))
		frappe.db.sql("update `tabSales Order` set discount_or_cost_amount = 0 where name = '{0}'".format( a.name))
		print("Updation of " + str(a.name) + " - " + str(a.discount_or_cost_amount) + " - " + str(add_amount))
		

def update_production_20190225():
		num = 0
		for a in frappe.db.sql("select a.name, a.posting_date from tabProduction a where docstatus = 1 and not exists (select 1 from  `tabGL Entry` b where b.voucher_no = a.name) order by a.posting_date asc, a.posting_time asc", as_dict=1):
				print(a.name)
				doc = frappe.get_doc("Production", a.name)
				doc.make_products_gl_entry()
				doc.make_raw_material_gl_entry()
				num = num + 1
				if num % 20 == 0:
						frappe.db.commit()
		frappe.db.commit()

def update_employment_status():
	for a in frappe.db.sql("select name, status from `tabEmployee`", as_dict=1):
		if a.status == "Active":
			frappe.db.sql("update `tabEmployee` set employment_status = 'In Service' where name = %s", a.name)
			print("Employment Status ===> Active")
		elif a.status == "Left":
			frappe.db.sql("update `tabEmployee` set employment_status = 'Left' where name = %s", a.name)
			print("Employment Status ==> Left")

def update_asset_1():
	for a in frappe.db.sql("select a.name, a.gross_purchase_amount as gross, b.accumulated_depreciation_amount as accu from tabAsset a, `tabDepreciation Schedule` b where a.name = b.parent and a.docstatus = 1 and a.value_after_depreciation = 0 and a.gross_purchase_amount != a.opening_accumulated_depreciation and b.schedule_date = '2019-03-31'", as_dict=1):
		print(a.name)
		frappe.db.sql("update tabAsset set value_after_depreciation = %s, status = 'Partially Depreciated', disable_depreciation = 0 where name = %s", (flt(a.gross) - flt(a.accu), a.name))

def update_asset_dtl():
	for a in frappe.db.sql("select name from `tabAsset` where docstatus = 1", as_dict=1):
		print("**** Activities are disabled, Remove # if you want to run the function *****")
		#frappe.db.sql("Delete from `tabJournal Entry` where name in (select parent from `tabJournal Entry Account` where reference_name = %s)", a.name)
		#frappe.db.sql("Delete from `tabJournal Entry Account` where reference_name = %s", a.name)
		#frappe.db.sql("Delete from `tabGL Entry` where against_voucher = %s", a.name)
		#frappe.db.sql("Delete from `tabAsset` where name = %s", a.name)
		#frappe.db.sql("Delete from `tabDepreciation Schedule` where parent = %s", a.name)

def update_production_20190225():
		num = 0
		for a in frappe.db.sql("select a.name, a.posting_date from tabProduction a where docstatus = 1 and not exists (select 1 from  `tabGL Entry` b where b.voucher_no = a.name) order by a.posting_date asc, a.posting_time asc", as_dict=1):
				print(a.name)
				doc = frappe.get_doc("Production", a.name)
				doc.make_products_gl_entry()
				doc.make_raw_material_gl_entry()
				num = num + 1
				if num % 20 == 0:
						frappe.db.commit()
		frappe.db.commit()



def update_mr():
	for a in frappe.db.sql("select name, owner from `tabMaterial Request`", as_dict=1):
		for b in frappe.db.sql("select employee_name, name from `tabEmployee` where user_id=%s", a.owner, as_dict=1):
			creator = b.name
			creator_name = b.employee_name
		frappe.db.sql("update `tabMaterial Request` set creator =%s, creator_name =%s where name = %s", (creator, creator_name, a.name))


def update_pol_1():
	for a in frappe.db.sql("select name from tabPOL where docstatus = 1", as_dict=1):
		frappe.db.sql("update tabPOL set docstatus = 0 where name = %s", a.name)
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
		frappe.db.sql("delete from `tabStock Ledger Entry` where voucher_no = %s", a.name)
		print(a.name)
		doc = frappe.get_doc("POL", a.name)
		doc.submit()

def update_si_today():
	for a in frappe.db.sql("select transportation_charges as tc, name from `tabSales Invoice` where docstatus = 0", as_dict=1):
		frappe.db.sql("update `tabSales Invoice` set transportation_charges = %s where name = %s", (round(flt(a.tc), 2), a.name))
		print(str(a.name) + " ==> " + str(round(flt(a.tc), 2)) + " :::: " + str(a.tc))

def update_si():
	for a in frappe.db.sql("select name, net_total, total_advance from `tabSales Invoice` where posting_date > '2018-12-31' and outstanding_amount > 0", as_dict=1):
		for b in frappe.db.sql("select name, credit, debit from `tabGL Entry` where voucher_no = %s and account != 'Advance from Customer - NRDCL'", a.name, as_dict=1):	
			if b.credit and b.credit != a.net_total and b.credit != a.total_advance:
				print(str(a.name) + " ==> " + str(a.net_total) + " >>> " + str(b.credit))
				frappe.db.sql("update `tabGL Entry` set credit = %s, credit_in_account_currency = %s where name = %s", (a.net_total, a.net_total, b.name))
			if b.debit and b.debit != a.net_total and b.debit != a.total_advance:
				frappe.db.sql("update `tabGL Entry` set debit = %s, debit_in_account_currency = %s where name = %s", (a.net_total, a.net_total, b.name))
				print(str(b.name) + " " + str(a.name) + " ==> " + str(a.net_total) + " >>> " + str(b.debit))
				#frappe.db.sql("")

def update_dn():
	for a in frappe.db.sql("select b.parent, b.name, a.transportation_rate as r, a.total_distance as d, b.qty, b.rate from `tabDelivery Note` a, `tabDelivery Note Item` b where a.name = b.parent and a.transportation_charges > 0 and a.docstatus != 2", as_dict=1):
		nr = flt(a.r) * flt(a.d)
		net = nr + flt(a.rate)
		nt = flt(net) * flt(a.qty)
		print(str(a.parent) + " ==> " + str(net) + " >>> " + str(nt))
		frappe.db.sql("update `tabDelivery Note Item` set net_rate = %s, net_amount = %s, base_net_rate = %s, base_net_amount = %s where name = %s", (net, nt, net, nt, a.name))


	"""for a in frappe.db.sql("select a.name, a.transportation_charges as tc, a.total from `tabDelivery Note` a where a.transportation_charges > 0 and a.docstatus != 2", as_dict=1):
		nt = flt(a.tc) + flt(a.total)
		print(str(a.name) + " ==> " + str(nt))
		in_word = frappe.utils.money_in_words(nt)
		frappe.db.sql("update `tabDelivery Note` set net_total = %s, grand_total = %s, in_words = %s where name = %s", (nt, nt, in_word, a.name))	

	for a in frappe.db.sql("select a.discount_or_cost_amount as dc, a.branch, a.name, sum(b.qty) as qty, b.against_sales_order as so from `tabDelivery Note` a, `tabDelivery Note Item` b where a.name = b.parent and a.transportation_charges > 0 and a.docstatus != 2 group by a.name", as_dict=1):
		d = frappe.get_doc("Sales Order", a.so).total_distance
		c = flt(d) * flt(a.qty) * 13.23
		print(str(a.name) + " ==> " + str(c))
		tdc = flt(a.dc) - flt(c)
		frappe.db.sql("update `tabDelivery Note` set transportation_rate = %s, total_quantity = %s, total_distance = %s, transportation_charges = %s, discount_amount = %s where name = %s", (13.23, flt(a.qty), flt(round(d, 2)), flt(c), flt(tdc),  a.name))"""

def update_consumed_budget_direct_payment():
		ml = frappe.db.sql("select p.name as name, p.posting_date as posting_date, p.cost_center as cost_center, p.debit_account as budget_account, p.amount as amount  from `tabDirect Payment` p where p.payment_type='payment' and p.name not in (select po_no from `tabConsumed Budget`)", as_dict=1)
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


def update_so():
	for a in frappe.db.sql("select a.branch, a.name, a.transportation_charges as tc, sum(b.qty) as qty from `tabSales Order` a, `tabSales Order Item` b where a.name = b.parent and a.transportation_charges > 0 and a.docstatus != 2 group by a.name", as_dict=1):
		distance = flt(a.tc) / (13.23 * flt(a.qty))
		print(str(a.name) + " ==> " + str(distance))
		frappe.db.sql("update `tabSales Order` set transportation_rate = %s, total_quantity = %s, total_distance = %s where name = %s", (13.23, flt(a.qty), flt(round(distance, 2)), a.name))

#
def update_equip():
	for a in frappe.db.sql("select name, hsd_type from tabEquipment where hsd_type is not null", as_dict=1):
		print (a.name, a.hsd_type)
		frappe.db.sql("update tabEquipment set item_name = (select item_name from tabItem where name = '{0}') where name = '{1}'".format(a.hsd_type, a.name))

def populate_wh_branch():
	counter = 0
	for t in frappe.db.sql("select name, branch from tabWarehouse", as_dict=1):
		counter += 1
		print (t.branch, t.name)
		doc = frappe.get_doc("Warehouse", t.name)
		row = doc.append("items",{})
		row.branch = t.branch
		row.save()

def insert_vehicle():
	doc = frappe.get_doc("Customer Order", "ORDR201000062")
	for a in frappe.db.sql("select name as vehicle, drivers_name, contact_no, driver_cid, vehicle_capacity, '2' as noof_truck_load, '5' as quantity from `tabVehicle` where name in ('BP-1A-2920','BP-1A-3892','BP-1A-4042')", as_dict=True):
		row = doc.append("vehicles", {
				"vehicle": a.vehicle,
				"drivers_name": a.drivers_name,
				"vehicle_capacity": a.vehicle_capacity,
				"contact_no": a.contact_no,
				"driver_cid": a.driver_cid,
				"noof_truck_load": a.noof_truck_load,
				"quantity": a.quantity
			})
		row.save(ignore_permissions = True)


def update_customer1():
		cus = frappe.db.sql("select name from tabCustomer", as_dict=1)
		count = 0
		for a in cus:
			#print a.name
			count += 1
			print (a.name, count)
			doc = frappe.get_doc("Customer", a.name)
			doc.customer_id = count
			doc.save()
			frappe.db.commit()


def update_emp():
	for a in frappe.db.sql("select name from tabEmployee where docstatus = 0", as_dict=1):
		print(str(a.name))
		doc = frappe.get_doc("Employee", a.name)
		doc.user_id = doc.company_email
		doc.save()

def update_se_ig():
	for a in frappe.db.sql("select name, item_code from `tabStock Entry Detail`", as_dict=1):
		item = frappe.get_doc("Item", a.item_code)
		frappe.db.sql("update `tabStock Entry Detail` set item_group = %s where name = %s", (item.item_group, a.name))

def update_production():
	for a in frappe.db.sql("select name from `tabProduction`", as_dict=1):
		doc = frappe.get_doc("Production", a.name)
		doc.delete_production_entry()
		doc.make_production_entry()
		"""for item in doc.items:
			item_name, item_group, item_sub_group, timber_species = frappe.db.get_value("Item", item.item_code, ["item_name", "item_group", "item_sub_group", "species"])
			i = frappe.get_doc("Production Product Item", item.name)
			i.db_set("item_name", item_name)
			i.db_set("item_group", item_group)
			i.db_set("item_sub_group", item_sub_group)
			i.db_set("timber_species", timber_species)
		"""

def update_mech():
	ml = frappe.db.sql("select name from `tabMechanical Payment` where docstatus = 1 and payment_for is null", as_dict=1)
	for a in ml:
		doc = frappe.get_doc("Mechanical Payment", a.name)
		print(doc.name)
		frappe.db.sql("update `tabMechanical Payment` set payment_for = %s where name = %s", (doc.ref_doc, doc.name))
		dc = frappe.new_doc("Mechanical Payment Item")
		dc.reference_type = doc.ref_doc
		dc.reference_name = doc.ref_no
		dc.outstanding_amount = doc.receivable_amount
		dc.allocated_amount = doc.receivable_amount
		dc.parent = doc.name
		dc.parenttype = "Mechanical Payment"
		dc.parentfield = "items"
		dc.owner = doc.owner
		dc.creation = doc.creation
		dc.modified_by = doc.modified_by
		dc.modified = doc.modified
		dc.docstatus = doc.docstatus
		dc.submit()

def update_equipment():
		els = frappe.db.sql("select name from tabEquipment", as_dict=1)
		for a in els:
				print (a.name)
				doc = frappe.get_doc("Equipment", a.name)
				doc.save()
				frappe.db.commit()

def adjust_advance_balance():
	advances = frappe.db.sql("select name from `tabHire Charge Invoice`", as_dict=1)
	for a in advances:
		doc = frappe.get_doc("Hire Charge Invoice", a.name)
		total = 0
		for b in doc.advances:
			total = flt(total) + flt(b.balance_advance_amount)
		if total != 0:
			print(str(a.name) + " ==> " + str(total))
			frappe.db.sql("update `tabHire Charge Invoice` set balance_advance_amount = %s where name = %s", (total, a.name))

def hire_balance_advance():
	advs = frappe.db.sql("select parent, name, actual_advance_amount, allocated_amount from `tabHire Invoice Advance`", as_dict=1)
	for a in advs:
		bal = flt(a.actual_advance_amount) - flt(a.allocated_amount)
		print(a.parent)
		frappe.db.sql("update `tabHire Invoice Advance` set balance_advance_amount = %s where name = %s", (bal, a.name))

def update_vl():
	vls = frappe.db.sql("select name, ehf_name from `tabVehicle Logbook`", as_dict=1)
	for a in vls:
		doc = frappe.get_doc("Equipment Hiring Form", a.ehf_name)
		print(doc.name)
		frappe.db.sql("update `tabVehicle Logbook` set customer_type = %s, customer = %s where name = %s", (doc.private, doc.customer, a.name))

def update_hcp():
	hcps = frappe.db.sql("select name from `tabHire Charge Parameter`", as_dict=1)
	for a in hcps:
		doc = frappe.get_doc("Hire Charge Parameter", a.name)
		doc.save()

def update_pol_time():
	pols = frappe.db.sql("select name, reference_name, reference_type from `tabPOL Entry` where reference_name is not null and reference_type is not null", as_dict=1)
	for a in pols:
		if a.reference_type and a.reference_name:
			doc = frappe.get_doc(a.reference_type, a.reference_name)
			print(a.name)
			frappe.db.sql("update `tabPOL Entry` set posting_time = %s where name = %s", (str(doc.posting_time), a.name))

def update_table():
		tables = frappe.db.sql("SELECT table_name FROM information_schema.tables where table_schema='4915427b5860138f'", as_dict=True)
		for a in tables:
				try:    
						frappe.db.sql("ALTER TABLE `"+str(a.table_name)+"` ADD COLUMN submitted_by varchar(140)")
						print(a.table_name)
				except: 
						pass

def adjust_asset_gl():
	#ams = frappe.db.sql("select name from `tabAsset Movement` where docstatus = 1 ", as_dict=True)
	ams = frappe.db.sql("select name from `tabAsset Movement` where docstatus = 1 and posting_date > '2017-12-31'", as_dict=True)
	cc = 0
	for a in ams:
		doc = frappe.get_doc("Asset Movement", a.name)
		if ((doc.target_cost_center and doc.target_cost_center != doc.current_cost_center) or (doc.target_custodian and doc.current_cost_center != doc.target_custodian_cost_center)):
			cc = cc + 1
			if doc.target_cost_center:
				to_cc = doc.target_cost_center
			else:
				to_cc = doc.target_custodian_cost_center
			do_gl_adjustment(doc, doc.asset, doc.posting_date, doc.name, doc.current_cost_center, to_cc)

	bam = frappe.db.sql("select name from `tabBulk Asset Transfer` where docstatus = 1 and posting_date > '2017-12-31'", as_dict=1)
	for a in bam:
		doc = frappe.get_doc("Bulk Asset Transfer", a.name)
		for b in doc.items:
			if b.cost_center != doc.custodian_cost_center:
				cc = cc + 1
				do_gl_adjustment(doc, str(b.asset_code), doc.posting_date, doc.name, b.cost_center, doc.custodian_cost_center)

	print(cc)

def do_gl_adjustment(self, asset_code, posting_date, name, from_cc, to_cc):
	asset = frappe.get_doc("Asset", asset_code)
	deps = frappe.db.sql("select accumulated_depreciation_amount from `tabDepreciation Schedule` where parent = %s and schedule_date <= %s order by schedule_date desc limit 1", (asset_code, posting_date),  as_dict=1)
	if deps:
		accumulated_dep = deps[0].accumulated_depreciation_amount
	else:
		accumulated_dep = asset.opening_accumulated_depreciation
	
	ic_amount = flt(asset.gross_purchase_amount) - flt(accumulated_dep)

	accumulated_dep_account = frappe.db.sql("select accumulated_depreciation_account from `tabAsset Category Account` where parent = %s", asset.asset_category, as_dict=True)[0].accumulated_depreciation_account
	ic_account = frappe.db.get_single_value("Accounts Settings", "intra_company_account")
	if not ic_account:
		frappe.throw("Setup Intra Company Accounts under Accounts Settings")

	from erpnext.accounts.general_ledger import make_gl_entries
	from erpnext.custom_utils import prepare_gl

	gl_entries = []
	gl_entries.append(
		prepare_gl(self, {
			   "account":  asset.asset_account,
			   "credit": asset.gross_purchase_amount,
			   "credit_in_account_currency": asset.gross_purchase_amount,
			   "against_voucher": asset.name,
			   "against_voucher_type": "Asset",
			   "cost_center": from_cc,
		})
	)
	gl_entries.append(
		prepare_gl(self, {
			   "account":  asset.asset_account,
			   "debit": asset.gross_purchase_amount,
			   "debit_in_account_currency": asset.gross_purchase_amount,
			   "against_voucher": asset.name,
			   "against_voucher_type": "Asset",
			   "cost_center": to_cc,
		})
	)

	if accumulated_dep:
		gl_entries.append(
			prepare_gl(self, {
				   "account": accumulated_dep_account,
				   "debit": accumulated_dep,
				   "debit_in_account_currency": accumulated_dep,
				   "against_voucher": asset.name,
				   "against_voucher_type": "Asset",
				   "cost_center": from_cc,
			})
		)
		gl_entries.append(
			prepare_gl(self, {
				   "account": accumulated_dep_account,
				   "credit": accumulated_dep,
				   "credit_in_account_currency": accumulated_dep,
				   "against_voucher": asset.name,
				   "against_voucher_type": "Asset",
				   "cost_center": to_cc,
			})
		)

	if ic_amount:
		allow_inter_company_transaction = frappe.db.get_single_value("Accounts Settings", "auto_accounting_for_inter_company")
		if allow_inter_company_transaction:
			ic_account = frappe.db.get_single_value("Accounts Settings", "intra_company_account")
			if not ic_account:
				frappe.throw("Setup Intra-Company Account in Accounts Settings")
			gl_entries.append(
				prepare_gl(self, {
					   "account": ic_account,
					   "debit": ic_amount,
					   "debit_in_account_currency": ic_amount,
					   "against_voucher": asset.name,
					   "against_voucher_type": "Asset",
					   "cost_center": from_cc,
				})
			)
			gl_entries.append(
				prepare_gl(self, {
					   "account": ic_account,
					   "credit": ic_amount,
					   "credit_in_account_currency": ic_amount,
					   "against_voucher": asset.name,
					   "against_voucher_type": "Asset",
					   "cost_center": to_cc,
				})
			)
	print(asset.name)
	make_gl_entries(gl_entries, cancel=0, update_outstanding="No", merge_entries=False)

def branch_access_list():
	bl = frappe.db.sql("select count(1) as count, parent from tabDefaultValue where defkey = 'Branch' group by parent having count > 1", as_dict=True)
	for a in bl:
		ab = frappe.db.sql("select 1 from `tabAssign Branch` where user = %s", a.parent, as_dict=1)
		if not ab:
			print(a)

def get_asset_list():
	li = frappe.db.sql("select a.gross_purchase_amount, a.name, a.asset_account, b.fixed_asset_account from tabAsset a, `tabAsset Category Account` b where a.asset_category = b.parent and a.asset_account != b.fixed_asset_account", as_dict=True)
	for a in li:
		print(a.name + "  :  " + a.asset_account + " ==> " + a.fixed_asset_account + "   ::: " + str(a.gross_purchase_amount))

	assets = frappe.db.sql("select a.name, a.asset_category, b.account from tabAsset a, `tabJournal Entry Account` b where b.debit > 0 and a.name = b.reference_name and (b.account not like '%Depreciation%' and b.account not like '%Amortization%')", as_dict=True)
	for a in assets:
		as_cat = frappe.db.sql("select fixed_asset_account from `tabAsset Category Account` where parent = %s", a.asset_category, as_dict=True)
		entry = as_cat[0].fixed_asset_account
		if a.account != entry:
			print(a.name + "  :  " + a.account + " ==> " + entry)
	

def move_bulk_asset_movement():
	ams = frappe.db.sql("select name, creation from `tabBulk Asset Transfer`", as_dict=True)
	for a in ams:
		print(a.name + " : " + str(getdate(a.creation)))
		frappe.db.sql("update `tabBulk Asset Transfer` set posting_date = %s, company = %s where name = %s", (str(getdate(a.creation)), "Construction Development Corporation Ltd", a.name))

def move_asset_movement():
	ams = frappe.db.sql("select name, transaction_date, reason from `tabAsset Movement`", as_dict=True)
	for a in ams:
		frappe.db.sql("update `tabAsset Movement` set posting_date = %s, remarks = %s where name = %s", (a.transaction_date, a.reason, a.name))

def adjust_km_consumption():
	vlogs = frappe.db.sql("select name, ys_km, distance_km, consumption_km from `tabVehicle Logbook` where consumption_km = distance_km * ys_km and consumption_km != 0", as_dict=True)
	for a in vlogs:
		#total = flt(a.distance_km) / flt(a.ys_km)
		#frappe.db.sql("update `tabVehicle Logbook` set consumption_km = %s, consumption = %s where name = %s", (total, total, a.name))
		print(a.name)

def logbook_consumption_others():
	logs = frappe.db.sql("select l.name from `tabVehicle Logbook` l, `tabEquipment Hiring Form` e where l.ehf_name = e.name and e.private != 'CDCL' and l.rate_type = 'Without Fuel' and l.consumption > 0 and l.docstatus = 1 and l.from_date > '2018-03-31'", as_dict=True)
	for a in logs:
		print(a.name)

def logbook_cunsumption():
	logs = frappe.db.sql("select l.name, l.branch from `tabVehicle Logbook` l, `tabEquipment Hiring Form` e where l.ehf_name = e.name and e.private = 'CDCL' and l.consumption = 0 and l.docstatus = 1 and l.from_date > '2018-03-31'", as_dict=True)
	#logs = frappe.db.sql("select l.name, l.branch from `tabVehicle Logbook` l, `tabEquipment Hiring Form` e where l.ehf_name = e.name and e.private = 'CDCL' and l.consumption = 0 and l.docstatus = 1 ", as_dict=True)
	both = km = time = none = 0
	for a in logs:
		distance = hours = consump = 0
		log = frappe.get_doc("Vehicle Logbook", a.name)
		if not log.ys_km and not log.ys_hours:
			pass
		if log.total_work_time and log.distance_km:
			#print("Both: " + str(log.name))
			if log.ys_km and log.ys_hours:
				distance = log.distance_km / log.ys_km
				hours = log.total_work_time * log.ys_hours
			elif log.ys_km:
				distance = log.distance_km / log.ys_km
			elif log.ys_hours:
				hours = log.total_work_time * log.ys_hours
			else:
				distance = log.distance_km / log.ys_km
				hours = log.total_work_time * log.ys_hours
		elif log.total_work_time:
			hours = log.total_work_time * log.ys_hours
		elif log.distance_km:
			distance = log.distance_km / log.ys_km
		else:
			distance = log.distance_km / log.ys_km
			hours = log.total_work_time * log.ys_hours
		consump = log.other_consumption + hours + distance
		if distance > 0 and hours > 0:
			tp, mo = frappe.db.get_value("Equipment", log.equipment, ['equipment_type', 'equipment_model'])	
			if tp not in ['Jack Hammer', 'Rock Breaker']:
				print("BOTH: " + a.name + " : " + log.branch)
		elif distance > 0:
			frappe.db.sql("update `tabVehicle Logbook` set include_km = 1, consumption_km = %s, consumption = %s where name = %s", (distance, consump, log.name))
		elif hours > 0:
			frappe.db.sql("update `tabVehicle Logbook` set include_hour = 1, consumption_hours = %s, consumption = %s where name = %s", (hours, consump, log.name))
		else:
			tp, mo = frappe.db.get_value("Equipment", log.equipment, ['equipment_type', 'equipment_model'])	
			if tp not in ['Jack Hammer', 'Rock Breaker']:
				print("NONE: " + a.name + " : " + log.branch)

def check_double_pol():
	pols = frappe.db.sql("select p.name from tabPOL p, `tabJournal Entry` j where p.docstatus = 1 and p.jv is not null and j.docstatus = 1 and p.jv = j.name", as_dict=True)
	for a in pols:
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)

def set_cc_kilikhar():
	gls = frappe.db.sql("select a.advance_cost_center, b.name from `tabSales Invoice Advance` a, `tabGL Entry` b where a.docstatus = 1 and a.parent = b.voucher_no and a.advance_account = b.against", as_dict=True)
	for a in gls:
		frappe.db.sql("update `tabGL Entry` set cost_center = %s where name = %s", (a.advance_cost_center, a.name))
		print(a.name)

def set_operator_name():
	ops = frappe.db.sql("select parent, name, operator, employee_type from `tabEquipment Operator` where operator_name is null", as_dict=True)
	for a in ops:
		if a.employee_type == "Employee":
			name = frappe.db.get_value("Employee", a.operator, "employee_name")
		else:
			name = frappe.db.get_value("Muster Roll Employee", a.operator, "person_name")
		frappe.db.sql("update `tabEquipment Operator` set operator_name = %s where name = %s", (name, a.name))

def link_consumed_committed():
	con = frappe.db.sql("select name, pii_name from `tabConsumed Budget` where docstatus = 1", as_dict=True)
	for a in con:
		if a.pii_name:
			try:
				doc = frappe.get_doc("Purchase Invoice Item", a.pii_name)
				if doc:
					print(doc.po_detail)
					frappe.db.sql("update `tabConsumed Budget` set poi_name = %s where name = %s", (doc.po_detail, a.name))
			except:
				pass

def adjust_pol_journal():
	pols = frappe.db.sql("select name from tabPOL where docstatus = 1 and direct_consumption = 1 and posting_date > '2017-12-31'", as_dict=True)
	for a in pols:
		print(a.name)
		doc = frappe.get_doc("POL", a.name)
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
		doc.update_general_ledger(1)

def set_equipment_type():
	pols = frappe.db.sql("select name, equipment from tabPOL", as_dict=True)
	for a in pols:
		print(a.equipment)
		et = frappe.db.get_value("Equipment", a.equipment, "equipment_type")
		frappe.db.sql("update tabPOL set equipment_type = %s where name = %s", (et, a.name))	

def adjust_pol_entry_1():
	pol = frappe.get_doc("POL", "POL180500576")
	frappe.db.sql("delete from `tabPOL Entry` where reference_name = 'POL180500576'")
	pol.make_pol_entry()

def adjust_dc_pol():
	pols = frappe.db.sql("select p.name, p.qty, e.equipment_type, p.posting_date, p.equipment_warehouse from tabPOL p, tabEquipment e, `tabEquipment Type` et where p.equipment = e.name and e.equipment_type = et.name and direct_consumption = 0 and et.is_container = 0 and posting_date > '2018-03-31' and p.docstatus = 1 ", as_dict=True)
	for a in pols:
		if a.name in ['POL180500492', 'POL180500491', 'POL180500490', 'POL180500456']:
			print(str(a.name))
			frappe.db.sql("delete from `tabStock Ledger Entry` where voucher_no = %s", a.name)
			frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
			frappe.db.sql("update `tabPOL` set direct_consumption = 1 where name = %s", a.name)
			doc = frappe.get_doc("POL", a.name)
			doc.direct_consumption = 1
			doc.update_stock_ledger()
			doc.make_pol_entry()
			frappe.db.commit()
		else:	
			pass
			frappe.db.sql("delete from `tabStock Ledger Entry` where voucher_no = %s", a.name)
			frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
			frappe.db.sql("update `tabPOL` set direct_consumption = 1 where name = %s", a.name)
			doc = frappe.get_doc("POL", a.name)
			doc.direct_consumption = 1
			doc.update_stock_ledger()
			doc.make_pol_entry()
			frappe.db.commit()

def adjust_hsd_outstanding():
	ols = frappe.db.sql("select pol from `tabHSD Payment Item` where parent = 'HSDP1805002'", as_dict=True)
	for a in ols:
		print(a.pol)
		frappe.db.sql("update `tabPOL` set paid_amount = '' where name = %s", a.pol)

def update_asset():
	prs = frappe.db.sql("select name from `tabPurchase Receipt` where docstatus = 1", as_dict=True)
	for a in prs:
		print(a.name)
		doc = frappe.get_doc("Purchase Receipt", a.name)
		doc.delete_asset()
		doc.update_asset()

def make_status_entry():
	vls = frappe.db.sql("select name from `tabJob Card` where docstatus = 1", as_dict=True)
	for a in vls:
		print(str(a.name))
		doc = frappe.get_doc("Job Card", a.name)
		doc.update_reservation()

def make_pol_entry():
	pols = frappe.db.sql("select name from `tabIssue POL` where docstatus = 1", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
		doc = frappe.get_doc("Issue POL", a.name)
		doc.make_pol_entry()
	frappe.db.commit()

	pols = frappe.db.sql("select name from `tabPOL` where docstatus = 1 and pol_type != 'N/A'", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
		doc = frappe.get_doc("POL", a.name)
		doc.make_pol_entry() 
	frappe.db.commit()

	pols = frappe.db.sql("select name from `tabEquipment POL Transfer` where docstatus = 1", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
		doc = frappe.get_doc("Equipment POL Transfer", a.name)
		doc.adjust_consumed_pol() 
	frappe.db.commit()

def list_bb():
		num = 1
		for self in frappe.db.sql("select name, owned_by, equipment, branch, customer_branch from `tabBreak Down Report` where docstatus != 2", as_dict=True):
				if self.owned_by in ['CDCL', 'Own']:
								eb = frappe.db.get_value("Equipment", self.equipment, "branch")
								if self.owned_by == "Own" and not self.branch == eb:
										print("OWN: " + str(self.name) )
										num = num + 1
								if self.owned_by == "CDCL" and not self.customer_branch == eb:
										print("CDCL: " + str(self.name) )
										num = num + 1
		print(num)

def clean_br():
	brs = frappe.db.sql("select b.name from `tabBreak Down Report` b, `tabJob Card` j where b.job_card = j.name and j.docstatus = 2 and b.docstatus = 1", as_dict=True)
	for a in brs:
		frappe.db.sql("update `tabBreak Down Report` set job_card = '' where name = %s", a.name)

def pol_entry():
	pols = frappe.db.sql("select name from `tabIssue POL` where docstatus = 1", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
		doc = frappe.get_doc("Issue POL", a.name)
		doc.make_pol_entry()

def ipol_gl():
	pols = frappe.db.sql("select distinct p.name from `tabIssue POL` p, `tabGL Entry` g where p.docstatus = 1 and p.name = g.voucher_no", as_dict=True)
	for a in pols:
		valuation_rate = frappe.db.sql("select valuation_rate from `tabStock Ledger Entry` where voucher_no = %s limit 1", a.name, as_dict=True)
		print(str(a.name))
		if a.name not in ['IPOL180500272']:
			frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
			pol = frappe.get_doc("Issue POL", a.name)
			pol.update_stock_gl_ledger(1, 0, round(valuation_rate[0].valuation_rate, 2))

def asset_cc():
	assets = frappe.db.sql("select name from tabAsset where docstatus = 1", as_dict=True)
	for a in assets:
		doc = frappe.get_doc("Asset", a.name)
		doc.db_set("cost_center", frappe.db.get_value("Employee", doc.issued_to, "cost_center"))
		doc.db_set("branch", frappe.db.get_value("Employee", doc.issued_to, "branch"))

def adjust_ipol():
	pols = frappe.db.sql("select name from `tabIssue POL` where docstatus = 1 and cost_center = 'Construction of 132 KV D/C Transmission Line from Nikachhu to Mangdechhu - CDCL'", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
		pol = frappe.get_doc("Issue POL", a.name)
		pol.update_stock_gl_ledger(1, 0)

def adjust_pol():
	pols = frappe.db.sql("select name from tabPOL where fuelbook is not null and docstatus = 1 and cost_center = 'Construction of 132 KV D/C Transmission Line from Nikachhu to Mangdechhu - CDCL'", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
		pol = frappe.get_doc("POL", a.name)
		pol.update_general_ledger(1)

def migrate_pol_entry():
	pols = frappe.db.sql("select name from `tabEquipment POL Transfer` where docstatus = 1", as_dict=True)
	for a in pols:
		doc = frappe.get_doc("Equipment POL Transfer", a.name)
		print(a.name)
		if not doc.pol_type == "N/A":
			doc.adjust_consumed_pol()

def operators():
	ops = frappe.db.sql("select name from `tabEquipment Operator`", as_dict=True)
	for a in ops:
		doc = frappe.get_doc("Equipment Operator", a.name)
		if doc.employee_type == "Employee":
			name = frappe.db.get_value("Employee", doc.operator, "employee_name")
		if doc.employee_type == "Muster Roll Employee":
			name = frappe.db.get_value("Muster Roll Employee", doc.operator, "person_name")
		doc.db_set("operator_name", name)

def migrate_ipol():
		pols = frappe.db.sql("select name, pol_type from `tabIssue POL` where pol_type in ('Diesel', 'Petrol')", as_dict=True)
		for a in pols:
				print(a.name)
				doc = frappe.get_doc("Issue POL", a.name)
				if a.pol_type == "Diesel":
						doc.db_set("pol_type", '100452')
				else:
						doc.db_set("pol_type", '100699')
				item = frappe.get_doc("Item", doc.pol_type)
				doc.db_set("stock_uom" , item.stock_uom)
				doc.db_set("is_hsd_item" , item.is_hsd_item)
				doc.db_set("item_name", item.item_name)
				doc.db_set("posting_date", doc.date)
				doc.db_set("company", 'Construction Development Corporation Ltd')
				doc.db_set("posting_time", '17:13:36')
				doc.db_set("warehouse", get_branch_warehouse(doc.branch))
				doc.db_set("cost_center", get_branch_cc(doc.branch))

				for b in doc.items:
					d = frappe.get_doc("POL Issue Report Item", b.name)
					e = frappe.get_doc("Equipment", d.equipment)
					d.db_set("equipment_branch", e.branch)
					d.db_set("equipment_warehouse", get_branch_warehouse(e.branch))
					d.db_set("equipment_cost_center", get_branch_cc(e.branch))


def migrate_pol():
		pols = frappe.db.sql("select name, pol_type from `tabPOL` where pol_type in ('Diesel', 'Petrol')", as_dict=True)
		for a in pols:
				print(a.name)
				doc = frappe.get_doc("POL", a.name)
				if a.pol_type == "Diesel":
						doc.db_set("pol_type", '100452')
				else:
						doc.db_set("pol_type", '100699')
				item = frappe.get_doc("Item", doc.pol_type)
				doc.db_set("stock_uom" , item.stock_uom)
				doc.db_set("item_name", item.item_name)
				doc.db_set("posting_date", doc.date)
				doc.db_set("company", 'Construction Development Corporation Ltd')
				doc.db_set("posting_time", '17:13:36')
				if doc.book_type == "Common Fuel Book":
						doc.db_set("book_type", "Common")
				else:
						doc.db_set("book_type", "Own")

				doc.db_set("warehouse", get_branch_warehouse(doc.branch))
				eqp = frappe.get_doc("Equipment", doc.equipment)
				doc.db_set("equipment_category", eqp.equipment_category)
				doc.db_set("equipment_warehouse", get_branch_warehouse(doc.equipment_branch))
				doc.db_set("fuelbook", "")
				doc.db_set("fuelbook_branch", "")

def post_stock():
	doc = frappe.get_doc("Stock Reconciliation", "SR/000016")
	doc.update_stock_ledger()

def pass_ic_se():
	num = 0
	ses = frappe.db.sql("select name from `tabStock Entry` where purpose = 'Material Transfer' and docstatus = 1 and posting_date >= '2018-01-01'", as_dict=True)
	for a in ses:
			print(a.name)
			doc = frappe.get_doc("Stock Entry", a.name)
			frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
			doc.make_gl_entries()
	print("COMPLETED")

def test():
	from erpnext.custom_utils import round5
	print(round(10.33, 0))
	print(round(10.56, 0))

def cancel_mr_po():
	mrs = frappe.db.sql("select mr.name from `tabMaterial Request` mr where mr.transaction_date < '2018-01-01' and mr.status = 'Cancelled' and mr.workflow_state = 'Approved' and mr.per_ordered = 0 and not exists (select 1 from `tabPurchase Order Item` poi where poi.docstatus != 1 and poi.material_request = mr.name)", as_dict=True)
	for a in mrs:
		if a.name != 'MRSP18010012':
			doc = frappe.get_doc("Material Request", a.name)
			#doc.cancel()
			doc.db_set("workflow_state", "Cancelled")
			print(a.name)

def move_equipment():
	assets = frappe.db.sql("select name from `tabAsset Movement` where docstatus = 1", as_dict=True)
	for a in assets:
		doc = frappe.get_doc("Asset Movement", a.name)
		equipment = frappe.db.get_value("Equipment", {"asset_code": doc.asset}, "name")
		if equipment:
			e = frappe.get_doc("Equipment", equipment)
			if doc.target_custodian:
				branch = frappe.db.get_value("Employee", doc.target_custodian, "branch")
			if doc.target_cost_center:
				branch = frappe.db.get_value("Cost Center", doc.target_cost_center, "branch")
			print(str(equipment) + " : " + str(branch))
			e.db_set("branch", branch)

def cancel_mr():
	mrs = frappe.db.sql("select name from `tabMaterial Request` where docstatus = 2", as_dict=True)
	for a in mrs:
		print(a.name)
		doc = frappe.get_doc("Material Request", a.name)
		doc.db_set("status", "Cancelled")
		doc.db_set("workflow_state", "Cancelled")

def tds_cost_center():
	datas = frappe.db.sql("select a.name as gl, b.name as pi, b.tds_cost_center, b.posting_date from `tabGL Entry` a,`tabPurchase Invoice` b where a.voucher_no = b.name and b.tds_amount > 0 and account like 'Creditors-Other - CDCL' and cost_center is null group by a.name, b.name;", as_dict=True)
	for a in datas:
		doc = frappe.get_doc("GL Entry", a.gl)
		doc.db_set("cost_center", a.tds_cost_center)
		print(str(a.gl) + " ==> " + str(a.tds_cost_center))

def pe_cost_center():
	datas = frappe.db.sql("select pe.name, per.reference_name as pi from `tabPayment Entry Reference` per, `tabPayment Entry` pe where pe.name = per.parent and  pe.paid_to = 'Creditors-Other - CDCL' and pe.docstatus = 1 and pe.payment_type = 'Pay'  group by pe.name;", as_dict=True)
	for a in datas:
		gls = frappe.db.sql("select name from `tabGL Entry` where voucher_no = %s and account = 'Creditors-Other - CDCL' and cost_center is null", a.name, as_dict=True)
		for g in gls:
			doc = frappe.get_doc("GL Entry", g.name)
			cc = frappe.db.get_value("Purchase Invoice", doc.against_voucher, "buying_cost_center")
			if not cc:
				cc = "Pachu Zam Construction - CDCL"
			doc.db_set("cost_center", cc)
			print(str(a.pi) + " :: " + str(g.name) + " ==> " + str(a.name) + " >>> " + str(cc))

def adjust_asset():
		assets = frappe.db.sql("select name, company, branch, cost_center, asset_category, expected_value_after_useful_life, status from tabAsset", as_dict=True)
		for a in assets:
				dep = frappe.db.sql("select name, journal_entry from `tabDepreciation Schedule` where parent = %s and depreciation_amount > 0 order by schedule_date DESC limit 1", (a.name), as_dict=True)
				if dep:
						obj = frappe.get_doc("Depreciation Schedule", dep[0].name)
						if a.status == "Fully Depreciated" and flt(a.expected_value_after_useful_life) > 0:
								js = frappe.db.sql("select name, account, cost_center, credit_in_account_currency, debit_in_account_currency from `tabJournal Entry Account` where parent = %s", dep[0].journal_entry, as_dict=True)
								amount = 0
								for b in js:
										jea = frappe.get_doc("Journal Entry Account", b.name)
										dr_or_cr = "credit"
										amount = flt(b.credit_in_account_currency)
										if flt(b.debit_in_account_currency) > 0:
												dr_or_cr = "debit"
												amount = flt(b.debit_in_account_currency)
										account_curr = str(dr_or_cr) + "_in_account_currency"
					#amount = flt(amount) - flt(a.expected_value_after_useful_life) * 2
										#jea.db_set(account_curr, flt(amount) - flt(a.expected_value_after_useful_life) * 2)

				je = frappe.get_doc("Journal Entry", dep[0].journal_entry)
				je.db_set("total_debit", amount)
				je.db_set("total_credit", amount)

				gls = frappe.db.sql("select name, credit, debit from `tabGL Entry` where voucher_no = %s", dep[0].journal_entry, as_dict=True)
				for c in gls:
						gl = frappe.get_doc("GL Entry", c.name)
						dr_or_cr = "credit"
						amount = flt(c.credit)
						if flt(c.debit) > 0:
								dr_or_cr = "debit"
								amount = flt(c.debit)
						account_curr = str(dr_or_cr) + "_in_account_currency"
						#gl.db_set(account_curr, flt(amount) - flt(a.expected_value_after_useful_life) * 2)
						#gl.db_set(dr_or_cr, flt(amount) - flt(a.expected_value_after_useful_life) * 2)

		if flt(a.expected_value_after_useful_life) > 0:
				cur_value = flt(obj.depreciation_amount) - flt(a.expected_value_after_useful_life) * 2
				#obj.db_set("depreciation_amount", flt(cur_value))

						
def consume_trans():
	trans = frappe.db.sql("select name from `tabEquipment POL Transfer` where docstatus = 1", as_dict=True)
	for a in trans:
		b = frappe.get_doc("Equipment POL Transfer", a.name)
		con = frappe.new_doc("Consumed POL")	
		con.equipment = b.from_equipment
		con.branch = b.from_branch
		con.pol_type = b.pol_type
		con.date = b.transfer_date
		con.qty = -1 * flt(b.quantity)
		con.reference_type = "Equipment POL Transfer"
		con.reference_name = b.name
		con.submit()
		con1 = frappe.new_doc("Consumed POL")	
		con1.equipment = b.to_equipment
		con1.branch = b.to_branch
		con1.pol_type = b.pol_type
		con1.date = b.transfer_date
		con1.qty = b.quantity
		con1.reference_type = "Equipment POL Transfer"
		con1.reference_name = b.name
		con1.submit()
		frappe.db.commit()


def consume_pol():
	frappe.db.sql("delete from `tabConsumed POL`")
	frappe.db.commit()

	issues = frappe.db.sql("select name from `tabIssue POL` where docstatus = 1", as_dict=True)
	for a in issues:
		pol = frappe.get_doc("Issue POL", a.name)
		for b in pol.items:
			con = frappe.new_doc("Consumed POL")	
			con.equipment = b.equipment
			con.branch = pol.branch
			con.pol_type = pol.pol_type
			con.date = pol.date
			con.qty = b.qty
			con.reference_type = "Issue POL"
			con.reference_name = pol.name
			con.submit()
			frappe.db.commit()
	
	dcs = frappe.db.sql("select name from `tabPOL` where docstatus = 1 and direct_consumption = 1", as_dict=True)
	for a in dcs:
		b = frappe.get_doc("POL", a.name)
		con = frappe.new_doc("Consumed POL")	
		con.equipment = b.equipment
		con.branch = b.branch
		con.pol_type = b.pol_type
		con.date = b.date
		con.qty = b.qty
		con.reference_type = "POL"
		con.reference_name = b.name
		con.submit()
		frappe.db.commit()

def update_mechanical():
	mps = frappe.db.sql("select name from `tabMechanical Payment` where docstatus = 1", as_dict=True)
	for a in mps:
		acc_name = frappe.db.sql("select account from `tabGL Entry` where voucher_no = %s and debit > 0 and docstatus = 1", (a.name), as_dict=True)
		if acc_name:
			doc = frappe.get_doc("Mechanical Payment", a.name)
			doc.db_set("income_account", acc_name[0].account)
			print(str(acc_name[0].account) + " ==> " + str(a.name))

def ta_attendance():
	all_ta = frappe.db.sql("select name from `tabTravel Authorization` where docstatus = 1", as_dict=True)
	for ta in all_ta:
		ta = frappe.get_doc("Travel Authorization", ta.name)
		d = ta.items[0].date
		if ta.items[len(ta.items) - 1].halt and ta.items[len(ta.items) - 1].till_date:
			e = ta.items[len(ta.items) - 1].till_date
		else:
			e = ta.items[len(ta.items) - 1].date

		days = date_diff(e,d) + 1
		print(str(ta.name) + " ==> " + str(d) + " till " + str(e) + " ::: " + str(days))
		for a in (d + timedelta(n) for n in range(days)):
			al = frappe.db.sql("select name from tabAttendance where docstatus = 1 and employee = %s and att_date = %s", (ta.employee, a), as_dict=True)
			if al:
				doc = frappe.get_doc("Attendance", al[0].name)
				doc.cancel()
			#create attendance
			attendance = frappe.new_doc("Attendance")
			attendance.flags.ignore_permissions = 1
			attendance.employee = ta.employee
			attendance.employee_name = ta.employee_name 
			attendance.att_date = a
			attendance.status = "Tour"
			attendance.branch = ta.branch
			attendance.company = frappe.db.get_value("Employee", ta.employee, "company")
			attendance.reference_name = ta.name
			attendance.submit()

def add_days_test():
	all_att = frappe.db.sql("select name from `tabLeave Application` where docstatus = 1", as_dict=True)
	for att in all_att:
		print(att.name)
		self = frappe.get_doc("Leave Application", att.name) 
		d = getdate(self.from_date)
		e = getdate(self.to_date)
		days = date_diff(e, d) + 1
		for a in (d + timedelta(n) for n in range(days)):
			if getdate(a).weekday() != 6:
				#create attendance
				attendance = frappe.new_doc("Attendance")
				attendance.flags.ignore_permissions = 1
				attendance.employee = self.employee
				attendance.employee_name = self.employee_name 
				attendance.att_date = a
				attendance.status = "Leave"
				attendance.branch = self.branch
				attendance.company = self.company
				attendance.reference_name = self.name
				attendance.submit()

def assign_branch_att():
	atts = frappe.db.sql("select name, employee from `tabAttendance` where docstatus = 1", as_dict=True)
	for a in atts:
		emp = frappe.db.get_value("Employee", a.employee, "branch")
		doc = frappe.get_doc("Attendance", a.name)
		doc.db_set("branch", emp)

def assign_date_ta():
	tas = frappe.db.sql("select name from `tabTravel Authorization` where travel_claim is null", as_dict=True)
	for ta in tas:
		taa = frappe.db.sql("select name, date from `tabTravel Authorization Item` where parent = %s order by date desc limit 1", (str(ta.name)), as_dict=True)
		doc = frappe.get_doc("Travel Authorization", ta.name)
		#doc.db_set('end_date_auth', taa[0].date)
		print(str(ta.name) + " ==> " + str(taa[0].date) + "  ==> " + str(doc.end_date_auth))

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

def delete_extra_gl_entries():
	gle = frappe.db.sql("""
		select name from `tabGL Entry` where voucher_no = 'SI22055874' and account = 'Advance from Customer - NRDCL'
	""", as_dict = 1)
	count = 1
	if gle:
		for a in gle:
			if count != 1:
				frappe.db.sql("""delete from `tabGL Entry` where name = '{}'""".format(a.name))
			print(str(count)+". "+a.name)
			count+=1

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
					"poi_name": item.name,
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
			expense, cost_center = frappe.db.get_value("Purchase Order Item", item.po_detail, ["budget_account", "cost_center"])
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
						"pii_name": item.name,
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
								select company, branch, name as employeecd, user_id, 'DES Employee' type
								 from `tabDES Employee`
								 where user_id is not null
								 and exists(select 1
												from  `tabUser`
												where `tabUser`.name = `tabDES Employee`.user_id)
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
		print (counter, idoc.name, idoc.docstatus)

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
						print (i.doctype.ljust(50,' ')+str(":"), c.cc, c.counts)
				
#bench execute erpnext.custom_patch.el_allocation --args 'CDCL0005001','no'
def el_allocation(employee=None):
		# Allocating missed out 5days EL for Hesothangkha for 01/01/17-30/09/17
		print ('employee', employee)

		cond = ""
		
		if employee:
				cond = "and employee = '{0}'".format(employee)
				
		li = frappe.db.sql("""
				select name, employee, from_date, to_date,
						new_leaves_allocated,
						carry_forwarded_leaves,
						total_leaves_allocated,
						leave_type
				from `tabLeave Allocation` as la
				where la.leave_type = 'Earned Leave'
				and from_date = '2017-01-01'
				and to_date = '2017-09-30'
				and exists(select 1
							 from `tabEmployee Internal Work History` as e
							where e.branch = 'Hesothangkha'
							  and e.parent = la.employee)
				and docstatus = 1
				{cond}
				order by employee
				""".format(cond=cond), as_dict=True)

		'''
		for i in li:
				cf = flt(i.carry_forwarded_leaves)+5.0 if flt(i.carry_forwarded_leaves)+5.0 <= 60.0 else 60.0
				ta = flt(i.total_leaves_allocated)+5.0 if flt(i.total_leaves_allocated)+5.0 <= 60.0 else 60.0
				
				frappe.db.sql(
								update `tabLeave Allocation`
								set carry_forwarded_leaves = {0}, total_leaves_allocated = {1}
								where name = '{2}'
						.format(flt(cf), flt(ta), i.name))
		'''

		counter = 0
		for i in li:
				counter += 1
				print (counter,'|', i.employee,'|', i.from_date,'|', i.to_date,'|', i.new_leaves_allocated,'|', i.carry_forwarded_leaves,'|', i.total_leaves_allocated)

				# New allocations
				na = frappe.db.sql("""
						select name, employee, from_date, to_date,
								new_leaves_allocated,
								carry_forwarded_leaves,
								total_leaves_allocated,
								leave_type
						  from `tabLeave Allocation`
						 where employee   = '{0}'
						   and leave_type = '{1}'
						   and docstatus  = 1
						   and from_date  > '{2}'
						 order by from_date, to_date
						""".format(i.employee, i.leave_type, i.to_date), as_dict=True)

				for a in na:
						print (counter,'|',a.employee,'|', a.from_date,'|', a.to_date,'|', a.new_leaves_allocated,'|', a.carry_forwarded_leaves,'|', a.total_leaves_allocated)

						'''
						cf = flt(a.carry_forwarded_leaves)+5.0 if flt(a.carry_forwarded_leaves)+5.0 <= 60.0 else 60.0
						ta = flt(a.total_leaves_allocated)+5.0 if flt(a.total_leaves_allocated)+5.0 <= 60.0 else 60.0

						print cf, ta

						frappe.db.sql(
								update `tabLeave Allocation`
								set carry_forwarded_leaves = {0}, total_leaves_allocated = {1}
								where name = '{2}'
						.format(flt(cf), flt(ta), a.name))
						'''

# /home/frappe/erp bench execute erpnext.custom_patch.refresh_salary_structure
def refresh_salary_structure():
	ss = frappe.db.sql("select name from `tabSalary Structure` where is_active='Yes'", as_dict=True)
	counter = 0
	for s in ss:
		doc = frappe.get_doc("Salary Structure", s.name)
		for a in doc.earnings:
			if a.salary_component == "Basic Pay":
				counter += 1
				print (counter,s.name)
				update_salary_structure(doc.employee, flt(a.amount), s.name)
				break

# /home/frappe/erp bench execute erpnext.custom_patch.update_project_invoice
# Refreshing fields uptodate_quantity, uptodate_rate, uptodate_amount
def update_project_invoice():
		bi = frappe.db.sql("""
				select t2.name, t2.parent, t1.invoice_date, t2.boq_item_name, t1.modified
				from `tabProject Invoice BOQ` as t2, `tabProject Invoice` as t1
				where t2.parent = t1.name
				and ifnull(t2.is_group,0) = 0
				and t1.docstatus != 2
				order by t1.project, t1.invoice_date
		""", as_dict=1)

		counter = 0
		for i in bi:
				counter += 1
				uptodate_quantity = 0.0
				uptodate_rate     = 0.0
				uptodate_amount   = 0.0
				
				tot = frappe.db.sql("""
						select
								sum(ifnull(invoice_quantity,0)) as invoice_quantity,
								max(ifnull(invoice_quantity,0)) as invoice_rate,
								sum(ifnull(invoice_amount,0))   as invoice_amount
						from `tabProject Invoice BOQ` as t2, `tabProject Invoice` as t1
						where t2.parent = t1.name
						and t2.boq_item_name = '{0}'
						and t2.is_selected = 1
						and t2.docstatus = 1
						and t1.invoice_date <= '{1}'
						and t1.modified < '{2}'
				""".format(i.boq_item_name, i.invoice_date, i.modified), as_dict=1)

				if tot:
						uptodate_quantity = flt(tot[0].invoice_quantity)
						uptodate_rate     = flt(tot[0].invoice_rate)
						uptodate_amount   = flt(tot[0].invoice_amount)

				frappe.db.sql("""
						update `tabProject Invoice BOQ`
						set uptodate_quantity = {1},
								uptodate_rate = {2},
								uptodate_amount = {3}
						where name = '{0}'
				""".format(i.name, uptodate_quantity, uptodate_rate, uptodate_amount))
				print (counter)

# /home/frappe/erp bench execute erpnext.custom_patch.add_mr_creator_role
# Adding back MR Creator role, 2018/07/26
def add_mr_creator_role():
		li = frappe.db.sql("""
				select distinct(t1.owner) as owner
				from `tabMaterial Request` as t1
				where t1.creation >= '2018-03-01'
				and not exists(select 1
							   from `tabUserRole` as t2
							   where t2.parent = t1.owner
							   and t2.role = 'MR Creator')
		""", as_dict=1)
		
		counter = 0
		for i in li:
				counter += 1
				user = frappe.get_doc("User", i.owner)
				user.flags.ignore_permissions = True
				user.add_roles("MR Creator")
				print (counter, i.owner)

#
# by SHIV on 2018/08/10
# Updating to_date in production from backup taken on 2018/08/08 12:00PM        
#
def update_hire_charge_parameter():
	li = frappe.db.sql("""
		select *
		from `tabHire Charge Item_temp` as t1
		where exists(select 1
				from `tabHire Charge Item_bkup20180810` as t2
				where t2.name = t1.name
				and date_format(t2.modified,'%H:%i') = '14:24') 
	""", as_dict=1)

	counter = 0
	for i in li:
		counter += 1
		print (counter, i.name)

#
# by SHIV on 2018/08/15
# Populating Family Details default record for all the active employees
#
def populate_family_details():
		counter = 0
		for t in frappe.get_all("Employee", ["name","employee_name","gender","date_of_birth","passport_number","dzongkhag","gewog","village"], {"status":"Active"}):
				if not frappe.db.exists("Employee Family Details", {"parent": t.name, "relationship": "Self"}):
						counter += 1
						print (counter, t.name)
						doc = frappe.get_doc("Employee", t.name)
						row = doc.append("employee_family_details",{})
						row.relationship  = "Self"
						row.full_name     = t.employee_name
						row.gender        = t.gender
						row.date_of_birth = t.date_of_birth
						row.cid_no        = t.passport_number
						row.district_name = t.dzongkhag
						row.city_name     = t.gewog
						row.village_name  = t.village
						row.save()
		print ('Done adding rows....')

"""
		Author: SHIV
		Date: 2018/09/27
		Purpose: This method will update all the payment method fields with default value from
						salary components.
"""
def update_sst_payment_methods():
		counter = 0
		for i in frappe.db.sql("select * from `tabSalary Component` where field_value is not null", as_dict=True):
				counter += 1
				print (counter, i.name)
				frappe.db.sql("""
						update `tabSalary Structure`
						set {0} = '{1}'
				""".format(i.field_method, i.payment_method))

		frappe.db.sql("update `tabSalary Structure` set temporary_transfer_allowance_method = 'Percent' where temporary_transfer_allowance > 0 and lumpsum_temp_transfer_amount = 0")
		frappe.db.sql("update `tabSalary Structure` set temporary_transfer_allowance_method = 'Lumpsum' where temporary_transfer_allowance = 0 and lumpsum_temp_transfer_amount > 0;");
		print ('Done updating.....')

"""
		Author: SHIV
		Date: 2018/10/29
		Purpose: This method will update all the salary structures with sws.
"""
def update_sst_grade():
		counter = 0
		for i in frappe.db.sql("select sst.name,sst.employee,e.employment_type,e.employee_group,e.employee_subgroup from `tabSalary Structure` as sst, `tabEmployee` as e where e.name = sst.employee", as_dict=True):
				counter += 1
				settings = get_payroll_settings(i.employee)
				doc = frappe.get_doc("Salary Structure", i.name)
				doc.employment_type = i.employment_type
				doc.employee_group = i.employee_group
				doc.employee_grade = i.employee_subgroup
				doc.eligible_for_sws = 1 if flt(settings.get("sws_contribution")) else 0
				doc.save()
				print (counter,i.employee,i.name) 

def remove_users():
		counter = 0
		for e in frappe.db.sql("select name, user_id from `tabEmployee` where docstatus=0 order by name", as_dict=True):
				counter += 1
				emp = frappe.get_doc("Employee", e.name)
				emp.user_id = None
				emp.company_email = None
				emp.save()
				print (counter,e.name, e.user_id, "Removed successfully....")

		counter = 0
		for u in frappe.db.sql("select name from `tabUser` where ifnull(btl,0)= 0 order by name", as_dict=True):
				counter += 1
				user = frappe.get_doc("User", u.name)
				user.delete()
				print (counter, u.name, "Removed successfully....")

def assign_role_approver():
	for e in frappe.db.sql("select distinct(reports_to) as employee from `tabEmployee`", as_dict=True):
		emp = frappe.get_doc("Employee", e.employee)
		if emp.user_id:
			user = frappe.get_doc("User", emp.user_id)
			user.flags.ignore_permissions = True
			user.remove_roles("Approver")
			user.add_roles("Approver")
			print ("Success", emp.employee)
		else:
			print ("Failed", emp.employee)

def cancel_delivery_note(debug=1):
	dn_arr = frappe.db.sql_list("""select name
					from `tabDelivery Note`
					where name in ('DN22013989')
					order by posting_date desc
				""")
	# dn_arr = ['DN21081026', 'DN21051921', 'DN21051924', 'DN21051926', 'DN21051292','DN21051854']
	counter = 0
	for a in dn_arr:
		counter += 1
		doc = frappe.get_doc("Delivery Note", a)
		print(counter, a, doc.docstatus)
		if not debug and doc.docstatus == 1:
			try:
				doc.cancel()
				print('Cancelled...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()

def cancel_sales_order(debug=1):
	so_arr = frappe.db.sql_list("""select name
					from `tabSales Order`
					where name in ('SO21080441', 'SO21050781', 'SO21050672','SO21050796')
					order by transaction_date desc
				""")
	# so_arr = [ 'SO21080441', 'SO21050781', 'SO21050672','SO21050796']
	counter = 0
	for a in so_arr:
		counter += 1
		doc = frappe.get_doc("Sales Order", a)
		print(counter, a, doc.docstatus)
		if not debug and doc.docstatus == 1:
			try:
				doc.cancel()
				print('Cancelled...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()

def cancel_production(debug=1):
	pd_arr = frappe.db.sql_list("""select name
					from `tabProduction`
					where name in ('PRO210301578', 'PRO211001191', 'PRO210301211',
						'PRO210301578', 'PRO211001191', 'PRO210301211')
					order by posting_date desc
				""")
	# pd_arr = ['PRO210301578', 'PRO211001191', 'PRO210301211']
	counter = 0
	for a in pd_arr:
		counter += 1
		doc = frappe.get_doc("Production", a)
		print(counter, a, doc.docstatus)
		if not debug and doc.docstatus == 1:
			try:
				doc.cancel()
				print('Cancelled...')
			except Exception as e:
				print(str(e))
			frappe.db.commit()

# def so_change_status():
# 	so = frappe.db.sql(" select name from `tabSales Order` where status='Draft' and docstatus=2", as_dict=True)
# 	c = 1
# 	for s in so:
# 		if s.name != 'SO19031525' and :
# 			doc = frappe.get_doc("Sales Order", s.name)
# 			doc.on_cancel()
# 			print(c)
# 			c += 1
# 	print("DONE")

# def submit_production_entry():
# 	pd_arr = ['PRO220100694', 'PRO220100702', 'PRO220100685', 'PRO220100628']
# 	c = 1
# 	for s in pd_arr:
# 		doc = frappe.get_doc("Production", s)
# 		doc.on_submit()
# 		print(c)
# 		c += 1
# 	print("DONE")

def delete_lot_list():
	with open("/home/frappe/erp/apps/erpnext/erpnext/Cancelled Lot_List.csv") as f:
		reader = csv.reader(f)
		mylist = list(reader)
		c = 0
		for i in mylist:
			docst = frappe.db.sql(""" select lld.name as cname from `tabLot List` ll, `tabLot List Details` lld where ll.name=lld.parent and ll.docstatus=2 and ll.name = "{}" """.format(i[1]),as_dict=1)
			if docst:
				print("ID: " + str(i[1]))
				print("CNAME: " + str(docst[0].cname))
				frappe.db.sql(""" delete from `tabLot List Details` where name = '{}' """.format(docst[0].cname))	
			frappe.db.sql(""" delete from `tabLot List` where docstatus=2 and name = "{}" """.format(i[1]))
			print("count: " + str(c))
			c += 1
		print("DONE")
	
def delete_lot_list2():
	with open("/home/frappe/erp/apps/erpnext/erpnext/Lot_List (2).csv") as f:
		reader = csv.reader(f)
		mylist = list(reader)
		c = 0
		for i in mylist:
			docst = frappe.db.sql(""" select lld.name as cname from `tabLot List` ll, `tabLot List Details` lld where ll.name=lld.parent and ll.docstatus=2 and ll.name = "{}" """.format(i[1]),as_dict=1)
			if docst:
				print("ID: " + str(i[1]))
				print("CNAME: " + str(docst[0].cname))
				frappe.db.sql(""" delete from `tabLot List Details` where name = '{}' """.format(docst[0].cname))	
			frappe.db.sql(""" delete from `tabLot List` where docstatus=2 and name = "{}" """.format(i[1]))
			print("count: " + str(c))
			c += 1
		print("DONE")


def delete_transactions_in_company():
	dt_list = [
		"Sales Order", "Delivery Note", "Sales Invoice", "Stock Entry", "Production", "Purchase Order", 
		"Purchase Receipt", "Purchase Invoice", "Material Request", "Stock Ledger Entry", "GL Entry", 
		"Payment Entry", "Journal Entry", "Direct Payment","Hire Charge Invoice","Job Card","Mechanical Payment",
		"HSD Payment","POL","Royalty Payment", "Asset", "Asset Issue Details", "BOM", "Work Order", "Production Plan",
		"Production Entry", "Lot List","Salary Slip","Travel Claim","Travel Authorization","Leave Encashment","Salary Increment",
		"Salary Advance", "Overtime Application","Other Contribution","Hall Booking","Request for Quotation","Supplier Quotation",
		"Lot Allotment", "Vehicle","Transporter","Transport Request","Vehicle Update","Change Status","Change Vehicle Status",
		"Load Request", "Delivery Confirmation","Customer Order","Customer Payment","Break Down Report","Job Card","Equipment Request",
		"Equipment Hiring Form","Vehicle Logbook","Equipment Hiring Extension","Issue POL","Equipment POL Transfer",
		"Imprest Receipt", "Imprest Recoup","Production Target"
	]
	for doctype in dt_list:
		print("Doc:" + str(doctype))
		meta = frappe.get_meta(doctype)
		if not meta.issingle:
			if not meta.istable:
				# delete children
				for df in meta.get_table_fields():
					print("CT :" + str(df.options))
					frappe.db.sql("""delete from `tab{0}`""".format(df.options))

			# delete parent
			frappe.db.sql("""delete from `tab{0}` """.format(doctype))

			# reset series
			naming_series = meta.get_field("naming_series")
			if naming_series and naming_series.options:
				prefixes = sorted(naming_series.options.split("\n"), lambda a, b: len(b) - len(a))

				for prefix in prefixes:
					if prefix:
						last = frappe.db.sql("""select max(name) from `tab{0}`
							where name like %s""".format(doctype), prefix + "%")
						if last and last[0][0]:
							last = cint(last[0][0].replace(prefix, ""))
						else:
							last = 0

						frappe.db.sql("""update tabSeries set current = %s
							where name=%s""", (last, prefix))

			# reset autoname
			frappe.db.sql("""
				delete
				from `tabSeries`
				where exists(select 1
								from `tabDocType` as dt
							where dt.name = '{0}'
								and dt.autoname like '%#%'
								and `tabSeries`.name like concat(substring_index(dt.autoname,'.',1),'%')
							)
				""".format(doctype))

def update_item_ba():
	with open("/home/frappe/erp/apps/erpnext/erpnext/Item_BA_relation.csv") as f:
		reader = csv.reader(f)
		mylist = list(reader)
		c = 0
		for i in mylist:
			frappe.db.sql("update `tabItem` set business_activity='{}' where name = '{}'".format(i[2],i[1]),as_dict=1)
			print("count: " + str(c))
			c += 1
		print("DONE")

def submit_sws_app():
	doc = frappe.get_doc("SWS Application", 'SWS2206012')
	# print(doc.name, doc.docstatus)
	# if doc.docstatus == 0:
	try:
		doc.on_submit()
		print('Submitted...')
	except Exception as e:
		print(str(e))
	frappe.db.commit()

def correct_gl_for_item_in_si():
	with open("/home/frappe/erp/apps/erpnext/erpnext/correct_gl.csv") as f:
		reader = csv.reader(f)
		mylist = list(reader)
		c = 0
		for i in mylist:
			si_doc = frappe.db.sql("select si.name, si.customer, si.posting_date, sid.item_name, sid.income_account from `tabSales Invoice` si, `tabSales Invoice Item` sid where sid.parent=si.name and si.docstatus=1 and sid.item_code='{}' and si.posting_date > '2023-01-01'".format(i[0]), as_dict=1)
			for d in si_doc:
				gl_entries = frappe.db.sql("select name, voucher_no, account from `tabGL Entry` where voucher_no='{}' and account='{}'".format(d.name, d.income_account), as_dict=1)
				for a in gl_entries:
					frappe.db.sql("update `tabGL Entry` set account='{}' where name='{}' and account='{}'".format(i[2], a.name, a.account))
					frappe.db.sql("update `tabSales Invoice Item` set income_account='{}' where parent='{}' and income_account='{}'".format(i[2], d.name, d.income_account))
				c += 1
		print(str(c))