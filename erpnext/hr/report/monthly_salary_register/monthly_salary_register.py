# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0          SSK                           03/08/2016         Taking care of Duplication of columns
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from erpnext.accounts.utils import get_child_cost_centers
from frappe.utils import flt, cstr
from frappe import msgprint, _

def execute(filters=None):
    if not filters: filters = {}
    data    = []
    columns = []
    if filters.get("report_type") == "Salary":
        salary_slips = get_salary_slips(filters)
    else:
        salary_slips = get_salary_arrears(filters)
    if not salary_slips:
                return columns, data
        
    columns, earning_types, ded_types = get_columns(salary_slips, filters)
    ss_earning_map = get_ss_earning_map(salary_slips)
    ss_ded_map = get_ss_ded_map(salary_slips)
    
    for ss in salary_slips:
        status = ""
        if ss.docstatus == 1:
            status = "Submitted"
        elif ss.docstatus == 0:
            status = "Un-Submitted"
        elif ss.docstatus == 2:
            status = "Cancelled"
        else:
            status = str(ss.docstatus)
        cid, joining_date = frappe.db.get_value("Employee", ss.employee, ["passport_number","date_of_joining"])
        if filters.get("report_type") == "Salary":
            row = [ss.employee, ss.employee_name, ss.employment_type, cid, joining_date,
                ss.bank_name, ss.bank_account_no, 
                ss.cost_center, ss.branch, ss.department,
                            ss.division, ss.section, ss.employee_grade, ss.designation, 
                ss.fiscal_year, ss.month, ss.leave_withut_pay, ss.payment_days,
                            status]
        else:
            row = [
                ss.employee,ss.employee_name, ss.employment_type, cid, joining_date,
                ss.bank_name, ss.bank_ac_no, 
                ss.cost_center, ss.branch, ss.department,
                ss.division, ss.employee_grade, ss.designation, 
                ss.fiscal_year, ss.from_month,
                status, ss.prev_basic_pay, ss.prev_corporate,
                ss.prev_contract, ss.prev_officiating, ss.prev_hc,
                ss.previous_pf, ss.previous_employer_pf, ss.previous_salary_tax,
                ss.basic_pay, ss.corporate_allowance,
                ss.contract_allowance, ss.officiating_allowance, ss.fixed_allowance, ss.health_contribution,
                ss.pf, ss.employer_pf, ss.salary_tax,
                ss.arrear_basic_pay, ss.arrear_corporate_allowance,
                ss.arrear_contract_allowance, ss.arrear_officiating_allowance, ss.arrear_hc,
                ss.arrear_pf, ss.arrear_employer_pf, ss.arrear_salary_tax, ss.total_deduction,
                ss.new_gross_pay, ss.net_payable_arrear
                ]
        if filters.get("report_type") == "Salary":
            for e in earning_types:
                row.append(ss_earning_map.get(ss.name, {}).get(e))
                
            row += [ss.arrear_amount, ss.leave_encashment_amount, ss.gross_pay]
            
            for d in ded_types:
                row.append(ss_ded_map.get(ss.name, {}).get(d))
            
            row += [ss.total_deduction, ss.net_pay]
        
        data.append(row)
    
    return columns, data
    
