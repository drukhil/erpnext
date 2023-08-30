from __future__ import unicode_literals
import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def test():
        return frappe.db.sql(""" select name, employment_type from `tabEmployee`""", as_dict =True)



@frappe.whitelist(allow_guest=True)
def project_progress(project = 'GA-Tareythang - GYALSUNG'):
	from erpnext.projects.report.project_progress_graphs.project_progress_graphs import execute, get_periodic_data1, get_columns
 	filters = {'project': project,  'activity': 0, 'from_date':  '01-04-2020', 'to_date': '19-12-2023'} 
        data =  execute(filters)
    	#import json
	#json_format = json.dumps(data)
	#print(json_format)
	#print(type(json_format))
	#return json_format	
	
	return data

#return type(columns)

	
#print(filters.get('from_date'))
#data = execute(filters)
#return data

