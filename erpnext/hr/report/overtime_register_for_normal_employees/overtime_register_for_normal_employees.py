# # Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

################Created by Cheten Tshering on 10/09/2020 #####################
from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate, flt
from frappe import msgprint, _
from calendar import monthrange

def execute(filters=None):
	columns, data = [], []

	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_data(filters):
	cond = get_condition(filters)
	data = frappe.db.sql("""
		select oa.employee, oa.employee_name, oa.branch,
			oai.from_date, oai.to_date, oai.number_of_hours, oai.remarks
		from `tabOvertime Application` oa, `tabOvertime Application Item` oai
		where oa.name = oai.parent
		and oai.to_date >= '{from_date}'
		and oai.from_date <= '{to_date}' {condition}
	""".format(from_date=filters.get("from_date"), to_date=filters.get("to_date"),condition=cond))

	return data

def get_columns(filters):
	columns = [
		_("Employee ID") + ":Link/Overtime Application:150",
		_("Employee Name") + "::150",
		_("Branch") + "::150",
		_("From Date/Time") + "::150",
		_("To Date/Time") + "::150",
		_("Number of Hours") + "::100",
		_("Remarks") + "::150"
	]
	return columns

def get_condition(filters):
	cond = ""
	if filters.branch:
		cond += """and branch="{}" """.format(filters.branch)
	return cond

# def execute_old(filters=None):
# 	if not filters: filters = {}

# 	conditions, filters = get_conditions(filters)
# 	columns = get_columns(filters)
# 	att_map = get_attendance_list(conditions, filters)
# 	emp_map = get_employee_details(filters.employee_type)

# 	data = []
# 	for emp in sorted(att_map):
# 		emp_det = emp_map.get(emp)
# 		if not emp_det:
# 			continue

# 		row = [emp_det.employee_name, emp_det.employee1, emp_det.rate]

# 		total_p = 0.0
# 		for day in range(filters["total_days_in_month"]):
# 			status = att_map.get(emp).get(day + 1, '')

# 			if status > 0:
# 				total_p += flt(status)

# 			row.append(status)

# 		row += [total_p]
# 		data.append(row)

# 	return columns, data

# def get_columns_old(filters):
# 	columns = [
# 		_("Employee Name") + "::140", 
# 		_("Employee ID")+ ":Link/Overtime Application:150",
# 		_("Hourly Rate") + "::120"
# 	]

# 	for day in range(filters["total_days_in_month"]):
# 		columns.append(cstr(day+1) +"::20")

# 	columns += [_("Total Hours") + ":Float:100"]
# 	return columns

# def get_attendance_list(conditions, filters):
# 	attendance_list = frappe.db.sql("""select employee as employee1, day(items.from_date) as day_of_month,
# 		items.number_of_hours as status from `tabOvertime Application` oa, `tabOvertime Application Item` items
# 		where items.parent=oa.name %s order by oa.employee1""" %
# 		conditions, filters, as_dict=1)

# 	att_map = {}
# 	for d in attendance_list:
# 		att_map.setdefault(d.employee1, frappe._dict()).setdefault(d.day_of_month, "")
# 		att_map[d.employee1][d.day_of_month] = d.status

# 	return att_map

# def get_conditions_old(filters):
# 	if not (filters.get("month") and filters.get("year")):
# 		msgprint(_("Please select month and year"), raise_exception=1)

# 	filters["month"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
# 		"Dec"].index(filters.month) + 1

# 	filters["total_days_in_month"] = monthrange(cint(filters.year), filters.month)[1]

# 	conditions = " and month(items.from_date) = %(month)s and year(items.from_date) = %(year)s and cost_center = \'" + str(filters.cost_center) + "\' "

# 	return conditions, filters

# def get_employee_details(employee_type):
# 	emp_map = frappe._dict()
# 	for d in frappe.db.sql("""select employee_name, employee, rate
#                         from `tabOvertime Appliction`""", as_dict=1):
#                         emp_map.setdefault(d.employee_name, d)

# 	return emp_map

# @frappe.whitelist()
# def get_years():
# 	year_list = frappe.db.sql_list("""select distinct YEAR(items.from_date) from `tabOvertime Application` oa,
# 	`tabOvertime Application Item` items where items.parent=oa.name """)
# 	if not year_list:
# 		year_list = [getdate().year]

