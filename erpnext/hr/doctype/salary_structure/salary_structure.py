# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0		  SSK		                   03/08/2016         Following functions introducted
                                                                          i) get_employee_pf: fetching pf component
1.0               SSK                              04/08/2016         Following functions introducted
                                                                          i) get_employee_gis : fetching employee gis
                                                                          ii)get_salary_tax : fetching tds
1.0               SSK                              08/08/2016         Changes made to accommodate erpnext v7 changes
                                                                          i) Displaying only Earnings on earnings side
                                                                          ii) Displaying only Deductions on deductions side
1.0               SSK                              23/08/2016         Introducing Monthly Salary Deductions
1.0               SSK                              25/08/2016         Updating branch, department, division in salary slip
                                                                        as per employee record as on processing date
1.0               SSK                              27/08/2016         Salary Structure Overlap rectification
1.0               SSK                              28/08/2016         Added employee_subgroup to Salary Slip
1.0               SSK                              29/08/2016         Added method calculate_totals for use in
                                                                        Salary Increment
2.0               SSK                              27/02/2018         Methods
                                                                                validate_salary_component()
                                                                                salary_component_query()
                                                                        introducted inorder to restrict user from making
                                                                        mistakes by adding deduction salary_component type
                                                                        under earnings table vice versa.
2.0.190429        SHIV                             27/12/2019         * Introduced is_pf_deductible under salary component                                                                        
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe

from frappe import msgprint
from frappe.utils import cstr, flt, cint, getdate, date_diff, nowdate
from frappe.utils.data import get_first_day, get_last_day, add_days
from frappe.model.naming import make_autoname
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name
from erpnext.hr.hr_custom_functions import get_month_details, get_payroll_settings, get_salary_tax
from erpnext.accounts.accounts_custom_functions import get_number_of_days
from erpnext.custom_utils import nvl
from frappe.desk.reportview import get_match_cond
import operator

