# Copyright (c) 2016, Druk Holding & Investments Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

'''
---------------------------------------------------------------------------------------------------------------------------
Version          Author            CreatedOn          ModifiedOn          Remarks
------------ ---------------  ------------------ -------------------  -----------------------------------------------------
2.0#CDCL#886      SSK	          06/09/2018                          Moved retirement_age, health_contribution, employee_pf,
                                                                         employer_pf from "HR Settings" to "Employee Group"
---------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, date_diff, nowdate
from frappe.utils.data import get_first_day, get_last_day, add_days
from erpnext.custom_utils import get_year_start_date, get_year_end_date
import json
import logging

# ++++++++++++++++++++ VER#2.0#CDCL#886 BEGINS ++++++++++++++++++++
# VER#2.0#CDCL#886: Following method introduced by SHIV on 02/10/2018
def post_leave_credits(today=None):
        """
           :param today: First day of the month
           :param employee: Employee id for individual allocation
           
           This method allocates leaves in bulk as per the leave credits defined in Employee Group master.
           It is mainly used for allocating monthly and yearly leave credits automatically through hooks.py.
           However, it can also be used for allocating manually if in case the automatic allocation failed
           for some reason.

           To run manually: Just pass the first day of the month to this method as argument. Following example
                   allocates monthly credits for the period from '2019-01-01' till '2019-01-31', and yearly
                   credits for the period from '2019-01-01' till '2019-12-31' as defined in Employee Group
                   master for all the leave types except `Earned Leave`. Monthly credits for `Earned Leave`
                   are allocated for the previous month i.e from '2018-12-01' till '2018-12-31'.

                   Example:
                        # Executing from console
                        bench execute erpnext.hr.hr_custom_functions.post_leave_credits --args "'2019-01-01',"
        """

        # Logging
        logging.basicConfig(format='%(asctime)s|%(name)s|%(levelname)s|%(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        
        today      = getdate(today) if today else getdate(nowdate())
        start_date = ''
        end_date   = ''

        first_day_of_month = 1 if today.day == 1 else 0
        first_day_of_year  = 1 if today.day == 1 and today.month == 1 else 0
                
	#if first_day_of_month or first_day_of_year:
        f_date = get_first_day(add_days(today, -today.day))
        t_date   = get_last_day(f_date)
	elist = frappe.db.sql("""
		select
			t1.name, t1.employee_name, t1.date_of_joining,
			(
			case
				when day(t1.date_of_joining) > 1 and day(t1.date_of_joining) <= 15
				then timestampdiff(MONTH,t1.date_of_joining,'{0}')+1 
				else timestampdiff(MONTH,t1.date_of_joining,'{0}')       
			end
			) as no_of_months,
			t2.leave_type, t2.credits_per_month, t2.credits_per_year,
			t3.is_carry_forward
		from `tabEmployee` as t1, `tabEmployee Group Item` as t2, `tabLeave Type` as t3
		where t1.status = 'Active'
		and t1.date_of_joining <= '{0}'
		and t1.employee_group = t2.parent
		and (t2.credits_per_month > 0 or t2.credits_per_year > 0)
		and t3.name = t2.leave_type
		and not exists(select 1
                                      from `tabLeave Allocation` as t4
                                      where t4.employee = t1.name
                                      and t4.docstatus != 2
                                      and t4.from_date = '{1}'
                                      and t4.to_date = '{2}'
                                      and t4.leave_type = t3.name
                                      )

		order by t1.name, t2.leave_type
	""".format(str(today), f_date, t_date), as_dict=1)

	counter = 0
	for e in elist:
		counter += 1
		leave_allocation = []
		credits_per_month = 0
		credits_per_year = 0
		
		if flt(e.no_of_months) <= 0:
			logger.error("{0}|{1}|{2}|{3}|{4}".format("NOT QUALIFIED",counter,e.name,e.employee_name,e.leave_type))
			continue

		# Monthly credits
		if flt(e.credits_per_month) > 0:
			# For Earned Leaved monthly credits are given for previous month
			if e.leave_type == "Earned Leave":
				start_date = get_first_day(add_days(today, -20))
				#start_date = get_first_day(add_days(today, -today.day))
				end_date   = get_last_day(start_date)
			else:
				start_date = get_first_day(today)
				end_date   = get_last_day(start_date)

			leave_allocation.append({
				'from_date': str(start_date),
				'to_date': str(end_date),
				'new_leaves_allocated': flt(e.credits_per_month)
			})

		# Yearly credits
		if first_day_of_year and flt(e.credits_per_year) > 0:
			start_date = get_year_start_date(today)
			end_date   = get_year_end_date(start_date)

			leave_allocation.append({
				'from_date': str(start_date),
				'to_date': str(end_date),
				'new_leaves_allocated': flt(e.credits_per_year)
			})

		for la in leave_allocation:
			if not frappe.db.exists("Leave Allocation", {"employee": e.name, "leave_type": e.leave_type, "from_date": la['from_date'], "to_date": la['to_date'], "docstatus": ("<",2)}):
					
				try:
					doc = frappe.new_doc("Leave Allocation")
					doc.employee             = e.name
					doc.employee_name        = e.employee_name
					doc.leave_type           = e.leave_type
					doc.from_date            = la['from_date']
					doc.to_date              = la['to_date']
					doc.carry_forward        = cint(e.is_carry_forward)
					doc.new_leaves_allocated = flt(la['new_leaves_allocated'])
					doc.submit()
					logger.info("{0}|{1}|{2}|{3}|{4}|{5}".format("SUCCESS",counter,e.name,e.employee_name,e.leave_type,flt(la['new_leaves_allocated'])))
				except Exception as ex:
					logger.exception("{0}|{1}|{2}|{3}|{4}|{5}".format("FAILED",counter,e.name,e.employee_name,e.leave_type,flt(la['new_leaves_allocated'])))
				'''
				if e.leave_type == "Earned Leave":	
					print("Leave Credit" + str(la['new_leaves_allocated']) + "leave Type :" + e.leave_type + "Employee :" + e.name + " Employee Name: "+ e.employee_name + "From Date :" +str(la['from_date']))
				'''
			else:
				logger.warning("{0}|{1}|{2}|{3}|{4}|{5}".format("ALREADY ALLOCATED",counter,e.name,e.employee_name,e.leave_type,flt(la['new_leaves_allocated'])))
#        else:
#                logger.info("Date {0} is neither beginning of the month nor year".format(str(today)))
#                return 0
        
# +++++++++++++++++++++ VER#2.0#CDCL#886 ENDS +++++++++++++++++++++

##
# Post casual leave on the first day of every month
##
def post_casual_leaves():
	date = getdate(frappe.utils.nowdate())
	if not (date.month == 1 and date.day == 1):
		return 0
	date = add_days(frappe.utils.nowdate(), 10)
	start = get_year_start_date(date);
	end = get_year_end_date(date);
	employees = frappe.db.sql("select name, employee_name from `tabEmployee` where status = 'Active'", as_dict=True)
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

##
# Post earned leave on the first day of every month
##
def post_earned_leaves():
	if not getdate(frappe.utils.nowdate()) == getdate(get_first_day(frappe.utils.nowdate())):
		return 0
 
	date = add_days(frappe.utils.nowdate(), -20)
	start = get_first_day(date);
	end = get_last_day(date);
	
	employees = frappe.db.sql("select name, employee_name, date_of_joining from `tabEmployee` where status = 'Active'", as_dict=True)
	for e in employees:
		if cint(date_diff(end, getdate(e.date_of_joining))) > 14:
			la = frappe.new_doc("Leave Allocation")
			la.employee = e.name
			la.employee_name = e.employee_name
			la.leave_type = "Earned Leave"
			la.from_date = str(start)
			la.to_date = str(end)
			la.carry_forward = cint(1)
			la.new_leaves_allocated = flt(2.5)
			la.submit()
		else:
			pass

#function to get the difference between two dates
@frappe.whitelist()
def get_date_diff(start_date, end_date):
	if start_date is None:
		return 0
	elif end_date is None:
		return 0
	else:	
		return frappe.utils.data.date_diff(end_date, start_date) + 1;

# Ver 1.0 added by SSK on 04/08/2016, Fetching TDS component
@frappe.whitelist()
def get_salary_tax(gross_amt):
        tax_amount = 0
        max_limit = frappe.db.sql("""select max(b.upper_limit)
                from `tabSalary Tax` a, `tabSalary Tax Item` b
                where now() between a.from_date and ifnull(a.to_date, now())
                and b.parent = a.name
                """)

        if flt(flt(gross_amt) if flt(gross_amt) else 0.00) > flt(flt(max_limit[0][0]) if flt(max_limit[0][0]) else 0.00):
               # tax_amount = flt((((flt(gross_amt) if flt(gross_amt) else 0.00)-83333.00)*0.25)+11875.00)
            tax_amount = flt((((flt(gross_amt) if flt(gross_amt) else 0.00)-125000.00)*0.30)+20208.00)
        else:
                result = frappe.db.sql("""select b.tax from
                        `tabSalary Tax` a, `tabSalary Tax Item` b
                        where now() between a.from_date and ifnull(a.to_date, now())
                        and b.parent = a.name
                        and %s between b.lower_limit and b.upper_limit
                        limit 1
                        """,gross_amt)
                if result:
                        tax_amount = flt(result[0][0])
                else:
                        tax_amount = 0

        return tax_amount

# ++++++++++++++++++++ VER#2.0#CDCL#886 BEGINS ++++++++++++++++++++
# VER#2.0#CDCL#886: Following code is commented by SHIV on 06/09/2018
'''		
# Ver 1.0 added by SSK on 03/08/2016, Fetching PF component
@frappe.whitelist()
def get_company_pf(fiscal_year=None, employee=None):
	employee_pf = frappe.db.get_single_value("HR Settings", "employee_pf")
	if not employee_pf:
		frappe.throw("Setup Employee PF in HR Settings")
	employer_pf = frappe.db.get_single_value("HR Settings", "employer_pf")
	if not employer_pf:
		frappe.throw("Setup Employer PF in HR Settings")
	health_contribution = frappe.db.get_single_value("HR Settings", "health_contribution")
	if not health_contribution:
		frappe.throw("Setup Health Contribution in HR Settings")
	retirement_age = frappe.db.get_single_value("HR Settings", "retirement_age")
	if not retirement_age:
		frappe.throw("Setup Retirement Age in HR Settings")
        result = ((flt(employee_pf), flt(employer_pf), flt(health_contribution), flt(retirement_age)),)
	return result