# 	return "\n".join(str(year) for year in year_list)

# def get_years():
# 	year_list = frappe.db.sql_list("""select distinct YEAR(items.from_date) from `tabOvertime Application` ORDER BY YEAR(items.from_date) DESC""")
# 	if not year_list:
# 		year_list = [getdate().year]

# 	return "\n".join(str(year) for year in year_list)


# def execute(filters):
# 	filters["total_days_in_month"] = monthrange(cint(filters.year), filters.month)[1]
# 	list1 = ["Jan","Mar","Jul","Aug","Oct","Dec"]
# 	list2 = ["Feb"]
# 	list3 = ["Apr","May","Jun","Sept","Nov"]
# 	for i in list1:
# 		if filters.get("month") == i:
# 			columns = get_thirtyfirst(filters)
# 			data = get_data1(filters)
# 	for j in list2:
# 		if filters.get("month") == j:      
# 			columns = get_twentynine(filters)
# 			data = get_data2(filters)
# 	for k in list3:
# 		if filters.get("month") == k:
# 			columns = get_columns(filters)
# 			data = get_data(filters)
# 	return columns, data

# def get_thirtyfirst(filters):
# 	columns = [
# 		_("Employee Name") + "::150",
# 		_("Employee ID") + ":ink/Overtime Appliction:150",
# 		_("Branch") + "::120",
# 		_("Hourly Rate") + "::120"
# 	]
# 	thirtyfirst = ["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24",
# 	"25","26","27","28","29","30","31"]
# 	for day in thirtyfirst:
# 		columns.append(day)
	
# 	columns += [_("Toatl Hours") + "::150"]
# 	return columns
# def get_data1(filters):
# 	data = frappe.db.sql(
# 		"""
# 			select oa.employee_name, oa.employee, oa.branch, oa.rate from `tabOvertime Application` as oa 
# 			where oa.posting_date between '{start_date}' and '{to_date}' 
# 		""".format(start_date=filters.start_date, to_date=filters.to_date)
# 	)
# 	return data

# def get_twentynine(filters):
# 	columns = [
# 		_("Employee Name") + "::150",
# 		_("Employee ID") + ":ink/Overtime Appliction:150",
# 		_("Branch") + "::120",
# 		_("Hourly Rate") + "::120"
# 	]
# 	twentynine = ["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24",
# 	"25","26","27","28","29"]
# 	for day in twentynine:
# 		columns.append(day)
# 	columns += [_("Toatl Hours") + "::150"]
# 	return columns
# def get_data2(filters):
# 	data = frappe.db.sql(
# 		"""
# 			select oa.employee_name, oa.employee, oa.branch, oa.rate from `tabOvertime Application` as oa 
# 			where oa.posting_date between '{start_date}' and '{to_date}' 
# 		""".format(start_date=filters.start_date, to_date=filters.to_date)
# 	)
# 	return data


# def get_columns(filters=None):
# 	columns = [
# 		_("Employee Name") + "::150",
# 		_("Employee ID") + ":ink/Overtime Appliction:150",
# 		_("Branch") + "::120",
# 		_("Hourly Rate") + "::120"
# 	]
	

# 	#day_of_month = ["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24","25",
# 	#"26","27","28","29","30"]
# 	for day in range(filters["total_days_in_month"]):
# 		columns.append(day)

# 	columns += [_("Toatl Hours") + "::150"]

# 	return columns

# def get_data(filters):
# 	data = frappe.db.sql(
# 		"""
# 			select oa.employee_name, oa.employee, oa.branch, oa.rate from `tabOvertime Application` as oa 
# 			where oa.posting_date between '{start_date}' and '{to_date}' 
# 		""".format(start_date=filters.start_date, to_date=filters.to_date)
# 	)
# 	return data

# @frappe.whitelist()
# def get_years():
# 	year_list = frappe.db.sql_list("""select distinct YEAR(posting_date) from `tabOvertime Application` ORDER BY YEAR(posting_date) DESC""")
# 	if not year_list:
# 		year_list = [getdate().year]

# 	return "\n".join(str(year) for year in year_list)
