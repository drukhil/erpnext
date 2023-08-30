# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
2.0		  SHIV		                   04/10/2017         Auto populating internal_work_history
2.0               SHIV                             15/08/2018         Auto populating employee_family_details
2.0               SHIV                             03/09/2018         Following changes made
                                                                        1) retirement_age moved from "HR Settings" to
                                                                                "Employee Group" master.
                                                                        2) health_contribution, employee_pf, employer_pf
                                                                                moved from "HR Settings" to "Employment Group"
2.0.190408        SHIV                             08/04/2019         Method update_retirement_age() created.                                                                                
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, getdate, cint, validate_email_add, today, add_years, date_diff, nowdate
from frappe.model.naming import make_autoname
from frappe import throw, _
import frappe.permissions
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from erpnext.utilities.transaction_base import delete_events
from erpnext.custom_utils import get_year_start_date, get_year_end_date, round5
from frappe.utils.data import get_first_day, get_last_day, add_days


class EmployeeUserDisabledError(frappe.ValidationError):
	pass


class Employee(Document):
        """def autoname(self):
		naming_method = frappe.db.get_value("HR Settings", None, "emp_created_by")
		if not naming_method:
			throw(_("Please setup Employee Naming System in Human Resource > HR Settings"))
		else:
			if naming_method == 'Naming Series':
				if not self.date_of_joining:
					frappe.throw("Date of Joining not Set!")
				abbr = frappe.db.get_value("Company", self.company, "abbr")
				#naming_series = str(abbr) + "." + str(getdate(self.date_of_joining).year)[2:4]	
				naming_series = str()
				x = make_autoname(str(naming_series) + '.###')
				y = make_autoname(str(getdate(self.date_of_joining).strftime('%m')) + ".#")
				start_id = cint(len(str(abbr))) + 2
				eid = x[:start_id] + y[:2] + x[start_id:start_id + 3]
				self.name = eid
				self.yearid = x
			elif naming_method == 'Employee Number':
				self.name = self.employee_number

		self.employee = self.name
		
     	""" 
	def autoname(self):
		naming_method = frappe.db.get_value("HR Settings", None, "emp_created_by")
		if not naming_method:
			throw(_("Please setup Employee Naming System in Human Resource > HR Settings"))
		else:
			if naming_method == 'Naming Series':
				if not self.date_of_joining:
					frappe.throw("Date of Joining not Set!")
				#naming_series = str(self.naming_series) + str(getdate(self.date_of_joining).year)[2:4]
				naming_series = str(self.naming_series)	
				x = make_autoname(str(naming_series) + '.###')
				y = make_autoname(str(getdate(self.date_of_joining).strftime('%m')) + ".#")
				eid = x[:6] + y[:2] + x[6:9]
				self.name = x
				self.yearid = x
			elif naming_method == 'Employee Number':
				self.name = self.employee_number

		self.employee = self.name

	def validate(self):
		from erpnext.controllers.status_updater import validate_status
		validate_status(self.status, ["Active", "Left"])
		#self.update_assign_branch()
		self.employee = self.name
		if self.reports_to:
			self.approver_name = frappe.db.get_value("Employee", self.reports_to, "employee_name")
		if self.cost_center:
			self.branch = frappe.db.get_value("Cost Center", self.cost_center, "branch")
		if self.branch:
                        self.gis_policy_number = frappe.db.get_value("Branch", self.branch, "gis_policy_number")
                        
		self.validate_date()
		self.validate_email()
		self.validate_status()
		#self.post_casual_leave()
		# Following method introduced by SHIV on 04/10/2018
		self.validate_employment()
		self.validate_employee_leave_approver()
		self.validate_reports_to()
	
		if self.user_id:
			self.company_email = self.user_id
			self.toggle_user_enable()
			self.validate_for_enabled_user_id()
			self.validate_duplicate_user_id()
		else:
			existing_user_id = frappe.db.get_value("Employee", self.name, "user_id")
			if existing_user_id:
				frappe.permissions.remove_user_permission(
					"Employee", self.name, existing_user_id)

		# Following method introduced by SHIV on 04/10/2017
		self.populate_work_history()
		# Following method introduced by SHIV on 15/08/2018
		self.populate_family_details()
                # Following method introduced by SHIV on 08/04/2019
                self.update_retirement_age()
    
	def before_save(self):
		if self.branch != self.get_db_value("branch") and  self.user_id:
			frappe.permissions.remove_user_permission("Branch", self.get_db_value("branch"), self.user_id)           
 
	def on_update(self):
		if self.user_id:
			self.update_user()
			self.update_user_permissions()
		self.post_casual_leave()
		self.update_salary_structure()

        def update_retirement_age(self):
                ret = frappe.db.sql("""
                                select date_add('{0}', INTERVAL retirement_age YEAR) as date_of_retirement
                                from `tabEmployee Group` where name = '{1}'
                """.format(getdate(self.date_of_birth), self.employee_group), as_dict=True)
                if ret:
                        self.date_of_retirement = ret[0].date_of_retirement
                        
        def update_salary_structure(self):
                ss = frappe.db.get_value("Salary Structure", {"employee": self.name, "is_active": "Yes"}, "name")
                if ss:
                        doc = frappe.get_doc("Salary Structure", ss)
			doc.flags.ignore_permissions = 1
			doc.save()
        
        def validate_employment(self):
                if not frappe.db.exists("Employment Type Item", {"parent": self.employment_type,"employee_group": self.employee_group}):
                        frappe.throw(_("Employee group `<b>{0}</b>` does not fall under employment type `<b>{1}</b>`").format(self.employee_group, self.employment_type),title="Invalid Data")
                        
                if not frappe.db.exists("Employee Grade", {"name": self.employee_subgroup,"employee_group": self.employee_group}):
                        frappe.throw(_("Employee grade `<b>{0}</b>` does not fall under employee group `<b>{1}</b>`").format(self.employee_subgroup, self.employee_group),title="Invalid Data")
        
        # Following method introducted by SHIV on 04/10/2017
        def populate_work_history(self):
                if not self.internal_work_history:
                        self.append("internal_work_history",{
                                                "branch": self.branch,
                                                "cost_center": self.cost_center,
                                                "department": self.department,
                                                "designation": self.designation,
                                                "from_date": self.date_of_joining,
                                                "owner": frappe.session.user,
                                                "creation": nowdate(),
                                                "modified_by": frappe.session.user,
                                                "modified": nowdate()
                        })
                else:
                        # Fetching previous document from db
                        prev_doc = frappe.get_doc(self.doctype,self.name)
                        self.date_of_transfer = self.date_of_transfer if self.date_of_transfer else today()

                        if (getdate(self.date_of_joining) != prev_doc.date_of_joining) or \
                           (self.status == 'Left' and self.relieving_date) or \
                           (self.cost_center != prev_doc.cost_center):
                                for wh in self.internal_work_history:
                                        # For change in date_of_joining
                                        if (getdate(self.date_of_joining) != prev_doc.date_of_joining):
                                                if (getdate(prev_doc.date_of_joining) == getdate(wh.from_date)):
                                                        wh.from_date = self.date_of_joining

                                        # For change in relieving_date, cost_center
                                        if (self.status == 'Left' and self.relieving_date):
                                                if not wh.to_date:
                                                        wh.to_date = self.relieving_date
                                                elif prev_doc.relieving_date:
                                                        if (getdate(prev_doc.relieving_date) == getdate(wh.to_date)):
                                                                wh.to_date = self.relieving_date
                                        elif (self.cost_center != prev_doc.cost_center):
                                                if getdate(self.date_of_transfer) > getdate(today()):
                                                        frappe.throw(_("Date of transfer cannot be a future date."),title="Invalid Date")      
                                                elif not wh.to_date:
                                                        if getdate(self.date_of_transfer) < getdate(wh.from_date):
                                                                frappe.throw(_("Row#{0} : Date of transfer({1}) cannot be beyond current effective entry.").format(wh.idx,self.date_of_transfer),title="Invalid Date")
                                                                
                                                        wh.to_date = wh.from_date if add_days(getdate(self.date_of_transfer),-1) < getdate(wh.from_date) else add_days(self.date_of_transfer,-1)
                                                
                        if (self.cost_center != prev_doc.cost_center):
                                self.append("internal_work_history",{
                                                "branch": self.branch,
                                                "cost_center": self.cost_center,
                                                "department": self.department,
                                                "designation": self.designation,
                                                "from_date": self.date_of_transfer,
                                                "owner": frappe.session.user,
                                                "creation": nowdate(),
                                                "modified_by": frappe.session.user,
                                                "modified": nowdate()
                                })
                        elif not self.internal_work_history:
                                self.append("internal_work_history",{
                                                        "branch": self.branch,
                                                        "cost_center": self.cost_center,
                                                        "department": self.department,
                                                        "designation": self.designation,
                                                        "from_date": self.date_of_joining,
                                                        "owner": frappe.session.user,
                                                        "creation": nowdate(),
                                                        "modified_by": frappe.session.user,
                                                        "modified": nowdate()
                                })

        def populate_family_details(self):
                exists = sum(1 if i.relationship == "Self" else 0 for i in self.employee_family_details)
                #if not self.employee_family_details or not frappe.db.exists("Employee Family Details", {"parent": self.name, "relationship": "Self"}):
                if not exists:
                        self.append("employee_family_details",{
                                                "relationship": "Self",
                                                "full_name": self.employee_name,
                                                "gender": self.gender,
                                                "date_of_birth": self.date_of_birth,
                                                "cid_no": self.passport_number,
                                                "district_name": self.dzongkhag,
                                                "city_name": self.gewog,
                                                "village_name": self.village,
                                                "owner": frappe.session.user,
                                                "creation": nowdate(),
                                                "modified_by": frappe.session.user,
                                                "modified": nowdate()
                        })
                else:
                        pass
                
	def update_user_permissions(self):
		if self.branch != self.get_db_value("branch") and  self.user_id:
			frappe.permissions.remove_user_permission("Branch", self.get_db_value("branch"), self.user_id)           

		frappe.permissions.add_user_permission("Employee", self.name, self.user_id)
		frappe.permissions.set_user_permission_if_allowed("Company", self.company, self.user_id)
		#Add Branch Permission to User
		frappe.permissions.add_user_permission("Branch", self.branch, self.user_id)

	def update_user(self):
		# add employee role if missing
		user = frappe.get_doc("User", self.user_id)
		user.flags.ignore_permissions = True

		if "Employee" not in user.get("user_roles"):
			user.add_roles("Employee")

		# copy details like Fullname, DOB and Image to User
		if self.employee_name and not (user.first_name and user.last_name):
			employee_name = self.employee_name.split(" ")
			if len(employee_name) >= 3:
				user.last_name = " ".join(employee_name[2:])
				user.middle_name = employee_name[1]
			elif len(employee_name) == 2:
				user.last_name = employee_name[1]

			user.first_name = employee_name[0]

		if self.date_of_birth:
			user.birth_date = self.date_of_birth

		if self.gender:
			user.gender = self.gender

		if self.image:
			if not user.user_image:
				user.user_image = self.image
				try:
					frappe.get_doc({
						"doctype": "File",
						"file_name": self.image,
						"attached_to_doctype": "User",
						"attached_to_name": self.user_id
					}).insert()
				except frappe.DuplicateEntryError:
					# already exists
					pass

		user.save()

	def validate_date(self):
		if self.date_of_birth and getdate(self.date_of_birth) > getdate(today()):
			throw(_("Date of Birth cannot be greater than today."))

		if self.date_of_birth and self.date_of_joining and getdate(self.date_of_birth) >= getdate(self.date_of_joining):
			throw(_("Date of Joining must be greater than Date of Birth"))

		elif self.date_of_retirement and self.date_of_joining and (getdate(self.date_of_retirement) <= getdate(self.date_of_joining)):
			throw(_("Date Of Retirement must be greater than Date of Joining"))

		elif self.relieving_date and self.date_of_joining and (getdate(self.relieving_date) <= getdate(self.date_of_joining)):
			throw(_("Relieving Date must be greater than Date of Joining"))

		elif self.contract_end_date and self.date_of_joining and (getdate(self.contract_end_date) <= getdate(self.date_of_joining)):
			throw(_("Contract End Date must be greater than Date of Joining"))

		if self.employment_type == 'Contract' and not self.increment_date:
			frappe.throw("Incremet Date is Mandatory for Contract Employees </b> ")
		
		if self.employment_type == 'Deputation' and not self.external_work_history:
                        frappe.throw("Work History In Required for Employees on Deputation")  

	def validate_email(self):
		if self.company_email:
			validate_email_add(self.company_email, True)
		if self.personal_email:
			validate_email_add(self.personal_email, True)

	def validate_status(self):
		if self.status == 'Left' and not self.relieving_date:
			throw(_("Please enter relieving date."),title="Missing Value")
                elif self.status == 'Left' and not self.reason_for_resignation:
                        frappe.throw(_("Please select reason for seperation."),title="Missing Value")
		if self.status == 'Left' and self.relieving_date:
			name = frappe.db.get_value("Salary Structure", {"employee": self.name, "is_active":"Yes"}, "name")
			if name:
				ss = frappe.get_doc("Salary Structure", name)
				if ss:
					ss.db_set("is_active", "No")

			# Disabling Employee record after marked as "Left"
			self.docstatus = 1


	def validate_for_enabled_user_id(self):
		if not self.status == 'Active':
			return
		enabled = frappe.db.get_value("User", self.user_id, "enabled")
		if enabled is None:
			frappe.throw(_("User {0} does not exist").format(self.user_id))
		if enabled == 0:
			frappe.throw(_("User {0} is disabled").format(self.user_id), EmployeeUserDisabledError)

	def validate_duplicate_user_id(self):
		employee = frappe.db.sql_list("""select name from `tabEmployee` where
			user_id=%s and status='Active' and name!=%s""", (self.user_id, self.name))
		if employee:
			throw(_("User {0} is already assigned to Employee {1}").format(
				self.user_id, employee[0]), frappe.DuplicateEntryError)

	def toggle_user_enable(self):
		user = frappe.get_doc("User", self.user_id)
		if user and self.status == 'Active':
			user.db_set("enabled", 1)
		if user and self.status == 'Left':
			user.db_set("enabled", 0)
	
	def validate_employee_leave_approver(self):
		for l in self.get("leave_approvers")[:]:
			#if l.leave_approver:
			#	frappe.permissions.add_user_permission("User", self.user_id, l.leave_approver)

			if "Approver" not in frappe.get_roles(l.leave_approver):
				frappe.get_doc("User", l.leave_approver).add_roles("Approver")

	def validate_reports_to(self):
		if self.reports_to == self.name:
			throw(_("Employee cannot report to self."))

	def on_trash(self):
		delete_events(self.doctype, self.name)


	def update_assign_branch(self):
		parent_cc = frappe.get_doc("Cost Center", self.cost_center).parent_cost_center
		frappe.msgprint("{0}".format(parent_cc))


	def post_casual_leave(self):
                if not cint(self.casual_leave_allocated):
                        credits_per_year = frappe.db.get_value("Employee Group Item", {"parent": self.employee_group, "leave_type": 'Casual Leave'}, "credits_per_year")

                        if flt(credits_per_year):
                                from_date = getdate(self.date_of_joining)
                                to_date = get_year_end_date(from_date);

                                no_of_months = frappe.db.sql("""
                                        select (
                                                case
                                                        when day('{0}') > 1 and day('{0}') <= 15
                                                        then timestampdiff(MONTH,'{0}','{1}')+1 
                                                        else timestampdiff(MONTH,'{0}','{1}')       
                                                end
                                                ) as no_of_months
                                """.format(str(self.date_of_joining),str(add_days(to_date,1))))[0][0]

                                new_leaves_allocated = round5((flt(no_of_months)/12)*flt(credits_per_year))
                                new_leaves_allocated = new_leaves_allocated if new_leaves_allocated <= flt(credits_per_year) else flt(credits_per_year)

				if self.employment_type == 'GCE':
                        		to_date = self.contract_end_date
                        		new_leaves_allocated = cint(5)

				if flt(new_leaves_allocated):
        	                	la = frappe.new_doc("Leave Allocation")
                	        	la.employee = self.employee
                        	 	la.employee_name = self.employee_name
                           		la.leave_type = "Casual Leave"
                              	 	la.from_date = str(from_date)
                             		la.to_date = str(to_date)
       		                       	la.carry_forward = cint(0)
                	            	la.new_leaves_allocated = flt(new_leaves_allocated)
                        	     	la.submit()
                             		self.db_set("casual_leave_allocated", 1)
					frappe.db.commit()
			                
                '''
		if not self.casual_leave_allocated:
			date = getdate(self.date_of_joining)
			start = date;
			end = get_year_end_date(date);
			end_month = get_last_day(date)
			leave_amount = 0 
			days = date_diff(end, start)
			leave_amount = flt(cint(cint(days) / 30) * 0.84)
			if cint(date_diff(end_month, start)) > 14:
				leave_amount += 0.84
			if leave_amount > 10:
				leave_amount = 10
			la = frappe.new_doc("Leave Allocation")
			la.employee = self.employee
			la.employee_name = self.employee_name
			la.leave_type = "Casual Leave"
			la.from_date = str(start)
			la.to_date = str(end)
			la.carry_forward = cint(0)
			la.new_leaves_allocated = round5(leave_amount)
			if flt(leave_amount) > 0:
				la.submit()
			self.db_set("casual_leave_allocated", 1)
                '''
                
