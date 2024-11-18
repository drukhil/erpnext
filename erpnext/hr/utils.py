# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def set_employee_name(doc):
	if doc.employee:
		emp = frappe.get_doc("Employee", doc.employee)
		doc.employee_name = emp.employee_name
		doc.designation = emp.designation
		doc.branch = emp.branch
		doc.department = emp.department
		doc.division = emp.division

@frappe.whitelist()
def get_employees():
	""" get list of employees for ndi wallet integration
	"""
	# cond 	  = []
	# site_cond = ""
	# tbp_cond = ""
	# columns   = ["cbs.branch", "cbs.has_common_pool", "cbs.allow_self_owned_transport", "cbs.allow_other_transport"]
	# if not item_sub_group and not item:
	# 	frappe.throw(_("Please select a material first"))
	# if destination_dzongkhag:
	# 	tbp_cond = """ and exists(select 1 from `tabBranch` b where b.name = cbs.branch and b.dzongkhag = '{}')""".format(destination_dzongkhag)

	# if branch:
	# 	cond.append('cbs.branch = "{0}" '.format(branch))
	# if item:
	# 	cond.append('cbsi.item = "{0}" '.format(item))
	# 	#columns.extend(["cbs.lead_time", "spr.selling_price as item_rate"])
	# 	columns.extend(["cbs.lead_time"])
	# if item_sub_group:
	# 	cond.append('cbsi.item_sub_group = "{0}" '.format(item_sub_group))
	# if site:
	# employees = frappe.db.sql("""
	# 	select e.name as employeeId, e.employee_name as name, e.passport_number as cid, e.gender, e.company, e.date_of_joining as appointmentDate,
	# 	e.date_of_retirement retirementDate, e.department, e.grade positionGrade, e.employment_type as employeeType, e.employee_group as positionLevel, e.designation as jobTitle, "Thimphu" as placeOfPosting,
	# 		(
	# 		select	
	# 			sd.amount
	# 		from
	# 		`tabSalary Detail` sd,
	# 		`tabSalary Structure` sl
	# 		where sd.parent = sl.name
	# 		and sl.employee = e.name
	# 		and sd.salary_component = 'Basic Pay'
	# 		and sl.is_active = 'Yes'
	# 		limit 1) as basicSalary,
	# 		(
	# 		select	
	# 			sl.total_earning
	# 		from
	# 		`tabSalary Structure` sl
	# 		where sl.employee = e.name
	# 		and sl.is_active = 'Yes'
	# 		limit 1) as grossSalary,
	# 		(
	# 		select	
	# 			sl.net_pay
	# 		from
	# 		`tabSalary Structure` sl
	# 		where sl.employee = e.name
	# 		and sl.is_active = 'Yes'
	# 		limit 1) as netSalary
	# 		from `tabEmployee` e where e.status = 'Active'
	# 		order by e.name asc
	# """, as_dict=True)
 
@frappe.whitelist()
def get_employees():
	employees = frappe.db.sql("""
		select e.name as employeeId, e.employee_name as name, e.passport_number as cid, e.gender, e.company, 
  		e.date_of_joining as appointmentDate, e.date_of_retirement retirementDate, e.department, 
    	e.employee_subgroup as positionGrade, e.employment_type as employeeType, e.employee_group as positionLevel, 
     	e.designation as jobTitle, "Thimphu" as placeOfPosting, 
      	( select sd.amount from `tabSalary Detail` sd, `tabSalary Structure` sl where sd.parent = sl.name and sl.employee = e.name and sd.salary_component = 'Basic Pay' and sl.is_active = 'Yes' limit 1) as basicSalary, 
       	( select sl.total_earning from `tabSalary Structure` sl where sl.employee = e.name and sl.is_active = 'Yes' limit 1) as grossSalary, 
        ( select sl.net_pay from `tabSalary Structure` sl where sl.employee = e.name and sl.is_active = 'Yes' limit 1) as netSalary from `tabEmployee` e where e.status = 'Active' order by e.name asc;
	""", as_dict=True)
	return employees

	
