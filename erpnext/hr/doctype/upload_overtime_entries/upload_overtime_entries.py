# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint
from frappe.utils import cstr, add_days, date_diff, cint, flt, getdate, nowdate, get_last_day
from frappe import _
from frappe.utils.csvutils import UnicodeWriter
from frappe.model.document import Document
from calendar import monthrange

class UploadOvertimeEntries(Document):
	pass

@frappe.whitelist()
def get_template():
	if not frappe.has_permission("Overtime Entry", "create"):
		raise frappe.PermissionError

	args = frappe.local.form_dict
	w = UnicodeWriter()
	w = add_header(w, args)
	w = add_data(w, args)

	# write out response as a type csv
	frappe.response['result'] = cstr(w.getvalue())
	frappe.response['type'] = 'csv'
	frappe.response['doctype'] = "Overtime Entry"

def add_header(w, args):
	w.writerow(["Notes:"])
	w.writerow(["Please do not change the template headings"])
#	w.writerow(["Hours should be in 'R' column if its from time: 5:00 PM To 10:00 PM, AND For 'S' column, from 10:01 PM To Next Morning 8:00 AM, Sunday and Government Holiday"])
	w.writerow(["Number of hours should be Integers"])
	hd = ["Branch", "Cost Center", "Employee Type", "Employee ID", "Employee Name", "Year", "Month"]

	month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
		"Dec"].index(args.month) + 1

	total_days = monthrange(cint(args.fiscal_year), month)[1]
	for day in range(cint(total_days)):
		hours = list(map(lambda x: "_".join([str(day+1),x]), ['RH','SH']))
		# hd.append(str(day + 1))	
		hd += hours

	w.writerow(hd)
	return w

def add_data(w, args):
	#dates = get_dates(args)
	month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(args.month) + 1
	month = str(month) if cint(month) > 9 else str("0" + str(month))

	total_days = monthrange(cint(args.fiscal_year), cint(month))[1]
	start_date = str(args.fiscal_year) + '-' + str(month) + '-' + str('01')
	end_date   = str(args.fiscal_year) + '-' + str(month) + '-' + str(total_days)
	
	employees  = get_active_employees(args, start_date, end_date)
	loaded     = get_loaded_records(args, start_date, end_date)
	
	for e in employees:
		row = [
			e.branch, e.cost_center, e.etype, "\'"+str(e.name)+"\'", e.person_name, args.fiscal_year, args.month
		]

		for day in range(cint(total_days)):
			hours = loaded.get(e.etype, frappe._dict()).get(e.name, frappe._dict()).get(day+1,[])
			# row.append(number_of_hours)
			row += hours if hours else [None, None]
		w.writerow(row)
	return w

def get_loaded_records(args, start_date, end_date):
	loaded_list= frappe._dict()

	rl = frappe.db.sql("""
			select
				case 
				    when employee_type = 'Muster Roll Employee' then 'MR'
				    when employee_type = 'GEP Employee' then 'GEP'
				    else 'Employee'
				end as employee_type,
				number as employee,
				day(date) as day_of_date,
				sum(ifnull(number_of_hours,0)) as number_of_hours,
				sum(ifnull(number_of_hours_special,0)) as number_of_hours_special
			from `tabOvertime Entry`
			where branch = '{0}'
			and date between %s and %s
			and docstatus = 1
			group by employee_type, employee, day_of_date
		""".format(args.branch), (start_date, end_date), as_dict=1)

	for r in rl:
		loaded_list.setdefault(r.employee_type, frappe._dict()).setdefault(r.employee, frappe._dict()).setdefault(r.day_of_date,[r.number_of_hours, r.number_of_hours_special])

	return loaded_list

def get_active_employees(args, start_date, end_date):
	employees = frappe.db.sql("""
		select distinct
			"MR" as etype,
			me.name,
			me.person_name,
			iw.branch,
			iw.cost_center
		from `tabMuster Roll Employee` as me, `tabEmployee Internal Work History` as iw
		where me.docstatus < 2
		and me.status = 'Active'
		and iw.parent = me.name
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
		UNION
		select distinct
			"GEP" as etype,
			ge.name,
			ge.person_name,
			iw.branch,
			iw.cost_center
		from `tabGEP Employee` as ge, `tabEmployee Internal Work History` as iw
		where ge.docstatus < 2
		and ge.status = 'Active'
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
		""".format(args.branch, start_date, end_date), {"branch": args.branch}, as_dict=1)
	return employees

