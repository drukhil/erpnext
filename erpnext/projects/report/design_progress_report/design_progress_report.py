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
	# data = []
	data = """ select b.parent_project, b.expected_start_date, b.expected_end_date, a.weightage as weightage,  round(sum(b.physical_progress * 100),3) as physical_progress, round((a.weightage * sum(b.physical_progress)), 3) as achivement,
		  b.status, b.architecture, b.a_name, b.contact from `tabDesign Weightage Item` a left join `tabDesign` b on b.parent_project= a.parent_project where a.docstatus <= 1  group by parent_project"""
	# data.append(1,2,3,4,5,6)
	cond = ""
	if filters.get("project"):
		data = """ select name,  expected_start_date, expected_end_date, physical_progress_weightage, percent_completed, (percent_completed*physical_progress_weightage) as achivement,
			
		  status, architecture, a_name, contact from `tabDesign` where docstatus <= 1 """
		 
		cond = """ and parent_project = "{0}" """.format(filters.get("project"))
		data +=cond
	if filters.get("activity"):
		data = """ select name,  expected_start_date, expected_end_date, physical_progress_weightage, percent_completed, (percent_completed*physical_progress_weightage) as achivement,
			 
		  status, architecture, a_name, contact from `tabDesign` where docstatus <= 1 """
		cond = """ and name = "{0}" """.format(filters.get("activity"))
		data +=cond
	# if filters.get("status"):
	# 	cond += " and status = '{0}'".format(filters.get('status'))
	
	
	
	return frappe.db.sql(data)

def get_columns(filters):
        return [
        { "fieldname": "name", 
				"label": _("Activity Name"), 
				 "fieldtype": "Link", 
				  "options": "Design",
				   "width": 200 },
		{ "fieldname": "expected_start_date", 
		"label": _("Start Date"), 
		 "fieldtype": "Date",
		  "width": 80 },
		{ "fieldname": "expected_end_date",
		 "label": _("End Date"), 
		  "fieldtype": "Date", 
		  "width": 80 },
     
        { "fieldname": "physical_progress_weightage",
		 "label": _("Weightage(%)"), 
		  "fieldtype": "Float", 
		   "width": 100 },
		   { "fieldname": "percent_completed", 
		"label": _("Progress(%)"), 
		 "fieldtype": "Float", 
		 "width": 100 },
        { "fieldname": "physical_progress",
		 "label": _("Achievement(%)"), 
		  "fieldtype": "Float",
		   "width": 120 },	
		
        { "fieldname": "status", 
		"label": _("Status"), 
		"fieldtype": "Data",
		 "width": 100 },
		{ "fieldname": "project_engineer", "label": _("Architecture ID"),  "fieldtype": "Link",  "options": "Employee", "width": 90 },
		{ "fieldname": "engineer_name", "label": _("Architecture Name"),  "fieldtype": "Data", "width": 140 },
		{ "fieldname": "contact", "label": _("Contact No."),  "fieldtype": "Data", "width": 90 }
	]