def get_columns(salary_slips, filters):
    if filters.get("report_type") == "Salary":
        columns = [
            _("Employee") + ":Link/Employee:80", _("Employee Name") + "::140", _("Employment Type") + ":Link/Employment Type:120",
            _("CID No") + "::120", _("Joining Date") + ":Date:100", _("Bank Name")+ "::80", _("Bank A/C#")+"::100", 
            #_("Company") + ":Link/Company:120",
            _("Cost Center") + ":Link/Cost Center:120",
                    _("Branch") + ":Link/Branch:120", _("Department") + ":Link/Department:120", _("Division") + ":Link/Division:120",
                    _("Grade") + ":Link/Employee Grade:120", _("Designation") + ":Link/Designation:120",
            _("Year") + "::80", _("Month") + "::80", _("Leave Without Pay") + ":Float:130", 
         _("Status") + "::100"
        ]
    else:
        columns = [
            _("Employee") + ":Link/Employee:80", _("Employee Name") + "::140", _("Employment Type") + ":Link/Employment Type:120",
            _("CID No") + " ::120", _("Joining Date") + ":Date:100", _("Bank Name")+ "::80", _("Bank A/C#")+"::100", 
            #_("Company") + ":Link/Company:120",
            _("Cost Center") + ":Link/Cost Center:120",
                    _("Branch") + ":Link/Branch:120", _("Department") + ":Link/Department:120", _("Division") + ":Link/Division:120",
                    _("Grade") + ":Link/Employee Grade:120", _("Designation") + ":Link/Designation:120",
            _("Year") + "::80", _("Month") + "::80", 
            _("Status") + "::100"
        ]
    earning_types = []
    ded_types     = []

    earning_types = frappe.db.sql_list("""select salary_component from `tabSalary Detail`
                        where amount != 0 and parent in (%s)
                        and parentfield = 'earnings'
                        group by salary_component
                        order by count(*) desc""" % 
                        (', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]))
        
    ded_types = frappe.db.sql_list("""select salary_component from `tabSalary Detail`
                        where amount != 0 and parent in (%s)
                        and parentfield = 'deductions'
                        group by salary_component
                        order by count(*) desc""" % 
                        (', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]))
    if filters.get("report_type") == "Salary":
        columns = columns + [(e + ":Currency:120") for e in earning_types] + \
                            ["Arrear Amount:Currency:120", "Leave Encashment Amount:Currency:150", 
                            "Gross Pay:Currency:120"] + [(d + ":Currency:120") for d in ded_types] + \
                            ["Total Deduction:Currency:120", "Net Pay:Currency:120"]
    else:
        columns = columns + ["Previous Basic Pay:Currency:120", "Previous Corporate Allowance:Currency:150", 
                            "Previous Contract Allowance:Currency:120", "Previous Officiating Allowance:Currency:150", "Previous Health Contribution:Currency:150",
                            "Previous PF:Currency:150", "Previous Employer PF:Currency:150", "Previous Salary Tax:Currency:150",
                            "New Basic Pay:Currency:120", "New Corporate Allowance:Currency:150", 
                            "New Contract Allowance:Currency:120", "New Officiating Allowance:Currency:150", "Fixed Allowance:Currency:150", "New Health Contribution:Currency:150",
                            "New PF:Currency:150", "New Employer PF:Currency:150", "New Salary Tax:Currency:150",
                            "Arrear Basic Pay:Currency:120", "Arrear Corporate Allowance:Currency:150", 
                            "Arrear Contract Allowance:Currency:120", "Arrear Officiating Allowance:Currency:150", "Arrear Health Contribution:Currency:150",
                            "Arrear PF:Currency:150", "Arrear Employer PF:Currency:150", "Arrear Salary Tax:Currency:150", "Total Arerar Deduction:Currency:150", "Arrear Gross Pay:Currency:150", "Net Arrear Payable:Currency:150"]

    return columns, earning_types, ded_types
    
def get_salary_slips(filters):
    conditions, filters = get_conditions(filters)
    salary_slips = frappe.db.sql("""select * from `tabSalary Slip` where 1 = 1 %s
        order by employee, month""" % conditions, filters, as_dict=1)

    '''
    if not salary_slips:
        msgprint(_("No salary slip found for month: ") + cstr(filters.get("month")) + 
            _(" and year: ") + cstr(filters.get("fiscal_year")), raise_exception=1)
        '''
    
    return salary_slips

def get_salary_arrears(filters):
    conditions, filters = get_arrear_conditions(filters)
    salary_slips = frappe.db.sql("""select sapi.*, sap.*, e.employee_subgroup as employee_grade, e.designation, e.employment_type, e.cost_center, e.branch, e.department, e.division from `tabSalary Arrear Payment` sap, `tabSalary Arrear Payment Item` sapi, `tabEmployee` e where e.name = sapi.employee and sapi.parent = sap.name {}
        order by sap.from_month, sap.fiscal_year""".format(conditions), as_dict=1)
    '''
    if not salary_slips:
        msgprint(_("No salary slip found for month: ") + cstr(filters.get("month")) + 
            _(" and year: ") + cstr(filters.get("fiscal_year")), raise_exception=1)
    '''
    
    return salary_slips

def get_arrear_conditions(filters):
    conditions = ""
    months = []
    month = None
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
            "Dec"]
    if filters.get("month"):
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
            "Dec"].index(filters.get("month")) + 1

    if month:
        months.append("'"+str(month_names[month-1])+"'")
        conditions += " and sap.from_month in ({})".format(", ".join(a for a in months))
    else:
        frappe.throw("From Month and To Month filters are mandatory")
    if filters.fiscal_year:
        conditions += " and sap.fiscal_year in ({})".format(filters.get("fiscal_year"))
    else:
        frappe.throw("Fiscal Year is mandatory")
    if filters.get("company"): conditions += " and sap.company = '{}'".format(filters.get("company"))
    if filters.get("employee"): conditions += " and sapi.employee = '{}'".format(filters.get("employee"))
    if filters.get("division"): conditions += " and e.division = '{}'".format(filters.get("division"))
    # if filters.get("section"): conditions += " and e.section = '{}'".format(filters.get("section"))
    # if filters.get("unit"): conditions += " and e.unit = '{}'".format(filters.get("unit"))
    # if filters.get("region"): conditions += " and e.region = '{}'".format(filters.get("region"))
    if filters.get("cost_center"):
        all_ccs = get_child_cost_centers(filters.cost_center)
        conditions += " and e.cost_center in {0} ".format(tuple(all_ccs))
        
    if filters.get("process_status") == "All":
            conditions += " and sap.docstatus = sap.docstatus"
    elif filters.get("process_status") == "Submitted":
            conditions += " and sap.docstatus = 1"
    elif filters.get("process_status") == "Un-Submitted":
            conditions += " and sap.docstatus = 0"
    elif filters.get("process_status") == "Cancelled":
            conditions += " and sap.docstatus = 2"

    return conditions, filters

def get_conditions(filters):
    conditions = ""
    if filters.get("month"):
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
            "Dec"].index(filters["month"]) + 1
        filters["month"] = month
        conditions += " and month = %(month)s"
    
    if filters.get("fiscal_year"): conditions += " and fiscal_year = %(fiscal_year)s"
    if filters.get("company"): conditions += " and company = %(company)s"
    if filters.get("employee"): conditions += " and employee = %(employee)s"
    if filters.get("division"): conditions += " and division = %(division)s"
    if filters.get("cost_center"):
        all_ccs = get_child_cost_centers(filters.cost_center)
        conditions += " and cost_center in {0} ".format(tuple(all_ccs))
        
        if filters.get("process_status") == "All":
                conditions += " and docstatus = docstatus"
        elif filters.get("process_status") == "Submitted":
                conditions += " and docstatus = 1"
        elif filters.get("process_status") == "Un-Submitted":
                conditions += " and docstatus = 0"
        elif filters.get("process_status") == "Cancelled":
                conditions += " and docstatus = 2"

    
    return conditions, filters
    
def get_ss_earning_map(salary_slips):
    ss_earning_map = {}

    ss_earnings = frappe.db.sql("""select parent, salary_component, sum(ifnull(amount,0)) as amount 
                        from `tabSalary Detail` where parent in (%s)
                        and parentfield = 'earnings'
                        group by parent, salary_component
                        """ %
                        (', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)
                
    for d in ss_earnings:
        ss_earning_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, [])
        ss_earning_map[d.parent][d.salary_component] = flt(d.amount)
    
    return ss_earning_map

def get_ss_ded_map(salary_slips):
    ss_deductions = frappe.db.sql("""select parent, salary_component, sum(ifnull(amount,0)) as amount 
        from `tabSalary Detail` where parent in (%s)
        and parentfield = 'deductions'
        group by parent, salary_component
        """ %
        (', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)
    
    ss_ded_map = {}
    for d in ss_deductions:
        ss_ded_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, [])
        ss_ded_map[d.parent][d.salary_component] = flt(d.amount)
    
    return ss_ded_map
