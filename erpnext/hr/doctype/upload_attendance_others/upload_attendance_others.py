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
    frappe.msgprint("this is the data returned: {}".format(w))
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
    month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(args.month) + 1
    month = str(month) if cint(month) > 9 else str("0" + str(month))

    total_days = monthrange(cint(args.fiscal_year), cint(month))[1]
    start_date = str(args.fiscal_year) + '-' + str(month) + '-' + str('01')
    end_date   = str(args.fiscal_year) + '-' + str(month) + '-' + str(total_days)
    
    employees = get_active_employees(args, start_date, end_date)
    loaded    = get_loaded_records(args, start_date, end_date)
    
    for e in employees:
        status = ''
        row = [
                e.branch, e.cost_center, e.etype, "\'"+str(e.name)+"\'", e.person_name, args.fiscal_year, args.month
        ]
        
        for day in range(cint(total_days)):
                status = loaded.get(e.etype, frappe._dict()).get(e.name, frappe._dict()).get(day+1,'')
                row.append(status)
                
        w.writerow(row)
    return w

def get_loaded_records(args, start_date, end_date):
    loaded_list= frappe._dict()

    rl = frappe.db.sql("""
        SELECT
            CASE
                WHEN employee_type = 'Muster Roll Employee' THEN 'MR'
                WHEN employee_type = 'GEP Employee' THEN 'GEP'
                ELSE employee_type
            END AS employee_type,
            employee,
            DAY(date) as day_of_date,
            CASE
                WHEN status = 'Present' then 'P'
                WHEN status = 'Absent' then 'A'
                ELSE status
            END AS status
        FROM `tabAttendance Others`
        WHERE branch = '{0}'
        AND date BETWEEN %s AND %s
        AND docstatus = 1
    """.format(args.branch), (start_date, end_date), as_dict=1)

    for r in rl:
        loaded_list.setdefault(r.employee_type, frappe._dict()).setdefault(r.employee, frappe._dict()).setdefault(r.day_of_date,r.status)

    return loaded_list

def get_active_employees(args, start_date, end_date):        
    employees = frappe.db.sql("""
        SELECT DISTINCT "MR" AS etype, me.name, me.person_name,
            iw.branch, iw.cost_center
        FROM `tabMuster Roll Employee` AS me, `tabEmployee Internal Work History` AS iw
        WHERE me.docstatus < 2
        AND me.status = 'Active'
        AND iw.parent = me.name
        AND iw.branch = '{0}'
        AND (
            ('{1}' BETWEEN iw.from_date AND IFNULL(iw.to_date,NOW()))
            OR
            ('{2}' BETWEEN iw.from_date and IFNULL(iw.to_date,NOW()))
            OR
            (iw.from_date BETWEEN '{1}' AND '{2}')
            OR
            (IFNULL(iw.to_date,NOW()) BETWEEN '{1}' AND '{2}')
        )
        UNION
        SELECT DISTINCT "GEP" AS etype, ge.name, ge.person_name,
            iw.branch, iw.cost_center
        FROM `tabGEP Employee` AS ge, `tabEmployee Internal Work History` AS iw
        WHERE ge.docstatus < 2
        AND ge.status = 'Active'
        AND iw.parent = ge.name
        AND iw.branch = '{0}'
        AND (
            ('{1}' BETWEEN iw.from_date and IFNULL(iw.to_date,NOW()))
            OR
            ('{2}' BETWEEN iw.from_date and IFNULL(iw.to_date,NOW()))
            OR
            (iw.from_date BETWEEN '{1}' AND '{2}')
            OR
            (IFNULL(iw.to_date,NOW()) BETWEEN '{1}' AND '{2}')
        )
    """.format(args.branch, start_date, end_date), {"branch": args.branch}, as_dict=1)

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

    # from frappe.utils.csvutils import check_record, import_doc

    frappe.msgprint("Started Parsing")
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
                        
                old = frappe.db.get_value("Attendance Others", {"employee": row[3].strip('\''), "date": str(row[5]) + '-' + str(month) + '-' + str(day)}, ["status","name"], as_dict=1)
                if old:
                    doc = frappe.get_doc("Attendance Others", old.name)
                    doc.db_set('status', status if status in ('Present','Absent') else doc.status)
                    doc.db_set('branch', row[0])
                    doc.db_set('cost_center', row[1])
                elif not old and status in ('Present','Absent'):
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
                        
                    #Prevent future dates creation
                    if not getdate(doc.date) > getdate(nowdate()):
                        doc.submit()
        except Exception as e:
            error = True
            ret.append('Error for row (#%d) %s : %s' % (row_idx,
                len(row)>1 and row[4] or "", cstr(e)))
            frappe.errprint(frappe.get_traceback())

    if error:
        frappe.db.rollback()
    else:
        frappe.db.commit()
        frappe.msgprint("DONE")
    return {"messages": ret, "error": error}
