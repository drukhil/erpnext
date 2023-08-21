# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, add_months, cint, get_last_day

class BulkAssetDepreciation(Document):
	def validate(self):
		pass

	def make_asset_depreciation(self):
		from erpnext.assets.doctype.asset.depreciation import make_depreciation_entry
		for a in frappe.db.sql("""
				select name, asset, schedule_date
					FROM `tabBulk Asset Depreciation Item`
				WHERE booked=0
					and parent='{0}'
			 	order by idx
				""".format(self.name), as_dict=True):
			make_depreciation_entry(a.asset, a.schedule_date)
			frappe.db.sql("""
					UPDATE `tabBulk Asset Depreciation Item`
					SET booked=1
					WHERE name='{0}'
					""".format(a.name))
			frappe.db.commit()
		if frappe.db.sql("""select count(name) as pending_count
				FROM `tabBulk Asset Depreciation Item`
				WHERE booked=0
				AND parent='{0}'
			""".format(self.name))[0][0] == 0:
			frappe.db.sql("UPDATE `tabBulk Asset Depreciation` set completed=1 where name='{}'".format(self.name))
			frappe.db.commit()

	def get_asset(self):
		schedule_date =  get_last_day(self.depreciation_schedule)
		self.set('item', [])
		for d in frappe.db.sql("""
				select a.name as asset, a.asset_name, s.depreciation_amount, s.schedule_date 
					from `tabAsset` a inner join `tabDepreciation Schedule` s
					on a.name=s.parent
				where a.status not in ("Sold", "Scraped")
					and a.docstatus=1
					and s.schedule_date='{0}'
					and disable_depreciation=0
					and (journal_entry IS NULL or journal_entry="")
				limit 100
			""".format(schedule_date), as_dict=True):
			row = self.append('item', {})
			row.update(d)


			