class SalaryStructure(Document):
	def autoname(self):
		self.name = make_autoname(self.employee + '/.SST' + '/.#####')
		
	def validate(self):
		if self.is_active == 'No' and not self.to_date:
			frappe.throw("To Date is mandatory for Non Active Salary Structures")
		self.check_overlap()
		self.validate_amount()
		self.validate_employee()
		self.validate_joining_date()
		set_employee_name(self)
		self.check_multiple_active()
		self.update_salary_structure()
                self.get_employee_details()
	
		if self.employment_type == 'GEP':
			self.depend_salary_on_attendance = 1

	def on_update(self):
		self.assign_employee_details()

        # Ver 2.0, following method introduced by SHIV on 2018/02/2017
        def validate_salary_component(self):
                dup = {}
                for parentfield in ['earnings','deductions']:
                        parenttype = 'Earning' if parentfield == 'earnings' else 'Deduction'
                        for i in self.get(parentfield):
                                # Restricting users from entering earning component under deductions table and vice versa.
                                component_type = frappe.db.get_value("Salary Component",i.salary_component,"type")
                                if parenttype != component_type:
                                        frappe.throw(_('Salary Component <b>`{1}`</b> of type <b>`{2}`</b> cannot be added under <b>`{3}`</b> table. <br/> <b><u>Reference# : </u></b> <a href="#Form/Salary Structure/{0}">{0}</a>').format(self.name,i.salary_component,component_type,parentfield.title()),title="Invalid Salary Component")

                                # Checking duplicate entries 
                                if i.salary_component in ('Basic Pay') and i.salary_component in dup:
                                        frappe.throw(_("Row#{0} : Duplicate entries not allowed for component <b>{1}</b>.").format(i.idx,i.salary_component),title="Duplicate Record Found")
                                else:
                                        dup.update({i.salary_component: 1})
        
	def get_employee_details(self):
                emp = frappe.get_doc("Employee", self.employee)
                for a in emp.external_work_history:
                        self.parent_organization = a.company_name
                self.employee_name      = emp.employee_name
		self.branch             = emp.branch
		self.designation        = emp.designation
		self.employment_type    = emp.employment_type
		self.employee_group     = emp.employee_group
		self.employee_grade     = emp.employee_subgroup
		self.department         = emp.department
                self.division           = emp.division
                self.section            = emp.section
		self.backup_employee    = self.employee
				
	def get_ss_values(self,employee):
		basic_info = frappe.db.sql("""select bank_name, bank_ac_no
			from `tabEmployee` where name =%s""", employee)
		ret = {'bank_name': basic_info and basic_info[0][0] or '',
			'bank_ac_no': basic_info and basic_info[0][1] or ''}
		return ret

	def make_table(self, doct_name, tab_fname, tab_name):
                # Ver 1.0 by SSK on 08/08/2016, Following line is commented and the subsequent if condition is added
                #list1 = frappe.db.sql("select name from `tab%s` where docstatus != 2" % doct_name)
                if (tab_fname == 'earnings'):
                        list1 = frappe.db.sql("select * from `tab{0}` where `docstatus` != 2 and `type` = 'Earning' and `default` = 1".format(doct_name), as_dict=True)
                else:
                        list1 = frappe.db.sql("select * from `tab{0}` where `docstatus` != 2 and `type` = 'Deduction' and `default` = 1".format(doct_name), as_dict=True)
                        
		for li in list1:
                        child = self.append(tab_fname, {})
			if(tab_fname == 'earnings'):
				child.salary_component = li.name
				child.amount = flt(li.default_amount)
			elif(tab_fname == 'deductions'):
				child.salary_component = li.name
				child.amount = flt(li.default_amount)
				
	def make_earn_ded_table(self):
		#self.make_table('Salary Component','earnings','Salary Detail')
		#self.make_table('Salary Component','deductions', 'Salary Detail')
		tbl_list = {'earnings': 'Earning', 'deductions': 'Deduction'}
		for ed in tbl_list:
                        sc_list = frappe.db.sql("select * from `tabSalary Component` where `docstatus` != 2 and `type` = '{0}'".format(tbl_list[ed]), as_dict=True)
                        for sc in sc_list:
                                if sc.default:
                                        child = self.append(ed, {})
                                        child.salary_component = sc.name
                                        if sc.type == 'Earning':
                                                child.amount = flt(sc.default_amount) if sc.payment_method == 'Lumpsum' else 0
                                        else:
                                                child.amount = flt(sc.default_amount)
                                        vars(self)[sc.field_name] = sc.default
                                vars(self)[sc.field_method] = sc.payment_method
                                vars(self)[sc.field_value]  = flt(sc.default_amount)
                                
	def check_overlap(self):
		existing = frappe.db.sql("""select name from `tabSalary Structure`
			where employee = %(employee)s and
			(
				(%(from_date)s >= ifnull(from_date,'0000-00-00') and %(from_date)s <= ifnull(to_date,'2199-12-31')) or
				(%(to_date)s >= ifnull(from_date,'0000-00-00') and %(to_date)s <= ifnull(to_date,'2199-12-31')) or
				(%(from_date)s <= ifnull(from_date,'0000-00-00') and %(to_date)s >= ifnull(to_date,'2199-12-31')))
			and name!=%(name)s
			and docstatus < 2""",
			{
				"employee": self.employee,
				"from_date": self.from_date,
				"to_date": self.to_date,
				"name": self.name or "No Name"
			}, as_dict=True)
			
		if existing:
			frappe.throw(_("Salary structure {0} already exist, more than one salary structure for same period is not allowed").format(existing[0].name))

	def validate_amount(self):
		if flt(self.net_pay) < 0 and self.salary_slip_based_on_timesheet:
			frappe.throw(_("Net pay cannot be negative"))

	def validate_employee(self):
		old_employee = frappe.db.get_value("Salary Structure", self.name, "employee")
		if old_employee and self.employee != old_employee:
			frappe.throw(_("Employee can not be changed"))

	def validate_joining_date(self):
		joining_date = getdate(frappe.db.get_value("Employee", self.employee, "date_of_joining"))
		if getdate(self.from_date) < joining_date:
			frappe.throw(_("From Date in Salary Structure cannot be lesser than Employee Joining Date."))

	def assign_employee_details(self):
		if self.employee:
			doc = frappe.get_doc("Employee", self.employee)
			self.db_set("employee_name", doc.employee_name)
			self.db_set("branch", doc.branch)
			self.db_set("department", doc.department)
			self.db_set("division", doc.division)
			self.db_set("section", doc.section)
			self.db_set("employment_type", doc.employment_type)
			self.db_set("employee_group", doc.employee_group)
			self.db_set("employee_grade", doc.employee_subgroup)
			self.db_set("designation", doc.designation)

	def check_multiple_active(self):
		if self.is_active == 'Yes':
			result = frappe.db.sql("select 1 from `tabSalary Structure` where employee = %s and is_active = \'Yes\' and name != %s", (self.employee, self.name))
			if result:
				frappe.throw("Can not have multiple 'Active' Salary Structures")

        # ++++++++++++++++++++ VER#2.0#CDCL#886 BEGINS ++++++++++++++++++++
        # Following code added by SHIV on 06/09/2018
        def update_salary_structure(self, new_basic_pay=0):
                '''
                    This method calculates all the allowances and deductions based on the preferences
                    set in the GUI. Calculated values are then checked and updated as follows.
                            1) If the calculated component is missing in the existing earnings/deductions
                                table then insert a new row.
                            2) If the calculated component is found in the existing earnings/deductions
                                table but amounts do not match, then update the respective row.
                '''
                self.validate_salary_component()
                
                basic_pay = comm_allowance = gis_amt = pf_amt = health_cont_amt = tax_amt = 0
                ### Ver.2.0.191227 Begins, added by SHIV on 2019/12/27
                # Following variables introduced
                basic_pay_arrears = 0
                basic_pay_arrears_pf = 0
                ### Ver.2.0.191227 Ends
                
                total_earning = total_deduction = net_pay = 0
                settings      = get_payroll_settings(self.employee)
                settings      = settings if settings else {}
                
                tbl_list      = {'earnings': 'Earning', 'deductions': 'Deduction'}

                for ed in ['earnings','deductions']:
                        add_list = []
                        del_list = []
                        calc_map = []

                        sst_map = {}
                        for sc in frappe.db.sql("select * from `tabSalary Component` where `type`='{0}' and field_name is not null".format(tbl_list[ed]), as_dict=True):
				sst_map.setdefault(ed,[]).append(sc)
                        ed_map = [i.name for i in sst_map[ed]]

                        # Update Basic Pay if new_basic_pay has value(from salary increments), and remove
                        #  components if not eligible from earnings and deductions tables. 
                        for ed_item in self.get(ed):
                                amount = flt(ed_item.amount)
                                if ed_item.salary_component not in ed_map:
                                        if ed == 'earnings':
                                                if ed_item.salary_component == 'Basic Pay':
                                                        if flt(new_basic_pay) > 0 and flt(new_basic_pay) != flt(amount):
                                                                amount = flt(new_basic_pay)
                                                        basic_pay = amount
                                                        ed_item.amount = basic_pay
                                                ### Ver.2.0.20191227 Begins, added by SHIV on 2019/12/27
                                                # Following condition added by SHIV on 2019/12/27
                                                elif frappe.db.exists("Salary Component", {"name": ed_item.salary_component, "is_pf_deductible": 1}):
                                                        if flt(ed_item.amount):
                                                                basic_pay_arrears += flt(ed_item.amount)
                                                                off_cycle_pf = frappe.db.get_value("Salary Component", ed_item.salary_component, "off_cycle_pf")
                                                                if flt(off_cycle_pf) > 0:
                                                                        basic_pay_arrears_pf += flt(ed_item.amount)*flt(off_cycle_pf)*0.01
                                                                elif not flt(off_cycle_pf):
                                                                        basic_pay_arrears_pf += round(flt(ed_item.amount)*flt(settings.get("employee_pf"))*0.01)
                                                ### Ver.2.0.20191227 Ends
                                                total_earning += round(amount)
                                        else:
                                                total_deduction += round(amount)
                                else:
                                        for m in sst_map[ed]:
                                                if m['name'] == ed_item.salary_component and not self.get(m['field_name']):
                                                        del_list.append(ed_item)
                        [self.remove(d) for d in del_list]

                        # Calculating Earnings and Deductions based on preferences and values set
                        for m in sst_map[ed]:
				calc_amt = 0
				if self.get(m['field_method']) == 'Percent' and flt(self.get(m['field_value'])) > 100:
					if m['name'] != 'Contract Allowance':
						frappe.throw(_("Percentage cannot exceed 100 for component <b>{0}</b>").format(m['name']), title="Invalid Data")	
				if ed =='earnings':
                                	if self.get(m['field_name']):
                                        	calc_amt = round(flt(basic_pay)*flt(self.get(m['field_value']))*0.01 if self.get(m['field_method']) == 'Percent' else flt(self.get(m['field_value'])))
                                                comm_allowance += round(flt(calc_amt) if m['name'] == 'Communication Allowance' else 0)
                                                total_earning += calc_amt
                                                calc_map.append({'salary_component': m['name'], 'amount': calc_amt})
                                else:
                                        if self.get(m['field_name']) and m['name'] == 'SWS':
                                                sws_amt = round(flt(settings.get("sws_contribution")))
                                                #sws_amt = 0.0
						#sws_amt = frappe.get_doc("Employee Grade", self.employee_grade).sws_contribution
						calc_amt = flt(sws_amt)
                                                calc_map.append({'salary_component': m['name'], 'amount': flt(sws_amt)})
                                        
					if self.get(m['field_name']) and m['name'] == 'Group Insurance Scheme':
                                                gis_amt  = round(flt(settings.get("gis")))
                                                calc_amt = gis_amt
                                                calc_map.append({'salary_component': m['name'], 'amount': flt(gis_amt)})
                                        elif self.get(m['field_name']) and m['name'] == 'PF':
                                                pf_amt   = round(flt(basic_pay)*flt(settings.get("employee_pf"))*0.01)
                                                ### Ver.2.0.191227 Begins, by SHIV on 2019/12/27
                                                # Following code added by SHIV to introduce is_pf_deductible logic
                                                pf_amt  += basic_pay_arrears_pf
                                                ### Ver.2.0.191227 Ends
                                                calc_amt = pf_amt
                                                calc_map.append({'salary_component': m['name'], 'amount': flt(pf_amt)})
                                        elif self.get(m['field_name']) and m['name'] == 'Health Contribution':
                                                health_cont_amt = round(flt(total_earning)*flt(settings.get("health_contribution"))*0.01)
                                                calc_amt = health_cont_amt
                                                calc_map.append({'salary_component': m['name'], 'amount': flt(health_cont_amt)})                                        	
					else:
                                                calc_amt = 0
                                        total_deduction += calc_amt

                        # Calculating Salary Tax
                        if ed == 'deductions':
                                tax_amount = round(get_salary_tax(flt(total_earning)-flt(pf_amt)-flt(gis_amt)-(comm_allowance*0.5)))
                                total_deduction += tax_amount
                                calc_map.append({'salary_component': 'Salary Tax', 'amount': flt(tax_amount)})

                        # Updating existing Earnings and Deductions tables
                        for c in calc_map:
                                found = 0
                                for ed_item in self.get(ed):
                                        if ed_item.salary_component == c['salary_component']:
                                                found = 1
                                                if flt(ed_item.amount) != flt(c['amount']):
                                                        ed_item.amount = flt(c['amount'])
                                if not found:
                                        add_list.append(c)

                        [self.append(ed,i) for i in add_list]
                                        
                self.total_earning = flt(total_earning)
                self.total_deduction = flt(total_deduction)
                self.net_pay = flt(total_earning)-flt(total_deduction)

                if flt(total_earning)-flt(total_deduction) < 0:
                        frappe.throw(_("Total deduction cannot be more than total earning."), title="Invalid Data")
                        
        # +++++++++++++++++++++ VER#2.0#CDCL#886 ENDS +++++++++++++++++++++