def get_timeline_data(doctype, name):
	'''Return timeline for attendance'''
	return dict(frappe.db.sql('''select unix_timestamp(att_date), count(*)
		from `tabAttendance` where employee=%s
			and att_date > date_sub(curdate(), interval 1 year)
			and status in ('Present', 'Half Day')
			group by att_date''', name))

@frappe.whitelist()
def get_retirement_date(date_of_birth=None, employee_group=None):
	import datetime
	ret = {}
	if date_of_birth and employee_group:
		try:
                        # ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++
                        # Following code commented by SHIV on 2018/09/05
                        '''
			if employment_type in ['Executive','Chief Executive Officer']:
				retirement_age = int(frappe.db.get_single_value("HR Settings", "contract_retirement_age") or 60)
			else:
				retirement_age = int(frappe.db.get_single_value("HR Settings", "retirement_age") or 58)
			'''
                        # Following code added by SHIV on 2018/09/05
                        retirement_age = int(frappe.db.get_value("Employee Group", employee_group, "retirement_age"))
                        # +++++++++++++++++++++ Ver 2.0 ENDS +++++++++++++++++++++
                        
			dt = add_years(getdate(date_of_birth),retirement_age)
			ret = {'date_of_retirement': dt.strftime('%Y-%m-%d')}
		except ValueError:
			# invalid date
			ret = {}

	return ret


