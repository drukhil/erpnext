# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr
from operator import itemgetter

def execute(filters=None):
	validate_filters(filters)
	columns = get_columns()
	queries = construct_query(filters)
	data = get_data(queries, filters)

	return columns, data, filters

def get_data(query, filters=None):
	data = []
	datas = frappe.db.sql(query, as_dict=True)
	for d in datas:
		row = [d.month, "Salary", d.basic_pay, round(flt(d.gross_pay) - flt(d.basic_pay) - (flt(d.comm_all) / 2), 2), round(flt(d.gross_pay)-(flt(d.comm_all) / 2),2), round(flt(d.gross_pay)-(flt(d.comm_all) / 2),2), d.nppf,d.gis, flt(d.gross_pay) - flt(d.nppf) - flt(d.gis) - (flt(d.comm_all) / 2), d.tds, d.health, d.receipt_number, d.receipt_date]
		data.append(row)

	#Leave Encashment 
	if filters.employee:
		encash_data = frappe.db.sql("select distinct a.application_date as date, a.encashment_amount, a.tax_amount, r.receipt_number, r.receipt_date from `tabLeave Encashment` a, `tabRRCO Receipt Entries` r where a.name = r.purchase_invoice and a.employee = %s and a.docstatus = 1 and a.application_date between \'" + filters.fiscal_year + "-01-01\' and \'" + filters.fiscal_year + "-12-31\'", filters.employee, as_dict=True) 
		if encash_data:
			for a in encash_data:
				row = [str(a.date)[5:7], "Leave Encashment", a.encashment_amount, 0, a.encashment_amount, a.encashment_amount, 0, 0, a.encashment_amount, a.tax_amount, 0, a.receipt_number, a.receipt_date]
				data.append(row)
	
		#Bonus
		bonus = frappe.db.sql("""
                                        select distinct b.name, b.fiscal_year, b.posting_date, r.receipt_number, r.receipt_date 
                                        from tabBonus b, `tabRRCO Receipt Entries` r
                                        where b.fiscal_year = r.fiscal_year and b.docstatus = 1 and b.posting_date between %s and %s and r.purpose = 'Annual Bonus' 
                                      """, (str(filters.fiscal_year) + "-01-01", str(filters.fiscal_year) + "-12-31"), as_dict=1)
		for b in bonus:
			
			amt = frappe.db.sql("""
                                        select amount, tax_amount, balance_amount  
                                        from `tabBonus Details` 
                                        where parent = %s and employee = %s
                                      """, (b.name, filters.employee), as_dict=1)
			for a in amt:
				
				row = [str(b.posting_date)[5:7], "Bonus", a.amount, 0, a.amount, a.amount, 0, 0, a.amount, a.tax_amount, 0, b.receipt_number, b.receipt_date]
				data.append(row)

		#PVBA
		pbva = frappe.db.sql("""
                                        select distinct b.name, b.fiscal_year, b.posting_date, r.receipt_number, r.receipt_date 
                                        from tabPBVA b, `tabRRCO Receipt Entries` r
                                        where b.fiscal_year = r.fiscal_year and b.docstatus = 1 and b.posting_date between %s and %s and r.purpose = 'PBVA' 
                                      """, (str(filters.fiscal_year) + "-01-01", str(filters.fiscal_year) + "-12-31"), as_dict=1)
		for b in pbva:
			amt = frappe.db.sql("""
                                        select amount, tax_amount, balance_amount  
                                        from `tabPBVA Details` 
                                        where parent = %s and employee = %s
                                      """, (b.name, filters.employee), as_dict=1)
			for a in amt:
				row = [str(b.posting_date)[5:7], "PBVA", a.amount, 0, a.amount, a.amount, 0, 0, a.amount, a.tax_amount, 0, b.receipt_number, b.receipt_date]
				data.append(row)
                
            #Salary arrear 
		salary_arrear = frappe.db.sql(""" SELECT
                                t3.month,
                                t3.tds_receipt_date as receipt_date, 
                                t3.purpose,
                                ifnull(t2.arrear_corporate_allowance+t2.arrear_contract_allowance+t2.arrear_project_allowance+t2.arrear_mpi+t2.arrear_scarcity_allowance+t2.arrear_officiating_allowance,0) as others,
                                t3.tds_receipt_number as receipt_number,
                                t2.arrear_basic_pay as basic,
                                t2.new_gross_pay as gross,
                                t2.new_gross_pay as total,
                                t2.arrear_salary_tax as tds,
                                0 as gis,
                                t3.purpose as type,
                                t2.arrear_hc as health,
                                t2.arrear_pf as nppf,
                                t2.new_gross_pay - t2.arrear_pf  AS taxable
                                FROM `tabSalary Arrear Payment Item` t2 left JOIN `tabRRCO Receipt Tool` t3 ON t3.purpose = "Salary Arrears" 
                                where t3.docstatus = 1 and t2.docstatus=1 and t2.employee ='{employee}' and t3.fiscal_year = '{fiscal_year}' 
                                
                                
                                
                           """.format(employee = filters.employee,fiscal_year = filters.fiscal_year),as_dict=True)
		frappe.errprint(str(salary_arrear))
		for a in salary_arrear:
			
			row =[a.month, a.type,a.basic,a.others,a.gross,a.total,a.nppf,a.gis,a.taxable,a.tds,a.health,a.receipt_number, a.receipt_date]	
			data.append(row)
   
   
	data = sorted(data, key=itemgetter(0))
	for a in data:
		a[0] = get_month(a[0])

	return data