@frappe.whitelist()
def make_salary_slip(source_name, target_doc=None, calc_days={}):
	def postprocess(source, target):
                gross_amt = 0.00
		comm_amt  = 0.00
		basic_amt = 0.00
		deput_amt = 0.00
		hra_amt = 0.00
		gross_amt1 = 0.00
		tax_amt1  = 0.00
                ### Ver.2.0.191227 Begins, added by SHIV on 2019/12/27
                # Following variables introduced
                basic_pay_arrears = 0
                basic_pay_arrears_pf = 0
                ### Ver.2.0.191227 Ends
                settings  = get_payroll_settings(source.employee)
		m_details = get_month_details(target_doc.fiscal_year, target_doc.month)

                target.gross_pay = 0
                target.total_deduction = 0
                target.net_pay = 0
                target.rounded_total = 0
                target.actual_basic = 0
                
                if calc_days:
                        start_date   = calc_days.get("from_date")
                        end_date     = calc_days.get("to_date")
                        days_in_month= calc_days.get("total_days_in_month")
                        working_days = calc_days.get("working_days")
                        lwp          = calc_days.get("leave_without_pay")
                        payment_days = calc_days.get("payment_days")

			if source.depend_salary_on_attendance:
                                absent_days = calc_days.get("absent_days")

                else:
                        return

		# Copy earnings and deductions table from source salary structure
		calc_map = {}
		full_basic = 0.0
		for key in ('earnings', 'deductions'):
			for d in source.get(key):
                                amount          = flt(d.amount)
                                deductible_amt  = 0.0
                                deducted_amt    = 0.0
                                outstanding_amt = 0.0
				if d.salary_component == 'Basic Pay':
                                        full_basic = amount

                                if d.from_date:
                                        if (start_date <= d.from_date <= end_date) or ((d.from_date <= end_date) and (nvl(d.to_date,end_date) >= start_date)):                
                                                if key == 'deductions':
                                                        if flt(d.total_deductible_amount) > 0:
                                                                if flt(d.total_outstanding_amount) > 0:
                                                                        if flt(amount) >= flt(d.total_outstanding_amount):
                                                                                amount = flt(d.total_outstanding_amount)
                                                                else:
                                                                        amount = 0
                                        else:
                                                amount = 0                
                                elif d.to_date:
                                        if (start_date <= d.to_date <= end_date) or ((d.to_date >= start_date) and (nvl(d.from_date,start_date) <= end_date)):
                                                if key == 'deductions':
                                                        if flt(d.total_deductible_amount) > 0:
                                                                if flt(d.total_outstanding_amount) > 0:
                                                                        if flt(amount) >= flt(d.total_outstanding_amount):
                                                                                amount = flt(d.total_outstanding_amount)
                                                                else:
                                                                        amount = 0
                                        else:
                                                amount = 0
                                else:
                                        if key == 'deductions':
                                                if flt(d.total_deductible_amount) > 0:
                                                        if flt(d.total_outstanding_amount) > 0:
                                                                if flt(amount) >= flt(d.total_outstanding_amount):
                                                                        amount = flt(d.total_outstanding_amount)

                                                        else:
                                                                amount = 0

                                if flt(d.total_deductible_amount) > 0:
                                        if flt(d.total_outstanding_amount) > 0:
                                                deductible_amt  = flt(d.total_deductible_amount)
                                                deducted_amt    = flt(d.total_deducted_amount) + flt(amount)
                                                outstanding_amt = flt(d.total_outstanding_amount) - flt(amount)

                                # Leave without pay
                                calc_amount = flt(amount)
                                if key == "earnings":
					if d.depends_on_lwp or source.depend_salary_on_attendance:
                                                calc_amount = round(flt(amount)*flt(payment_days)/flt(days_in_month))
                                        else:
                                                calc_amount = round(flt(amount)*(flt(working_days)/flt(days_in_month)))

                                
                                # following condition added by SHIV on 2021/05/28
                                if not flt(calc_amount):
                                        continue

                                calc_map.setdefault(key,[]).append({
                                        'salary_component'         : d.salary_component,
                                        'depends_on_lwp'           : d.depends_on_lwp,
					'institution_name'         : d.institution_name,
					'reference_type'           : d.reference_type,
					'reference_number'         : d.reference_number,
                                        'ref_docname'              : d.name,
                                        'from_date'                : start_date,
                                        'to_date'                  : end_date,
                                        'amount'                   : flt(calc_amount),
                                        'default_amount'           : flt(amount),
                                        'total_deductible_amount'  : flt(deductible_amt),
                                        'total_deducted_amount'    : flt(deducted_amt),
                                        'total_outstanding_amount' : flt(outstanding_amt),
                                        'total_days_in_month'      : flt(days_in_month),
                                        'working_days'             : flt(working_days),
                                        'leave_without_pay'        : flt(lwp),
                                        'payment_days'             : flt(payment_days)
                                })

                for e in calc_map['earnings']:
                        if e['salary_component'] == 'Basic Pay':
                        	basic_amt = (flt(e['amount']))
                        ### Ver.2.0.20191227 Begins, added by SHIV on 2019/12/27
                        # Following condition added by SHIV on 2019/12/27
                        elif frappe.db.exists("Salary Component", {"name": e["salary_component"], "is_pf_deductible": 1}):
                                if flt(e["amount"]):
                                        basic_pay_arrears += flt(e["amount"])
                                        off_cycle_pf = frappe.db.get_value("Salary Component", e["salary_component"], "off_cycle_pf")
                                        if flt(off_cycle_pf) > 0:
                                                basic_pay_arrears_pf += flt(e["amount"])*flt(off_cycle_pf)*0.01
                                        elif not flt(off_cycle_pf):
                                                basic_pay_arrears_pf += round(flt(e["amount"])*flt(settings.get("employee_pf"))*0.01)
                        ### Ver.2.0.20191227 Ends
                        if e['salary_component'] == 'Communication Allowance':
                        	comm_amt = (flt(e['amount']))
			gross_amt += flt(e['amount'])

			#Deputation allowance
			if e['salary_component'] == 'Deputation Allowance':
				deput_amt = (flt(e['amount']))
			# HRA
			if e['salary_component'] == 'Housing Allowance':
                                hra_amt = (flt(e['amount']))
	
                gross_amt += (flt(target.arrear_amount) + flt(target.leave_encashment_amount))

                # Calculating PF, Group Insurance Scheme, Health Contribution
		sws = pf = gis = health = 0.00
		for d in calc_map['deductions']:
                        if not flt(gross_amt):
                                d['amount'] = 0
                        else:
                                
                                if d['salary_component'] == 'SWS':
                                        sws = flt(settings.get("sws_contribution"));
                                        #sws = 0.0
					#sws = frappe.get_doc("Employee Grade", self.employee_grade).sws_contribution
					d['amount'] = flt(sws)
                                
                                if d['salary_component'] == 'PF':
					percent = flt(settings.get("employee_pf"))
                                        if source.employment_type == 'GEP':
                                                pf = round(full_basic*flt(percent)*0.01);
                                        else:
                                                pf = round(basic_amt*flt(percent)*0.01);

					pf += basic_pay_arrears_pf
                                        ### Ver.2.0.20191227 Begins, added by SHIV on 2019/12/27
                                        # Temporary workout for adding 4% of oct-2019 and nov-2019 PF
                                        # this needs to be commented after processing 201912 payslips
                                        '''tmp_basic = 0
                                        tmp_pf = 0
                                        if target_doc.fiscal_year == '2019' and target_doc.month == '12':
                                                tmp = frappe.db.sql("""
                                                        select sum(amount) total_amount
                                                        from `tabSalary Detail`
                                                        where salary_component = 'Basic Pay'
                                                        and exists(select 1
                                                                        from `tabSalary Slip`
                                                                        where `tabSalary Slip`.employee = '{employee}'
                                                                        and `tabSalary Slip`.fiscal_year = '2019'
                                                                        and `tabSalary Slip`.month in ('10','11')
                                                                        and `tabSalary Slip`.docstatus = 1
                                                                        and `tabSalary Detail`.parent = `tabSalary Slip`.name
                                                        )
                                                """.format(employee=source.employee), as_dict=True)

                                                if tmp:
                                                       tmp_basic = flt(tmp[0].total_amount)
                                                tmp_pf = tmp_basic*4*0.01
                                        pf += flt(tmp_pf)'''
                                        ### Ver.2.0.20191227 Ends
                                        d['amount'] = pf
                                if d['salary_component'] == 'Group Insurance Scheme':
                                        gis = flt(settings.get("gis"))
                                        d['amount'] = gis

                                if d['salary_component'] == 'Health Contribution':
                                        percent = flt(settings.get("health_contribution"))
					health = round(gross_amt*flt(percent)*0.01);

					if source.employment_type == 'Deputation':	
						#gross_amt  =  gross_amt - deput_amt
						health = round(deput_amt*flt(percent)*0.01);

                                        d['amount'] = health

				
                # Calculating Salary Tax
		tax_included = 0
		for d in calc_map['deductions']:
                        if not flt(gross_amt):
                                d['amount'] = 0
                        else:
                                if d['salary_component'] == 'Salary Tax':
                                        if not tax_included:
                                                tax_amt = get_salary_tax(flt(gross_amt) - flt(gis) - flt(pf) - (flt(comm_amt) * 0.5))
                                        	if source.employment_type == 'Deputation':
							gross_amt1 = gross_amt - deput_amt 
							tax_amt1 = get_salary_tax(flt(gross_amt1) - flt(gis) - flt(pf) -(flt(comm_amt) * 0.5))  
							tax_amt = tax_amt - tax_amt1	
                                                        

						d['amount'] = flt(tax_amt)
                                                tax_included = 1

                # Appending calculated components to salary slip                                                
                #[target.append('earnings',m) for m in calc_map['earnings']]
                #[target.append('deductions',m) for m in calc_map['deductions']]
		for m in calc_map['earnings']:
			#frappe.msgprint("hhh {0} {1}".format(m['salary_component'], source.employment_type))
			if source.employment_type == 'Deputation' and m['salary_component'] not in ['Deputation Allowance','Communication Allowance', 'Salary Arrears', 'Contract Allowance CDCL', 'PSA']:
				continue 
			else:
				target.append('earnings', m)
		for m in calc_map['deductions']:
			if source.employment_type == 'Deputation' and m['salary_component'] not in ['SWS', 'Salary Tax','Health Contribution', 'Other deduction','Other Recoveries']:
				continue
			else:
				target.append('deductions', m)
  
		target.run_method("pull_emp_details")
		target.run_method("calculate_net_pay")

	
	doc = get_mapped_doc("Salary Structure", source_name, {
		"Salary Structure": {
			"doctype": "Salary Slip",
			"field_map": {
				"total_earning": "gross_pay",
				"name": "salary_structure",
			}
		}
	}, target_doc, postprocess, ignore_child_tables=True)
                
	return doc

# Ver 2.0, Following method added by SHIV on 2018/02/27
@frappe.whitelist()
def salary_component_query(doctype, txt, searchfield, start, page_len, filters):
        return frappe.db.sql(""" 
                        select
                                name,
                                type,
                                payment_method
                        from `tabSalary Component`
                        where type = %(component_type)s
                        and (
                                {key} like %(txt)s
                                or
                                type like %(txt)s
                                or
                                payment_method like %(txt)s
                        )
                        {mcond}
                        order by
                                if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
                                if(locate(%(_txt)s, type), locate(%(_txt)s, type), 99999),
                                if(locate(%(_txt)s, payment_method), locate(%(_txt)s, payment_method), 99999),
                                idx desc,
                                name, type, payment_method
                        limit %(start)s, %(page_len)s
                        """.format(**{
                                'key': searchfield,
                                'mcond': get_match_cond(doctype)
                        }),
                        {
                "txt": "%%%s%%" % txt,
                "_txt": txt.replace("%", ""),
                "start": start,
                "page_len": page_len,
                "component_type": 'Earning' if filters['parentfield'] == 'earnings' else 'Deduction'
            })