# Ver 1.0 added by SSK on 04/08/2016, Fetching GIS component
@frappe.whitelist()
def get_employee_gis(employee):
        #msgprint(employee);
        result = frappe.db.sql("""select a.gis
                from `tabEmployee Grade` a, `tabEmployee` b
                where b.employee = %s
                and b.employee_group = a.employee_group
                and b.employee_subgroup = a.name
                limit 1
                """,employee);

        if result:
                return result[0][0]
        else:
                return 0.0
'''

# VER#2.0#CDCL#886: Following code is added by SHIV on 06/09/2018
@frappe.whitelist()
def get_payroll_settings(employee=None):
        settings = {}
        if employee:
                settings = frappe.db.sql("""
                        select
                                e.employee_group,
                                e.employee_subgroup,
                                d.gis,
                                g.health_contribution,
                                g.employee_pf,
                                g.employer_pf
                        from `tabEmployee` e, `tabEmployee Group` g, `tabEmployee Grade` d
                        where e.name = '{0}'
                        and g.name = e.employee_group
                        and d.employee_group = g.name
                        and d.name = e.employee_subgroup
                """.format(employee), as_dict=True);
        settings = settings[0] if settings else settings
        return settings
# +++++++++++++++++++++ VER#2.0#CDCL#886 ENDS +++++++++++++++++++++

@frappe.whitelist()
def get_month_details(year, month):
	ysd = frappe.db.get_value("Fiscal Year", year, "year_start_date")
	if ysd:
		from dateutil.relativedelta import relativedelta
		import calendar, datetime
		diff_mnt = cint(month)-cint(ysd.month)
		if diff_mnt<0:
			diff_mnt = 12-int(ysd.month)+cint(month)
		msd = ysd + relativedelta(months=diff_mnt) # month start date
		month_days = cint(calendar.monthrange(cint(msd.year) ,cint(month))[1]) # days in month
		med = datetime.date(msd.year, cint(month), month_days) # month end date
		return frappe._dict({
			'year': msd.year,
			'month_start_date': msd,
			'month_end_date': med,
			'month_days': month_days
		})
	else:
		frappe.throw(_("Fiscal Year {0} not found").format(year))
