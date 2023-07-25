# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, add_days, date_diff, cint, flt, getdate, nowdate
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
	hd = ["Branch", "Unit", "Cost Center", "Employee Type", "Employee ID", "Employee Name", "Year", "Month"]

	month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
		"Dec"].index(args.month) + 1

	total_days = monthrange(cint(args.fiscal_year), month)[1]
	for day in range(cint(total_days)):
		hd.append(str(day + 1))	

	w.writerow(hd)
	return w

def add_data(w, args):
        month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(args.month) + 1
        month = str(month) if cint(month) > 9 else str("0" + str(month))

        total_days = monthrange(cint(args.fiscal_year), cint(month))[1]
        start_date = str(args.fiscal_year) + '-' + str(month) + '-' + str('01')
        end_date   = str(args.fiscal_year) + '-' + str(month) + '-' + str(total_days)
        
	employees = get_active_employees(args, start_date, end_date)
	loaded     = get_loaded_records(args, start_date, end_date)
	
	for e in employees:
                status = ''
		row = [
			e.branch, e.unit, e.cost_center, e.etype, "\'"+str(e.name)+"\'", e.person_name, args.fiscal_year, args.month
		]
		
		for day in range(cint(total_days)):
                        status = loaded.get(e.etype, frappe._dict()).get(e.name, frappe._dict()).get(day+1,'')
                        row.append(status)
                        
		w.writerow(row)
	return w

def get_loaded_records(args, start_date, end_date):
        loaded_list= frappe._dict()

        rl = frappe.db.sql("""
                        select
                                case 
                                    when employee_type = 'Muster Roll Employee' then 'MR'
                                    when employee_type = 'DES Employee' then 'DES'
                                    else employee_type
                                end as employee_type,
                                employee,
                                day(date) as day_of_date,
                                case
                                    when status = 'Present' then 'P'
                                    when status = 'Absent' then 'A'
                                    else status
                                end as status
                        from `tabAttendance Others`
                        where branch = '{0}'
                        and date between %s and %s
                        and docstatus = 1
                """.format(args.branch), (start_date, end_date), as_dict=1)

        for r in rl:
                loaded_list.setdefault(r.employee_type, frappe._dict()).setdefault(r.employee, frappe._dict()).setdefault(r.day_of_date,r.status)

        return loaded_list

def get_active_employees(args, start_date, end_date):        
	employees = frappe.db.sql("""
                select distinct
                        "MR" as etype,
                        me.name,
                        me.person_name,
                        iw.branch,
			me.unit,
                        iw.cost_center
		from `tabMuster Roll Employee` as me, `tabEmployee Internal Work History` as iw
                where me.docstatus < 2
                and iw.parent = me.name
                and iw.branch = '{0}'
		and me.unit = '{3}'
		and (
                        ('{1}' between iw.from_date and ifnull(iw.to_date,now()))
                        or
                        ('{2}' between iw.from_date and ifnull(iw.to_date,now()))
                        or
                        (iw.from_date between '{1}' and '{2}')
                        or
                        (ifnull(iw.to_date,now()) between '{1}' and '{2}')
                )
		UNION
		select distinct
                        "DES" as etype,
                        ge.name,
                        ge.person_name,
                        iw.branch,
			'unit' as unit,
                        iw.cost_center
		from `tabDES Employee` as ge, `tabEmployee Internal Work History` as iw
		where ge.docstatus < 2
                and iw.parent = ge.name
                and iw.branch = '{0}'
		and (
                        ('{1}' between iw.from_date and ifnull(iw.to_date,now()))
                        or
                        ('{2}' between iw.from_date and ifnull(iw.to_date,now()))
                        or
                        (iw.from_date between '{1}' and '{2}')
                        or
                        (ifnull(iw.to_date,now()) between '{1}' and '{2}')
                )
		""".format(args.branch, start_date, end_date, args.unit), {"branch": args.branch, "unit": args.unit}, as_dict=1)

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
	columns = [scrub(f) for f in rows[4]]
	ret = []
	error = False

	from frappe.utils.csvutils import check_record, import_doc

	frappe.msgprint("Started Parsing")
	for i, row in enumerate(rows[4:]):
		if not row: continue
		try:
			row_idx = i + 4
			for j in range(9, len(row) + 1):
                                month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(row[7]) + 1	
				month = str(month) if cint(month) > 9 else str("0" + str(month))
				day = str(cint(j) - 8) if cint(j) > 9 else str("0" + str(cint(j) - 8))
				status = ''
				
				if str(row[j -1]) in ("P","p"):
                                        status = 'Present'
                                elif str(row[j -1]) in ("A","a"):
                                        status = 'Absent'
                                else:
                                        status = ''
                                        
				#frappe.msgprint(str(j))
                                old = frappe.db.get_value("Attendance Others", {"employee": row[4].strip('\''), "date": str(row[6]) + '-' + str(month) + '-' + str(day)}, ["status","name"], as_dict=1)
                                # Following IF condition enabled temporarily by SHIV on 2018/02/01
                                if old:
                                        doc = frappe.get_doc("Attendance Others", old.name)
                                        doc.db_set('status', status if status in ('Present','Absent') else doc.status)
                                        doc.db_set('branch', row[0])
					doc.db_set('unit', row[1])
                                        doc.db_set('cost_center', row[2])
                                #else:
                                if not old and status in ('Present','Absent'):
                                        doc = frappe.new_doc("Attendance Others")
                                        doc.status = status
                                        doc.branch = row[0]
					doc.unit = row[1]
                                        doc.cost_center = row[2]
                                        doc.employee = str(row[4]).strip('\'')
                                        doc.date = str(row[6]) + '-' + str(month) + '-' + str(day)
                                        
                                        if str(row[3]) == "MR":
                                                doc.employee_type = "Muster Roll Employee"
                                        elif str(row[3]) == "DES":
                                                doc.employee_type = "DES Employee"
                                    	
					#Prevent future dates creation
                                        # Jai commented. 25 July, 2023
					# if not getdate(doc.date) > getdate(nowdate()):
					# 	doc.submit()
		except Exception, e:
			error = True
			ret.append('Error for row (#%d) %s : %s' % (row_idx,
				len(row)>1 and row[5] or "", cstr(e)))
			frappe.errprint(frappe.get_traceback())

	if error:
		frappe.db.rollback()
	else:
		frappe.db.commit()
		frappe.msgprint("DONE")
	return {"messages": ret, "error": error}
