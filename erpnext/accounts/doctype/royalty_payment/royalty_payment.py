# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.custom_utils import check_future_date, get_branch_cc, prepare_gl, prepare_sl, get_settings_value

class RoyaltyPayment(Document):
	def validate(self):
		check_future_date(self.posting_date)
		self.validate_data()

	def validate_data(self):
		if self.production_type == "Planned" or self.production_type == "Adhoc":
			# if not self.marking_list:
			# 	frappe.throw("Marking List is mandatory")
			# if not self.planned_items:
			# 	frappe.throw("Royalty Details is mandatory")
			if self.from_date < '2020-11-01' or self.to_date < '2020-11-01':
				if not self.production_type == "Planned":
					if not self.adhoc_production:
						frappe.errprint("")
						# frappe.throw("Please select Adhoc Production for production entries before 2020-11-01")
				else:
					self.adhoc_production = None
			else:
				if self.production_type == 'Planned':
					self.adhoc_production = None
				if not self.range_name:
					frappe.throw("Range name should be selected")


			self.marking_list = None
			self.planned_items = []
			# self.adhoc_items = []
			# self.adhoc_temp_items = []
			
			if self.discount_amount:
				if self.discount_amount > self.total_royalty:
					frappe.throw("Discount amount cannot be greater than the total royalty.")
				else:
					if self.net_royalty != 0:
						self.net_royalty = self.total_royalty - self.discount_amount
			# if self.less_cft:
			# 	if self.less_cft > self.total_cft:
			# 		frappe.throw("Volume to be subtracted cannot be greater than the total volume.")
			# 	else:
			# 		if self.net_cft != 0:
			# 			self.net_cft = self.total_cft - self.less_cft

			if self.less_qty:
				if self.less_qty > self.total_qty:
					frappe.throw("Quantity to be subtracted cannot be greater than the Total Quantity.")
				else:
					if self.net_qty != 0:
						self.net_qty = self.total_qty - self.less_qty			

		else:
			if not self.range_name:
				frappe.throw("Range Name should be selected")
			self.marking_list = None
			self.planned_items = []

	def get_royalty_details(self):
		#First if condition statement to be kept same if the planned production flow changes to old flow 16/09/2020
		if self.production_type == "Planned":
			#COMMENT CODES FROM BELOW IF PLANNED PRODUCTION FLOW CHAGNES TO OLD FLOW 16/09/2020
			if self.business_activity == "Firewood":
				if self.from_date < '2020-11-01' or self.to_date < '2020-11-01':
						entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.qty) as qty, b.uom, b.item_sub_group, sum(b.qty_in_no) as qty_in_no, b.reading_inches from `tabProduction` a, `tabProduction Product Item` b where a.name = b.parent and b.item_sub_group in ('Firewood','Firewood (Bhutan Ply)','Firewood, Bhutan Furniture') and a.branch = %s and a.posting_date between %s and %s and a.docstatus = 1 and a.royalty_paid = 0 and a.production_type = %s group by b.item_code, b.reading", (self.branch, self.from_date, self.to_date, self.production_type), as_dict=1)
				else:
					if self.range_name:
						entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.qty) as qty, b.uom, b.item_sub_group, sum(b.qty_in_no) as qty_in_no, b.reading_inches from `tabProduction` a, `tabProduction Product Item` b where a.name = b.parent and b.item_sub_group in ('Firewood','Firewood (Bhutan Ply)','Firewood, Bhutan Furniture') and a.branch = %s and a.range = %s and a.posting_date between %s and %s and a.docstatus = 1 and a.royalty_paid = 0 and a.production_type = %s group by b.item_code, b.reading", (self.branch, self.range_name, self.from_date, self.to_date, self.production_type), as_dict=1)

			else:
				if self.from_date < '2020-11-01' or self.to_date < '2020-11-01':
						entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.qty) as qty, b.uom, b.item_sub_group, sum(b.qty_in_no) as qty_in_no, b.reading_inches from `tabProduction` a, `tabProduction Product Item` b where a.name = b.parent and b.item_sub_group != 'Firewood' and a.branch = %s and a.posting_date between %s and %s and a.business_activity = %s and a.docstatus = 1 and a.royalty_paid = 0 and a.production_type = %s group by b.item_code, b.reading", (self.branch, self.from_date, self.to_date, self.business_activity, self.production_type), as_dict=1)
				else:
					if self.range_name:
						entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.reading_in_numbers) as reading_in_numbers, sum(b.qty) as qty, b.uom, b.item_sub_group, sum(b.qty_in_no) as qty_in_no, b.reading_inches, b.reading_select from `tabProduction` a, `tabProduction Product Item` b where a.name = b.parent and b.item_sub_group != 'Firewood' and a.branch = %s and a.range = %s and a.posting_date between %s and %s and a.business_activity = %s and a.docstatus = 1 and a.royalty_paid = 0 and a.production_type = %s group by b.item_code, b.reading, b.reading_select", (self.branch, self.range_name, self.from_date, self.to_date, self.business_activity, self.production_type), as_dict=1)
						# frappe.msgprint(str(entries))

			self.set('adhoc_temp_items', [])
			frappe.db.sql("delete from `tabRoyalty Adhoc Temp` where parent = %s or parent like %s", (self.name,("%" + "New Royalty Payment" + "%")))

			for a in entries:
				d = self.get_adhoc_royalty(a.item_code, a.reading_inches)
				if d[0].based_on == "Item Sub Group":
					d[0].par_name = frappe.db.get_value(d[0].based_on, d[0].particular, "reading_parameter")
				if self.from_date < '2020-07-01' or self.to_date < '2020-07-01':
					if a.item_sub_group == "Pole":
						d[0].qty = a.qty_in_no
						d[0].amount = a.qty_in_no * d[0].royalty_rate
					else:
						d[0].qty = a.qty
						d[0].amount = a.qty * d[0].royalty_rate
				else:
					if a.item_sub_group == "Pole":
						d[0].qty = a.reading_in_numbers
						d[0].amount = a.reading_in_numbers * d[0].royalty_rate
					else:
						d[0].qty = a.qty
						d[0].amount = a.qty * d[0].royalty_rate
				d[0].uom = a.uom
				d[0].reading_select = a.reading_select
				d[0].reference_document = a.name
				# frappe.msgprint(str(d[0]))

				row = self.append('adhoc_temp_items', {})
				row.update(d[0])
				row.save()

			entries = frappe.db.sql("select based_on, particular, timber_class, royalty_rate as rate, from_reading, to_reading, sum(qty) as quantity, uom, sum(amount) as amount, par_name from `tabRoyalty Adhoc Temp` where parent = %s group by particular, timber_class, royalty_rate, from_reading, to_reading,reading_select order by particular", self.name, as_dict=1)
			# frappe.throw(str(entries))
			self.set('adhoc_items', [])
			# Following line replaced by subsequent, by SHIV on 2018/11/13
			#frappe.db.sql("delete from `tabRoyalty Payment Adhoc` where parent = %s or parent like '%New Royalty Payment%'", self.name)
			frappe.db.sql("delete from `tabRoyalty Payment Adhoc` where parent = %s or parent like %s", (self.name,("%" + "New Royalty Payment" + "%")))

			total_royalty = total_qty = 0
			for a in entries:
				row = self.append('adhoc_items', {})
				if a.based_on == "Item":
					a.particular = frappe.db.get_value("Item", a.particular, "item_name")
				if a.par_name:
					a.reading = str(a.par_name) + " : " + str(a.from_reading) + " to " + str(a.to_reading)
				row.update(a)
				row.save()
				total_royalty += a.amount
				total_qty += a.quantity
			self.set_total(total_royalty, total_qty)

			#UNCOMMENT THE FOLLOWING BLOCK OF CODES IF PLANNED PRODUCTION CHANGES TO OLD SYSTEM *commented by Kinley Dorji on 16/09/2020
			# if not self.marking_list:
			# 	frappe.throw("Marking List is Mandatory")
			# entries = frappe.db.sql("select timber_class, timber_type, sum(qty_m3) as qty_m3, sum(qty_cft) as qty_cft, log_rate, log_percent, sum(log_amount) as log_amount, firewood_rate, firewood_percent, sum(firewood_amount) as firewood_amount, sum(royalty_amount) as royalty_amount from `tabMarking List Details` where parent = %s and docstatus = 1 group by timber_class, timber_type order by timber_class", self.marking_list, as_dict=1)

			# self.set("planned_items", [])

			# total_royalty = total_m3 = total_cft = log_amount = timber_amount = total_log = total_timber = 0
			# for d in entries:
			# 	row = self.append('planned_items', {})
			# 	row.update(d)
			# 	total_royalty += d.royalty_amount
			# 	total_m3 += d.qty_m3
			# 	total_cft += d.qty_cft
			# 	log_amount += d.log_amount
			# 	timber_amount += d.firewood_amount 
			# 	total_log += d.qty_cft * d.log_percent / 100
			# 	total_timber += d.qty_m3 * d.firewood_percent / 100

			# self.set_total(total_royalty, total_m3, total_cft, log_amount, timber_amount, total_log, total_timber)
		else:
			if self.from_date > '2020-10-31' or self.to_date > '2020-10-31':
				if not self.range_name or not self.from_date or not self.to_date:
					frappe.throw("Range, From Date and To Date are Mandatory")
			else:
				# if not self.adhoc_production or not self.from_date or not self.to_date:
				# 	frappe.throw("Adhoc Production, From Date and To Date are Mandotory")
				if not self.from_date or not self.to_date:
					frappe.throw("From Date and To Date are Mandotory")
			if self.business_activity == "Firewood":
				if self.from_date > '2020-10-31' or self.to_date > '2020-10-31':
					if self.range_name:
						entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.qty) as qty, b.uom, b.item_sub_group, sum(b.qty_in_no) as qty_in_no, b.reading_inches from `tabProduction` a, `tabProduction Product Item` b where a.name = b.parent and b.item_sub_group in ('Firewood','Firewood (Bhutan Ply)','Firewood, Bhutan Furniture') and a.branch = %s and a.range = %s and a.posting_date between %s and %s and a.docstatus = 1 and a.royalty_paid = 0 and a.production_type = %s group by b.item_code, b.reading", (self.branch, self.range_name, self.from_date, self.to_date, self.production_type), as_dict=1)
				# else:
				# 	if self.adhoc_production:
				# 		entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.qty) as qty, b.uom, b.item_sub_group, sum(b.qty_in_no) as qty_in_no, b.reading_inches from `tabProduction` a, `tabProduction Product Item` b where a.name = b.parent and b.item_sub_group in ('Firewood','Firewood (Bhutan Ply)','Firewood, Bhutan Furniture') and a.branch = %s and a.adhoc_production = %s and a.posting_date between %s and %s and a.docstatus = 1 and a.royalty_paid = 0 and a.production_type = %s group by b.item_code, b.reading", (self.branch, self.adhoc_production, self.from_date, self.to_date, self.production_type), as_dict=1)
				# 	elif self.range_name:
				# 		entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.qty) as qty, b.uom, b.item_sub_group, sum(b.qty_in_no) as qty_in_no, b.reading_inches from `tabProduction` a, `tabProduction Product Item` b where a.name = b.parent and b.item_sub_group in ('Firewood','Firewood (Bhutan Ply)','Firewood, Bhutan Furniture') and a.branch = %s and a.range = %s and a.posting_date between %s and %s and a.docstatus = 1 and a.royalty_paid = 0 and a.production_type  = %s group by b.item_code, b.reading", (self.branch, self.range_name, self.from_date, self.to_date, self.production_type), as_dict=1)
				# 	else:
				# 		entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.qty) as qty, b.uom, b.item_sub_group, \
				# 		sum(b.qty_in_no) as qty_in_no, b.reading_inches from `tabProduction` a, `tabProduction Product Item` b \
				# 		where a.name = b.parent and a.branch = %s and b.item_sub_group in ('Firewood','Firewood (Bhutan Ply)','Firewood, Bhutan Furniture') \
				# 		and a.adhoc_production in (select adhoc_name from `tabAdhoc Production` \
				# 		where range_name = %s) and a.posting_date between %s and %s \
				# 		and a.docstatus = 1 and a.royalty_paid = 0 group by b.item_code, \
				# 		b.reading", (self.branch, self.range_name, self.from_date, self.to_date), as_dict=1)
				
			else:
				if self.from_date > '2020-10-31' or self.to_date > '2020-10-31':
					if self.range_name:
						entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.reading_in_numbers) as reading_in_numbers, sum(b.qty) as qty, b.uom, b.item_sub_group, sum(b.qty_in_no) as qty_in_no, b.reading_inches, b.reading_select from `tabProduction` a, `tabProduction Product Item` b where a.name = b.parent and b.item_sub_group != 'Firewood' and a.branch = %s and a.range = %s and a.posting_date between %s and %s and a.business_activity = %s and a.docstatus = 1 and a.royalty_paid = 0 and a.production_type = %s group by b.item_code, b.reading, b.reading_select", (self.branch, self.range_name, self.from_date, self.to_date, self.business_activity, self.production_type), as_dict=1)
						# entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.qty) as qty, b.uom, b.item_sub_group, sum(b.qty_in_no) as qty_in_no, b.reading_inches from `tabProduction` a, `tabProduction Product Item` b where a.name = b.parent and b.item_sub_group != 'Firewood' and a.branch = %s and a.range = %s and a.posting_date between %s and %s and a.business_activity = %s and a.docstatus = 1 and a.royalty_paid = 0 and b.item_sub_group not in ('Sawn') and a.production_type = %s group by b.item_code, b.reading", (self.branch, self.range_name, self.from_date, self.to_date, self.business_activity, self.production_type), as_dict=1)
				else:
					if self.adhoc_production:
						entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.qty) as qty, b.uom, b.item_sub_group, sum(b.qty_in_no) as qty_in_no, b.reading_inches from `tabProduction` a, `tabProduction Product Item` b where a.name = b.parent and b.item_sub_group != 'Firewood' and a.branch = %s and a.adhoc_production = %s and a.posting_date between %s and %s and a.business_activity = %s and a.docstatus = 1 and a.royalty_paid = 0 and b.item_sub_group not in ('Sawn') and a.production_type = %s group by b.item_code, b.reading", (self.branch, self.adhoc_production, self.from_date, self.to_date, self.business_activity, self.production_type), as_dict=1)
				
					elif self.range_name:
						entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.qty) as qty, b.uom, b.item_sub_group, sum(b.qty_in_no) as qty_in_no, b.reading_inches from `tabProduction` a, `tabProduction Product Item` b where a.name = b.parent and b.item_sub_group != 'Firewood' and a.branch = %s and a.range = %s and a.posting_date between %s and %s and a.business_activity = %s and a.docstatus = 1 and a.royalty_paid = 0 and b.item_sub_group not in ('Sawn') and a.production_type = %s group by b.item_code, b.reading", (self.branch, self.range_name, self.from_date, self.to_date, self.business_activity, self.production_type), as_dict=1)

					else:
						entries = frappe.db.sql("select a.name, b.item_code, b.reading, sum(b.qty) as qty, b.uom, b.item_sub_group, \
						sum(b.qty_in_no) as qty_in_no, b.reading_inches from `tabProduction` a, `tabProduction Product Item` b \
						where a.name = b.parent and a.branch = %s and b.item_sub_group != 'Firewood' \
						and a.adhoc_production in (select adhoc_name from `tabAdhoc Production` \
						where range_name = %s) and a.posting_date between %s and %s \
						and a.docstatus = 1 and a.royalty_paid = 0 group by b.item_code, \
						b.reading", (self.branch, self.range_name, self.from_date, self.to_date), as_dict=1)

			self.set('adhoc_temp_items', [])
			# Following line replaced by subsequent, by SHIV on 2018/11/13
			#frappe.db.sql("delete from `tabRoyalty Adhoc Temp` where parent = %s or parent like '%New Royalty Payment%'", self.name)
			frappe.db.sql("delete from `tabRoyalty Adhoc Temp` where parent = %s or parent like %s", (self.name,("%" + "New Royalty Payment" + "%")))
			for a in entries:
				#frappe.msgprint("item_code: {0} , reading:  {1} ".format(a.item_code, a.reading_inches))
				d = self.get_adhoc_royalty(a.item_code, a.reading_inches)
				if d[0].based_on == "Item Sub Group":
					d[0].par_name = frappe.db.get_value(d[0].based_on, d[0].particular, "reading_parameter")
				if self.from_date < '2020-07-01' or self.to_date < '2020-07-01':
					if a.item_sub_group == "Pole":
						d[0].qty = a.qty_in_no
						d[0].amount = a.qty_in_no * d[0].royalty_rate
					else:
						d[0].qty = a.qty
						d[0].amount = a.qty * d[0].royalty_rate
				else:
					if a.item_sub_group == "Pole":
						d[0].qty = a.reading_in_numbers
						d[0].amount = a.reading_in_numbers * d[0].royalty_rate
					else:
						d[0].qty = a.qty
						d[0].amount = a.qty * d[0].royalty_rate
					# d[0].qty = a.qty
					# d[0].amount = a.qty * d[0].royalty_rate
					
					
				d[0].uom = a.uom
				d[0].reference_document = a.name
				
				row = self.append('adhoc_temp_items', {})
				row.update(d[0])
				row.save()

			entries = frappe.db.sql("select based_on, particular, timber_class, royalty_rate as rate, from_reading, to_reading, sum(qty) as quantity, uom, sum(amount) as amount, par_name from `tabRoyalty Adhoc Temp` where parent = %s group by particular, timber_class, royalty_rate, from_reading, to_reading order by particular", self.name, as_dict=1)
			self.set('adhoc_items', [])
			# Following line replaced by subsequent, by SHIV on 2018/11/13
			#frappe.db.sql("delete from `tabRoyalty Payment Adhoc` where parent = %s or parent like '%New Royalty Payment%'", self.name)
			frappe.db.sql("delete from `tabRoyalty Payment Adhoc` where parent = %s or parent like %s", (self.name,("%" + "New Royalty Payment" + "%")))

			total_royalty = total_qty = 0
			for a in entries:
				row = self.append('adhoc_items', {})
				if a.based_on == "Item":
					a.particular = frappe.db.get_value("Item", a.particular, "item_name")
				if a.par_name:
					a.reading = str(a.par_name) + " : " + str(a.from_reading) + " to " + str(a.to_reading)
				row.update(a)
				row.save()
				total_royalty += a.amount
				total_qty += a.quantity
			self.set_total(total_royalty, total_qty)

	def get_adhoc_royalty(self, item_code, reading):
		sub_group, species = frappe.db.get_value("Item", item_code, ["item_sub_group", "species"])
		if species:
			timber_class = frappe.db.get_value("Timber Species", species, "timber_class")
			if not timber_class:
				timber_class = 0
		else:
			timber_class = 0

		#frappe.msgprint("Timber Class" + str(timber_class) + " Reading " + str(reading)) 

		if reading < 1:
			rate = frappe.db.sql("select b.based_on, b.particular, b.royalty_rate, b.timber_class, b.from_reading, b.to_reading from `tabAdhoc Royalty Setting` a, `tabAdhoc Royalty Setting Item` b where a.name = b.parent and b.particular = %s and %s between a.from_date and a.to_date and b.timber_class=''", (item_code, self.posting_date), as_dict=1)
		else:
			rate = frappe.db.sql("select b.based_on, b.particular, b.royalty_rate, b.timber_class, b.from_reading, b.to_reading from `tabAdhoc Royalty Setting` a, `tabAdhoc Royalty Setting Item` b where a.name = b.parent and b.particular = %s and %s between a.from_date and a.to_date", (item_code, self.posting_date), as_dict=1)
		if not rate:
			rate = frappe.db.sql("select b.based_on, b.particular, b.royalty_rate, b.timber_class, b.from_reading, b.to_reading from `tabAdhoc Royalty Setting` a, `tabAdhoc Royalty Setting Item` b where a.name = b.parent and b.particular = %s and %s between a.from_date and a.to_date", (item_code, self.posting_date), as_dict=1)
		if not rate:
			#frappe.msgprint("subgroup: {0} Date: {1} class: {2} reading: {3} reading:{4} ".format(sub_group, self.posting_date, timber_class, reading, reading))
			if timber_class != 0:
				rate = frappe.db.sql("select b.based_on, b.particular, b.royalty_rate, b.timber_class, b.from_reading, b.to_reading from `tabAdhoc Royalty Setting` a, `tabAdhoc Royalty Setting Item` b where a.name = b.parent and b.particular = %s and %s between a.from_date and a.to_date and b.timber_class = %s and %s >= from_inch and %s <= to_inch", (sub_group, self.from_date, timber_class, reading, reading), as_dict=1, debug=1)
		if not rate:
			if sub_group:
				rate = frappe.db.sql("select b.based_on, b.particular, b.royalty_rate, b.timber_class, b.from_reading, b.to_reading from `tabAdhoc Royalty Setting` a, `tabAdhoc Royalty Setting Item` b where a.name = b.parent and b.based_on = 'Item Sub Group' and b.particular = %s and %s between a.from_date and a.to_date and b.timber_class is NULL", (sub_group, self.posting_date), as_dict=1)

		if not rate:
			frappe.throw("Royalty Rate for {0} has not been defined in Adhoc Royalty Setting".format(frappe.bold(item_code)))
		return rate

	def set_total(self, total_royalty=0, total_qty=0, total_m3=0, log_amount=0, timber_amount=0, total_log=0, total_timber=0):
		self.db_set("total_royalty", total_royalty)
		self.db_set("total_m3", total_m3)
		self.db_set("total_qty", total_qty)
		self.db_set("log_amount", log_amount)
		self.db_set("timber_amount", timber_amount)
		self.db_set("total_log", total_log)
		self.db_set("total_timber", total_timber)

	def on_submit(self):
		self.update_production()
		self.make_royalty_payment()

	def on_cancel(self):
		self.update_production()
		self.update_reference()

	def update_reference(self):
		if not self.journal_entry:
			return
		journal_entry_accounts = frappe.db.sql("""
			select name from `tabJournal Entry Account` where reference_name = '{0}'
		""".format(self.name), as_dict=1)
		if journal_entry_accounts:
			for a in journal_entry_accounts:
				frappe.db.set_value("Journal Entry Account",a.name,"reference_name",None)
		je = frappe.get_doc("Journal Entry",self.journal_entry)
		if je.docstatus != 2:
			je.cancel()

	def update_production(self):
		if self.production_type == "Planned":
			return

		if self.docstatus == 1:
			r_paid = 1
		else:
			r_paid = 0

		for a in frappe.db.sql("select reference_document from `tabRoyalty Adhoc Temp` where parent = %s group by reference_document", self.name, as_dict=1):
			doc = frappe.get_doc("Production", a.reference_document)
			if r_paid and doc.royalty_paid == 1:
				frappe.throw("Royalty for {0} has already been paid. Reload the Royalty Details again".format(frappe.bold(doc.name)))
			if doc.docstatus == 2:
				frappe.throw("{0} is a cancelled document. Please reload the royalty details again".format(frappe.bold(doc.name)))
			doc.db_set("royalty_paid", r_paid)

	def make_royalty_payment(self):
		if not self.total_royalty:
			frappe.throw("Total Royalty Amount is Mandatory")	
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1 
		if self.location:
			je.title = "Royalty payment for " + self.location + " (" + self.name + ")"
		elif self.range_name:
			je.title = "Royalty payment for " + self.range_name + " {" +self.name + ")"
		je.voucher_type = 'Bank Entry'
		je.naming_series = 'Bank Payment Voucher'
		je.remark = 'Payment against : ' + self.name
		je.posting_date = frappe.utils.nowdate()
		je.branch = self.branch
		discount_account = None
		royalty_account = frappe.db.get_value("Production Account Settings", self.company, "default_royalty_account")
		if not royalty_account:
			frappe.throw("Setup Default Royalty Account in Production Account Settings")	
		if self.net_royalty:
			discount_account = frappe.db.get_value("Production Account Settings", self.company, "discount_account")
			if not discount_account:
				frappe.throw("Setup Discount Account in Production Account Settings")
		bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		if not bank_account:
			frappe.throw("Setup Expense Bank Account in Branch")
		#Created if else block and put the old code in if block with the introduction in discount // Kinley Dorji 2021/01/11	
		if self.net_royalty == 0 or self.net_royalty == None:
			je.append("accounts", {
				"account": royalty_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": self.cost_center,
				"debit_in_account_currency": flt(self.total_royalty),
				"debit": flt(self.total_royalty),
				"business_activity": self.business_activity
				})

			je.append("accounts", {
				"account": bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": self.cost_center,
				"credit_in_account_currency": flt(self.total_royalty),
				"credit": flt(self.total_royalty),
				"business_activity": self.business_activity
				})
		else:
			je.append("accounts", {
				"account": royalty_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": self.cost_center,
				"debit_in_account_currency": flt(self.total_royalty),
				"debit": flt(self.total_royalty),
				"business_activity": self.business_activity
				})

			je.append("accounts", {
				"account": bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": self.cost_center,
				"credit_in_account_currency": flt(self.net_royalty),
				"credit": flt(self.net_royalty),
				"business_activity": self.business_activity
				})
			je.append("accounts", {
				"account": bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": self.cost_center,
				"credit_in_account_currency": flt(self.discount_amount),
				"credit": flt(self.discount_amount),
				"business_activity": self.business_activity
				})
		je.save()
		self.db_set("journal_entry", je.name)
		frappe.reload_doctype(self.doctype)