@frappe.whitelist()
def make_salary_structure(source_name, target=None):
	target = get_mapped_doc("Employee", source_name, {
		"Employee": {
			"doctype": "Salary Structure",
			"field_map": {
				"name": "employee",
			}
		}
	})
	target.make_earn_ded_table()
	return target

@frappe.whitelist()
def get_overtime_rate(employee):
		basic = frappe.db.sql("select a.amount as basic_pay from `tabSalary Detail` a, `tabSalary Structure` b where a.parent = b.name and a.salary_component in ('GCE Basic Pay', 'Basic Pay') and b.is_active = 'Yes' and b.employee = \'" + str(employee) + "\'", as_dict=True)
		if basic:
			return ((flt(basic[0].basic_pay) * 1) / (30 * 8))
		else:
			frappe.throw("No Salary Structure found for the employee")


def validate_employee_role(doc, method):
	# called via User hook
	if "Employee" in [d.role for d in doc.get("user_roles")]:
		if not frappe.db.get_value("Employee", {"user_id": doc.name}):
			frappe.msgprint(_("Please set User ID field in an Employee record to set Employee Role"))
			doc.get("user_roles").remove(doc.get("user_roles", {"role": "Employee"})[0])

def update_user_permissions(doc, method):
	# called via User hook
	if "Employee" in [d.role for d in doc.get("user_roles")]:
		employee = frappe.get_doc("Employee", {"user_id": doc.name})
		employee.update_user_permissions()

