# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, add_days, date_diff, cint, flt
from frappe import _
from frappe.utils.csvutils import UnicodeWriter
from frappe.model.document import Document
from calendar import monthrange

class UploadAttendanceOthers(Document):
	pass

@frappe.whitelist()
def get_template():
	if not frappe.has_permission("Attendance Others", "create"):
		raise frappe.PermissionError

	args = frappe.local.form_dict
	w = UnicodeWriter()
	w = add_header(w, args)
	w = add_data(w, args)

	# write out response as a type csv
	frappe.response['result'] = cstr(w.getvalue())
	frappe.response['type'] = 'csv'
	frappe.response['doctype'] = "Attendance Others"

def add_header(w, args):
	status = ", ".join((frappe.get_meta("Attendance Others").get_field("status").options or "").strip().split("\n"))
	w.writerow(["Notes:"])
	w.writerow(["Please do not change the template headings"])
	w.writerow(["Status should be P if Present, A if Absent"])
	hd = ["Branch", "Cost Center", "Employee Type", "Employee ID", "Employee Name", "Year", "Month"]

	month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
		"Dec"].index(args.month) + 1

	total_days = monthrange(cint(args.fiscal_year), month)[1]
	for day in range(cint(total_days)):
		hd.append(str(day + 1))	

	w.writerow(hd)
	return w

def add_data(w, args):
	employees = get_active_employees(args)
	for e in employees:
		row = [
			e.branch, e.cost_center, e.etype, "\'"+str(e.name)+"\'", e.person_name, args.fiscal_year, args.month
		]
		w.writerow(row)
	return w

def test(args):
        print 'Test print...', args.fname, args.lname
        
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
		"Dec"].index('Dec') + 1
        total_days = monthrange(cint(2017), month)[1]
        

        col = []
        for day in range(cint(total_days)):
		#hd.append(str(day + 1))
                col.append(" MAX(case when day(date) = {0} then lower(substr(status,1,1)) else '' end) as day{0}".format(day+1))

        att_list = """
                        select
                                case
                                        when a.employee_type = 'GEP Employee' then 'GEP'
                                        when a.employee_type = 'Muster Roll Employee' then 'MR'
                                end as etype,
                                a.employee,
                                
                """
        
        employees = frappe.db.sql("""
                select
                        "MR" as etype,
                        name,
                        person_name,
                        branch,
                        cost_center
		from `tabMuster Roll Employee`
		where docstatus < 2
		and status = 'Active'
		and branch = %(branch)s
		UNION
		select
                        "GEP" as etype,
                        name,
                        person_name,
                        branch,
                        cost_center
		from `tabGEP Employee`
		where docstatus < 2
		and status = 'Active'
		and branch = %(branch)s
		""", {"branch": 'Pachu Zam Construction'}, as_dict=1)

        print employees
        print 'Test 2'

def get_active_employees(args):        
	employees = frappe.db.sql("""
                select
                        "MR" as etype,
                        name,
                        person_name,
                        branch,
                        cost_center
		from `tabMuster Roll Employee`
		where docstatus < 2
		and status = 'Active'
		and branch = '{0}'
		UNION
		select
                        "GEP" as etype,
                        name,
                        person_name,
                        branch,
                        cost_center
		from `tabGEP Employee`
		where docstatus < 2
		and status = 'Active'
		and branch = '{0}'
		""".format(args.branch), {"branch": args.branch}, as_dict=1)

	return employees

@frappe.whitelist()
def upload():
	if not frappe.has_permission("Attendance Others", "create"):
		raise frappe.PermissionError

	from frappe.utils.csvutils import read_csv_content_from_uploaded_file
	from frappe.modules import scrub

	rows = read_csv_content_from_uploaded_file()
	rows = filter(lambda x: x and any(x), rows)
	if not rows:
		msg = [_("Please select a csv file")]
		return {"messages": msg, "error": msg}
	columns = [scrub(f) for f in rows[3]]
	ret = []
	error = False

	from frappe.utils.csvutils import check_record, import_doc

	for i, row in enumerate(rows[4:]):
		if not row: continue
		try:
			row_idx = i + 4
			for j in range(8, len(row) + 1):
                                month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(row[6]) + 1	
				month = str(month) if cint(month) > 9 else str("0" + str(month))
				day = str(cint(j) - 7) if cint(j) > 9 else str("0" + str(cint(j) - 7))
				status = ''
				
				if str(row[j -1]) in ("P","p"):
                                        status = 'Present'
                                elif str(row[j -1]) in ("A","a"):
                                        status = 'Absent'
                                else:
                                        status = ''
                                        
				#frappe.msgprint(str(j))
                                old = frappe.db.get_value("Attendance Others", {"employee": row[3].strip('\''), "date": str(row[5]) + '-' + str(month) + '-' + str(day)}, ["status","name"], as_dict=1)
                                if old:
                                        doc = frappe.get_doc("Attendance Others", old.name)
                                        doc.db_set('status', status if status in ('Present','Absent') else doc.status)
                                        doc.db_set('branch', row[0])
                                        doc.db_set('cost_center', row[1])
                                else:
                                        doc = frappe.new_doc("Attendance Others")
                                        doc.status = status
                                        doc.branch = row[0]
                                        doc.cost_center = row[1]
                                        doc.employee = str(row[3]).strip('\'')
                                        doc.date = str(row[5]) + '-' + str(month) + '-' + str(day)
                                        
                                        if str(row[2]) == "MR":
                                                doc.employee_type = "Muster Roll Employee"
                                        elif str(row[2]) == "GEP":
                                                doc.employee_type = "GEP Employee"
                                        
                                        if doc.status in ('Present','Absent'):
                                                doc.submit()
		except Exception, e:
			error = True
			ret.append('Error for row (#%d) %s : %s' % (row_idx,
				len(row)>1 and row[4] or "", cstr(e)))
			frappe.errprint(frappe.get_traceback())

	if error:
		frappe.db.rollback()
	else:
		frappe.db.commit()
	return {"messages": ret, "error": error}
