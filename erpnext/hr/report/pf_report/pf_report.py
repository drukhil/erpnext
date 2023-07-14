# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0		  SSK		                   03/08/2016         Taking care of Duplication of columns
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}
        data    = []
        columns = []
        
	data = get_data(filters)
	if not data:
                return columns, data
        
	columns = get_columns(data)
	
	return columns, data
	
def get_columns(data):
	columns = [
		_("#Posting Member") + "::80", 
		_("Acc No DPA") + "::80", 

		_("Company") + ":Link/Branch:120", 
		_("Dept Code") + "::80", 
		_("Dept Name") + "::110", 
		_("Branch") + ":Link/Branch:120", 
        
		_("NPPF Agency Code") + " ::70",
		_("Month") + "::80",
		_("Year") + "::80", 
		
		_("Employee Code") + ":Link/Employee:90", 
		_("Employee Name") + "::140", 
		
		_("CID") + "::120",
		
		_("PF Account#") + "::100",
		_("ension Scheme") + "::70", 
		_("Grade") + "::70",
		_("Designation") + ":Link/Designation:120",
		_("PI Code") + "::100", 
		_("Journal #") + "::100",
		_("Basic Pay") + ":Currency:120",
		_("Pay Arrear") + ":Currency:100",
		_("EOLS MTG") + ":Currency:100",
        _("Employee PF") + ":Currency:120", 
		_("Employer PF") + ":Currency:120", 
		_("PF Amt GC") + ":Currency:100",
		_("PF Amt VC") + ":Currency:120",
		_("Total") + ":Currency:120"
	]
	
	return columns
	
def get_data(filters):
	conditions, filters = get_conditions(filters)

        data = frappe.db.sql("""
                select "#Posting Menber", 0, t1.company, "", "", t1.branch,   "C080000070",t1.month, t1.fiscal_year, t3.name,  t3.employee_name,t3.passport_number,  t3.nppf_number,  0, t1.employee_grade, t1.designation,  " ", " ",
                        sum(case when t2.salary_component = 'Basic Pay' then ifnull(t2.amount,0) else 0 end) as basicpay, "", "",
                        
                        sum(case when t2.salary_component = 'PF' then ifnull(t2.amount,0) else 0 end) as employeepf,
                        sum(case when t2.salary_component = 'PF' then ifnull(t2.amount,0) else 0 end) as employerpf, "","",
                        sum(case when t2.salary_component = 'PF' then ifnull(t2.amount,0)*2 else 0 end) as total
                       
                        
                from `tabSalary Slip` t1, `tabSalary Detail` t2, `tabEmployee` t3
                where t1.docstatus = 1 %s
                and t3.employee = t1.employee
                and t2.parent = t1.name
                and t2.salary_component in ('Basic Pay','PF')
                group by t1.employee, t3.employee_name, t1.designation, t3.passport_number,
                        t3.nppf_number, t1.company, t1.branch, t1.department, t1.division, t1.section
                        
                """ % conditions, filters)

	'''	
	if not data:
		msgprint(_("No Data Found for month: ") + cstr(filters.get("month")) + 
			_(" and year: ") + cstr(filters.get("fiscal_year")), raise_exception=1)
	'''
	
	return data
	
def get_conditions(filters):
	conditions = ""
	if filters.get("month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
			"Dec"].index(filters["month"]) + 1
		filters["month"] = month
		conditions += " and t1.month = %(month)s"
	if filters.get("employment_type"): conditions += " and t3.employment_type = %(employment_type)s"
	if filters.get("fiscal_year"): conditions += " and t1.fiscal_year = %(fiscal_year)s"
	if filters.get("company"): conditions += " and t1.company = %(company)s"
	if filters.get("employee"): conditions += " and t1.employee = %(employee)s"
	if filters.get("tier"): conditions += " and t3.nppf_tiers = %(tier)s"
	
	return conditions, filters
	
