# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_data(filters):
	data = []
	row  = {}
	parent = "Gyalsung Infra"
	duration = mandays = manpower = exp =  weightage = physical_progress = percent_completed = estimated_budget = expense = 0.0
	query = construct_query(filters)
	for a in frappe.db.sql(query, as_dict = True):
		expense = a.expense
                if not filters.project:
                        expense = get_expense(filters, a.name)
		parent = a.parent
		progress_weightage = round(flt(a.physical_progress_weightage), 6)
		physical_achievement =   round(flt(a.physical_progress), 4)
		completion = round(flt(physical_achievement)/flt(progress_weightage) * 100, 4)
		row = {"name": a.name, "expected_start_date": a.expected_start_date, "expected_end_date": a.expected_end_date, 
		"total_duration": flt(a.total_duration), "estimated_budget": flt(a.estimated_budget), 
		"expense_incured": flt(expense),	
		"physical_progress_weightage": progress_weightage, 
		"physical_progress":  physical_achievement, 
		"percent_completed": flt(completion),
		"project_engineer": a.project_engineer, 
		"engineer_name": a.pe_name, "contact": a.contact}
		data.append(row)	
		duration += flt(a.total_duration)
                estimated_budget += flt(a.estimated_budget)
                exp += flt(expense)
		weightage += round(flt(progress_weightage), 3)
		#weightage += flt(a.physical_progress_weightage)/100 * flt(a.parent_weightage)
		#physical_progress += flt(a.physical_progress)/100 * flt(a.parent_weightage)
		physical_progress += round(flt(physical_achievement), 3)
		percent_completed  = flt(physical_progress)/flt(weightage) * 100
	row1 = {"name": '<b> {0} </b> '.format(parent), "total_duration": duration, "estimated_budget": round(estimated_budget, 2), 
                "expense_incured": exp, "physical_progress_weightage": round(weightage, 2),
                "physical_progress":  round(physical_progress,2),  "percent_completed": "",  "project_engineer": ""}
	data.append(row1)
	return data


def get_expense(filters, cost_center):
        exp = 0.0
        from erpnext.accounts.accounts_custom_functions import get_child_cost_centers
        parent_cc = frappe.get_doc("Cost Center", cost_center).parent_cost_center
        cost_centers = get_child_cost_centers(parent_cc)
        exp = frappe.db.sql(""" select sum(debit) - sum(credit) as expense from `tabGL Entry` 
        where cost_center IN %(cost_center)s  and account in (select name from `tabAccount` 
        where root_type = 'Expense') and docstatus = 1""", {"cost_center": cost_centers}, as_dict = 1)
        return exp[0].expense

def construct_query(filters):
	cond = " and is_group = 1"
	fields = " ifnull(parent_project, 'GYALSUNG INFRA') as  parent, ifnull(physical_progress_weightage,0) as physical_progress_weightage, case physical_progress when 'NaN' then 0.0 else physical_progress end as physical_progress"
	if filters.get("project"):
		if filters.get("show_all"):
			frappe.throw("Cannot use filters with Show All, Un-Check <b> Show All </b>  to use other filters")
		cond = """ and parent_project = "{0}" """.format(filters.get("project"))
	if filters.get("activity"):
		if filters.get("show_all"):
			frappe.throw("Cannot use filters with Show All, Un-Check <b> Show All </b> to use other filters")
		cond = """ and project_name = "{0}" """.format(filters.get("activity"))
	
	if filters.get("show_all"):
		cond = " and is_group != 1"
		fields = " 'GYALSUNG INFRA' as parent, physical_progress_weightage /100 * parent_weightage as physical_progress_weightage, physical_progress / 100 * parent_weightage as physical_progress"

	if filters.get("status"):
		cond += " and status = '{0}'".format(filters.get('status'))
	
	query = """ select name, project_name, expense, expected_start_date, expected_end_date, parent_weightage, 
			ifnull(total_duration, 0) as total_duration, 
		ifnull(estimated_budget,0) as estimated_budget, {0},
		  status, project_engineer, pe_name, contact from `tabProject` where docstatus <= 1 """.format(fields)
	query += cond 
	return query

def get_columns(filters):	
        cols =  [
                { "fieldname": "name", "label": _("Activity Name"),  "fieldtype": "Link",  "options": "Project", "width": 200 },
		{ "fieldname": "expected_start_date", "label": _("Start Date"),  "fieldtype": "Date", "width": 80 },
		{ "fieldname": "expected_end_date", "label": _("End Date"),  "fieldtype": "Date", "width": 80 },
                { "fieldname": "total_duration", "label": _("Duration(Days)"),  "fieldtype": "Int", "width": 100 },
		{ "fieldname": "estimated_budget", "label": _("Estimated Budget"),  "fieldtype": "Currency", "width": 150 },
                { "fieldname": "expense_incured", "label": _("Actual Expense"),  "fieldtype": "Currency", "width": 130 },
                { "fieldname": "physical_progress_weightage", "label": _("Weightage(%)"),  "fieldtype": "Data",  "width": 100 },
		{ "fieldname": "project_engineer", "label": _("PM/PE ID"),  "fieldtype": "Link",  "options": "Employee", "width": 90 },
		{ "fieldname": "engineer_name", "label": _("PM/PE Name"),  "fieldtype": "Data", "width": 140 },
		{ "fieldname": "contact", "label": _("Contact No."),  "fieldtype": "Data", "width": 90 }
	]
	if not filters.get("project"):
                 cols.insert(6,{
                  "fieldname": "physical_progress",
                  "label": "Project Progress(%)",
                  "fieldtype": "Data",
                  "width": 140
                 })
                 cols.insert(7,{
                  "fieldname": "percent_completed",
                  "label": "Site Progress(%)",
                  "fieldtype": "Data",
                  "width": 140
                 })

	else:
		cols.insert(6,{
                  "fieldname": "physical_progress",
                  "label": "Site Progress(%)",
                  "fieldtype": "Data",
                  "width": 140
                 })
		cols.insert(7,{
                  "fieldname": "percent_completed",
                  "label": "Activity Progress(%)",
                  "fieldtype": "Data",
                  "width": 140
                 })
	return cols