def send_birthday_reminders():
	"""Send Employee birthday reminders if no 'Stop Birthday Reminders' is not set."""
	if int(frappe.db.get_single_value("HR Settings", "stop_birthday_reminders") or 0):
		return

	from frappe.utils.user import get_enabled_system_users
	users = None

	birthdays = get_employees_who_are_born_today()

	if birthdays:
		if not users:
			users = [u.email_id or u.name for u in get_enabled_system_users()]

		for e in birthdays:
			frappe.sendmail(recipients=filter(lambda u: u not in (e.company_email, e.personal_email, e.user_id), users),
				subject=_("Birthday Reminder for {0}").format(e.employee_name),
				message=_("""Today is {0}'s birthday!""").format(e.employee_name),
				reply_to=e.company_email or e.personal_email or e.user_id)

def get_employees_who_are_born_today():
	"""Get Employee properties whose birthday is today."""
	return frappe.db.sql("""select name, personal_email, company_email, user_id, employee_name
		from tabEmployee where day(date_of_birth) = day(%(date)s)
		and month(date_of_birth) = month(%(date)s)
		and status = 'Active'""", {"date": today()}, as_dict=True)

def get_holiday_list_for_employee(employee, raise_exception=True):
	holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
	if holiday_list:
		return holiday_list
	branch, company = frappe.db.get_value("Employee", employee, ["branch", "company"])
	holiday_list = frappe.db.get_value("Branch", branch, "holiday_list")
	if not holiday_list:
		holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")

	if not holiday_list and raise_exception:
		frappe.throw(_('Please set a default Holiday List for Branch {0} or Company {1}').format(branch, company))

	return holiday_list

def get_employee_groups(doctype, txt, searchfield, start, page_len, filters):
        return frappe.db.sql("""select employee_group
                from `tabEmployment Type Item`
                where parent = '{0}'
                """.format(filters.get("employment_type")))
