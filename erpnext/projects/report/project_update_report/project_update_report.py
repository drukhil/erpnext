# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
        data    = get_data(filters)
        columns = get_columns()
	return columns, data

def get_data(filters):
        
        data = frappe.db.sql("""
                        select project as activity, posting_date, percent_completed
                        from  `tabAchievement Entry Sheet`  
                        where project    = "{0}"
                        
                        order by posting_date asc 
                        """.format(filters.get("activity")), as_dict=1)

        
        return data
        
def get_columns():
        return [
                {
                        "fieldname": "activity",
                        "label": ("Project"),
                        "fieldtype": "Link",
                        "options": "Project",
                        "width": 400
                },
                {
                        "fieldname": "posting_date",
                        "label": ("Update Date"),
                        "width": 150
                },
                {
                        "fieldname": "percent_completed",
                        "label": ("Percent Updated"),
                        "fieldtype": "float",
                        "width": 100
                },
                # {
                #         "fieldname": "posting_date",
                #         "label": _("Update Date"),
                #         "width": 150
                # },
                # {
                #         "fieldname": "designation",
                #         "label": _("Designation"),
                #         "width": 150
                # },
               
                # {
                #         "fieldname": "branch",
                #         "label": _("Branch"),
                #         "fieldtype": "Link",
                #         "options": "Branch",
                #         "width": 100
                # },
               
        ]