def get_holidays(branch, fiscal_year, month):
	from_date = "-".join([str(fiscal_year), str(month), '01'])
	to_date = str(get_last_day(from_date))

	return frappe.db.sql_list("""
		SELECT h.holiday_date 
		FROM `tabHoliday List` hl, `tabHoliday List Branch` hlb, `tabHoliday` h 
		WHERE "{from_date}" <= hl.to_date AND "{to_date}" >= hl.from_date
		AND hlb.parent = hl.name
		AND hlb.branch = "{branch}"
		AND h.parent = hl.name
	""".format(branch=branch, from_date=from_date, to_date=to_date))


@frappe.whitelist()
def upload():
	# from erpnext.projects.doctype.process_mr_payment.process_mr_payment import check_if_holiday_overtime_entry		
	from erpnext.projects.doctype.process_mr_payment.process_mr_payment import get_pay_details

	if not frappe.has_permission("Overtime Entry", "create"):
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
	months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
	holidays = frappe._dict()
	for i, row in enumerate(rows[4:]):
		if not row: continue
		try:
			row_idx = i + 4

			# get dictionary for row data mapped with column names
			rec = frappe._dict(zip(columns, map(lambda v: str(v).strip("'") if v else None, row)))
			month = months.index(str(rec.month).title()) + 1
			month = str(month).rjust(2,str("0"))
			year  = str(rec.year)

			# get day wise, hour_type rates 
			# eg., day_li = {1 : {'rh': 3, 'sh': 1}, 2: {'rh': 4, 'sh': 2}}
			day_li = frappe._dict()
			for k, v in rec.items():
				if str(k).endswith('_rh') or str(k).endswith('_sh'):
					day, hour_type = str(k).split('_')[0], str(k).split('_')[-1]
					day_li.setdefault(day,frappe._dict()).setdefault(hour_type, v)

			# get overtime rates for the employee
			employee_type = None
			if rec.employee_type == "MR":
				employee_type = "Muster Roll Employee"
			elif rec.employee_type == "GEP":
				employee_type = "GEP Employee"
			else:
				continue

			pay_details = get_pay_details(employee_type, str(rec.employee_id), year, month)
			if not pay_details:
				frappe.throw("Wage Details(Rate Per Day) is not defined")
			rate_per_day, rate_per_hour, rate_per_hour_normal = 0, 0, 0
			if pay_details:
				rate_per_day 		 = flt(pay_details[0].get("rate_per_day"))
				rate_per_hour 		 = flt(pay_details[0].get("rate_per_hour"))
				rate_per_hour_normal = flt(pay_details[0].get("rate_per_hour_normal"))

			# get branch wise holidays
			if rec.branch not in holidays:
				holidays[rec.branch] = get_holidays(rec.branch, year, month)

			for day in day_li:
				date = str(year) + '-' + str(month) + '-' + str(day).rjust(2,str("0"))
				number_of_hours = flt(day_li[day].get('rh'))
				number_of_hours_special = flt(day_li[day].get('sh'))

				old = frappe.db.get_value("Overtime Entry", {"number": str(rec.employee_id), \
						"date": date, "docstatus": 1}, ["docstatus", "name"], as_dict=1)

				if old:
					doc = frappe.get_doc("Overtime Entry", old.name)
					doc.db_set('rate_per_day', flt(rate_per_day))
					doc.db_set('number_of_hours', flt(number_of_hours))
					doc.db_set('number_of_hours_special', flt(number_of_hours_special))
					doc.db_set('rate_per_hour', flt(rate_per_hour))
					doc.db_set('rate_per_hour_normal', flt(rate_per_hour_normal))
					doc.db_set('is_holiday',cint(getdate(date) in holidays[rec.branch]))
				else:
					if not (number_of_hours or number_of_hours_special): continue

					doc = frappe.new_doc("Overtime Entry")
					doc.branch          = rec.branch
					doc.cost_center     = rec.cost_center
					doc.number          = rec.employee_id
					doc.date            = date
					doc.is_holiday 		= cint(getdate(date) in holidays[rec.branch])
					doc.rate_per_day	= flt(rate_per_day)
					doc.number_of_hours = flt(number_of_hours)
					doc.number_of_hours_special = flt(number_of_hours_special)
					doc.rate_per_hour	= flt(rate_per_hour)
					doc.rate_per_hour_normal = flt(rate_per_hour_normal)
					doc.employee_type	= employee_type
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
	return {"messages": ret, "error": error}