def construct_query(filters=None):
	query = """select a.month, a.gross_pay,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Basic Pay' and b.parent = a.name) as basic_pay,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Salary Tax' and b.parent = a.name) as tds ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'PF' and b.parent = a.name) as nppf ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Group Insurance Scheme' and b.parent = a.name) as gis ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Communication Allowance' and b.parent = a.name) as comm_all ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Health Contribution' and b.parent = a.name) as health,
	r.receipt_number, r.receipt_date
	 from `tabSalary Slip` a, `tabRRCO Receipt Entries` r
	 where a.fiscal_year = r.fiscal_year and a.month = r.month and a.docstatus = 1 and a.fiscal_year = """ + str(filters.fiscal_year)

	if filters.employee:
		query = query + " AND a.employee = \'" + str(filters.employee) + "\'"

	query+=";"
	
	return query

def validate_filters(filters):

	if not filters.fiscal_year:
		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))

	start, end = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"])
	filters.year_start = start
	filters.year_end = end

def get_columns():
	return [
		{
		  "fieldname": "month",
		  "label": "Month",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "type",
		  "label": "Income Type",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "basic",
		  "label": "Basic Salary",
		  "fieldtype": "Currency",
		  "width": 150
		},
		{
		  "fieldname": "others",
		  "label": "Other Allowances",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "gross",
		  "label": "Gross Salary",
		  "fieldtype": "Currency",
		  "width": 150
		},
		{
		  "fieldname": "total",
		  "label": "Total Income",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "pf",
		  "label": "NPPF",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "gis",
		  "label": "GIS",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "taxable",
		  "label": "Taxable Income",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "tds",
		  "label": "TDS / PIT",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "health",
		  "label": "Health",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "receipt_number",
		  "label": "RRCO Receipt No.",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "receipt_date",
		  "label": "RRCO Rt. Date",
		  "fieldtype": "Date",
		  "width": 100
		},
	]

def get_month(month):
	if month == "01":
		return "January"
	elif month == "02":
		return "February"
	elif month == "03":
		return "March"
	elif month == "04":
		return "April"
	elif month == "05":
		return "May"
	elif month == "06":
		return "June"
	elif month == "07":
		return "July"
	elif month == "08":
		return "August"
	elif month == "09":
		return "September"
	elif month == "10":
		return "October"
	elif month == "11":
		return "November"
	elif month == "12":
		return "December"
	else:
		return "None"
