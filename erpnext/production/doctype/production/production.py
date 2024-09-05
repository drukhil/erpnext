# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
'''
------------------------------------------------------------------------------------------------------------------------------------------
Version          Author         Ticket#           CreatedOn          ModifiedOn          Remarks
------------ --------------- --------------- ------------------ -------------------  -----------------------------------------------------
1.0.190401       SHIV		                                     2019/04/01         Refined process for making SL and GL entries
------------------------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt, fmt_money, formatdate, nowtime, getdate, datetime
from erpnext.accounts.utils import get_fiscal_year
from erpnext.custom_utils import check_future_date, get_branch_cc, prepare_gl, prepare_sl, get_settings_value
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.utils import get_stock_balance

class Production(StockController):
	def validate(self):
		self.validate_date()
		self.validate_if_sawn()
		check_future_date(self.posting_date)
		self.check_cop()
		self.validate_data()
		self.validate_warehouse()
		self.validate_supplier()
		self.validate_items()
		self.validate_posting_time()
		self.validate_lot_list()

	def before_submit(self):
		self.assign_default_dummy()
		self.check_cop()
		if not self.items:
			frappe.throw("Product Item is mandatory to submit the production")
		self.check_cull_qty_file()

	def on_submit(self):
		if self.raw_materials:
			self.update_lot_list(action="submit")

		""" ++++++++++ Ver 1.0.190401 Begins ++++++++++ """
		# Following lines commented by SHIV on 2019/04/01
		#self.make_products_sl_entry()
		#self.make_products_gl_entry()
		#self.make_raw_material_stock_ledger()
		#self.make_raw_material_gl_entry()

		if not self.items:
			frappe.throw("There should be atleast one Product Item")

		# Following lines added by SHIV on 2019/04/01
		self.update_stock_ledger()
		self.make_gl_entries()
		""" ++++++++++ Ver 1.0.190401 Ends ++++++++++++ """
		self.make_production_entry()

	def on_cancel(self):
		self.assign_default_dummy()
		if self.raw_materials:
			self.update_lot_list(action="cancel")

		""" ++++++++++ Ver 1.0.190401 Begins ++++++++++ """
		# Following lines commented by SHIV on 2019/04/01
		#self.make_products_sl_entry()
		#self.make_products_gl_entry()
		#self.make_raw_material_stock_ledger()
		#self.make_raw_material_gl_entry()

		# Following lines added by SHIV on 2019/04/01
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()
		""" ++++++++++ Ver 1.0.190401 Ends ++++++++++++ """
		self.delete_production_entry()

	def validate_date(self):
		if 'Production Master' not in frappe.get_roles(frappe.session.user):
			today = datetime.datetime.now()
			DD = datetime.timedelta(days=3)
			earlier = today - DD
			date = earlier.strftime("%Y-%m-%d")
			if (self.posting_date < date ):
				frappe.throw("You Can Not Create Submit For Posting Date Beyond Past 3 Days "+str(frappe.get_roles(frappe.session.user)))
				frappe.validated = false

	def validate_if_sawn(self):
		if self.business_activity == 'Timber':
			sawn = 0
			for a in self.items:
				if a.item_sub_group in ('Sawn','Off-Cuts','Joinery Products'):
					sawn += 1
			if sawn != len(self.items):
				if sawn > 0:
					frappe.throw("Product Items cannot be mixed for Sawn and Off Cuts items with other Item Sub Group items")
			elif sawn > 0 and sawn == len(self.items):
				# frappe.throw(self.range)
				if self.range != None and self.range != '':
					frappe.throw("Range should be empty for Sawn and Off Cuts Products")
			if sawn == 0:	
				if not self.range or self.range == "":
					frappe.throw("Range is mandatory for Timber Products except Sawn and Off Cuts Products")

	def validate_data(self):
		#Please uncomment below if NRDCL decide to use adhoc_production again
		# if self.production_type == "Adhoc" and not self.adhoc_production:
		# 	frappe.throw("Select Adhoc Production to Proceed")
		if self.production_type == "Planned":
			self.adhoc_production = None
		if self.work_type == "Private" and not self.supplier:
			frappe.throw("Contractor is Mandatory if work type is private")

		# if self.business_activity == 'Timber' or self.business_activity == 'Firewood':
		# 	if not self.range:
		# 		frappe.throw("Range is Mandatory")

	def validate_lot_list(self):
		for item in self.raw_materials:
			if item.lot_list:
				lot_dtl = frappe.db.sql("""
							select lot_no from `tabLot List` ll
							where ll.docstatus = 1 and (ll.sales_order is NULL or ll.sales_order = '')
							and ll.lot_no = '{0}'
							and (ll.sales_order is NULL or ll.sales_order ='')
							and (ll.production is NULL or ll.production ='')
						""".format(item.lot_list), as_dict = True)
				if not lot_dtl:
					frappe.throw("Lot No {0} is either sold or previously transferred".format(item.lot_list))

	def update_lot_list(self, action):
		for item in self.raw_materials:
			if item.lot_list:
				if action == "submit":
					frappe.db.sql("update `tabLot List` set production='{0}' where name = '{1}'".format(self.name, item.lot_list))
				elif action == "cancel":
					frappe.db.sql("update `tabLot List` set production='' where name = '{0}'".format(item.lot_list))

	def validate_warehouse(self):
		self.validate_warehouse_branch(self.warehouse, self.branch)

	def validate_supplier(self):
		if self.work_type == "Private" and not self.supplier:
				frappe.throw("Supplier Is Mandiatory For Production Carried Out By Others")

	########## Ver.2020.11.02 Begins ##########
	# following method created by SHIV on 2020/11/02 
	def validate_raw_materials(self, prod_items):
		''' validation for raw materials '''
		total_raw_material_qty = 0
		if len(self.raw_materials) > 1:
			frappe.throw("Only One Raw Material can be inserted.")
		for item in self.get("raw_materials"):
			if item.item_code not in prod_items:
				frappe.throw(_("{0} is not a Production Item").format(item.item_code))
			if flt(item.qty) <= 0:
				frappe.throw(_("Quantity for <b>{0}</b> cannot be zero or less").format(item.item_code))

			""" ++++++++++ Ver 1.0.190401 Begins ++++++++++ """
			# Following code added by SHIV on 2019/04/01
			item.business_activity = self.business_activity
			item.cost_center = self.cost_center
			item.warehouse = self.warehouse
			item.expense_account = get_expense_account(self.company, item.item_code)
			""" ++++++++++ Ver 1.0.190401 Ends ++++++++++++ """

			if self.business_activity == "Timber":
				if item.uom == "Cft":
					total_raw_material_qty += item.qty
			else:
				total_raw_material_qty += item.qty

		self.total_raw_material_qty = total_raw_material_qty

	# following method created by SHIV on 2020/11/02
	def validate_production_materials(self, prod_items):
		''' validation for production materials '''
		total_production_qty = 0

		for item in self.get("items"):
			doc = frappe.get_doc("Item", item.item_code)
			item.production_type = self.production_type
			item.item_name = doc.item_name
			item.item_group = doc.item_group
			item.item_sub_group = doc.item_sub_group
			item.timber_species = doc.species

			if self.business_activity == "Timber":
				if item.uom == "Cft":
					total_production_qty += item.qty
			else:
				total_production_qty += item.qty

			""" ++++++++++ Ver 1.0.190401 Begins ++++++++++ """
			# Following code added by SHIV on 2019/04/01
			item.business_activity = self.business_activity
			item.cost_center = self.cost_center
			item.warehouse = self.warehouse
			item.expense_account = get_expense_account(self.company, item.item_code)
			""" ++++++++++ Ver 1.0.190401 Ends ++++++++++++ """

			if item.item_code not in prod_items:
				frappe.throw(_("{0} is not a Production Item").format(item.item_code))
			elif flt(item.qty) <= 0:
				frappe.throw(_("Quantity for <b>{0}</b> cannot be zero or less").format(item.item_code))
			elif flt(item.cop) <= 0:
				frappe.throw(_("COP for <b>{0}</b> cannot be zero or less").format(item.item_code))

			if doc.material_measurement and item.reading_select and doc.material_measurement != item.reading_select:
				frappe.throw(_("Row#{}: Only Reading {} is permitted for material {}").format(item.idx, frappe.bold(doc.material_measurement), frppe.get_desk_link("Item", item.item_code)))

			if item.reading_select:
				if not frappe.db.exists("Item Sub Group Measurement", {"parent": item.item_sub_group, "material_measurement": item.reading_select}):
					frappe.throw(_("Row#{}: Reading {} is not permitted for material {}").format(item.idx, frappe.bold(item.reading_select), frappe.get_desk_link("Item", item.item_code)))

				measurement, uom = frappe.db.get_value("Material Measurement", item.reading_select, ["measurement", "uom"])
				item.reading = measurement
			else:
				if frappe.db.exists("Item Sub Group Measurement", {"parent": item.item_sub_group}):
					frappe.throw(_("Row#{}: Reading is mandatory for material {}").format(item.idx, frappe.get_desk_link("Item", item.item_code)))

			# if self.production_type == "Planned":
			# 	continue
			# if item.item_sub_group == "Pole" and flt(item.qty_in_no) <= 0:
			# 	frappe.throw("Number of Poles is required for Adhoc Loggings")
			reading_required, par, min_val, max_val = frappe.db.get_value("Item Sub Group", item.item_sub_group, ["reading_required", "reading_parameter", "minimum_value", "maximum_value"])
			if reading_required:
				if not flt(min_val) <= flt(item.reading) <=  flt(max_val):
					frappe.throw("<b>{0}</b> reading should be between {1} and {2} for {3} for Adhoc Production".format(par, frappe.bold(min_val), frappe.bold(max_val), frappe.bold(item.item_code)))
			elif not item.reading:
				item.reading = 0
			
			# convert to inches
			in_inches = 0
			f = str(item.reading).split(".")
			in_inches = cint(f[0]) * 12
			if len(f) > 1:
				if cint(f[1]) > 11:
					frappe.throw("Inches should be smaller than 12 on row {0}".format(item.idx))
				in_inches += cint(f[1])
			item.reading_inches = in_inches

		self.total_production_qty = total_production_qty

	def validate_items(self):
		prod_items = self.get_production_items()
		self.validate_raw_materials(prod_items)
		self.validate_production_materials(prod_items)

	# following method replaced with the above one by SHIV on 2020/11/02
	'''
	def validate_items(self):
		prod_items = self.get_production_items()
		total_raw_material_qty = total_production_qty = 0

		# raw materials validation
		for item in self.get("raw_materials"):
			if item.item_code not in prod_items:
				frappe.throw(_("{0} is not a Production Item").format(item.item_code))
			if flt(item.qty) <= 0:
				frappe.throw(_("Quantity for <b>{0}</b> cannot be zero or less").format(item.item_code))

			""" ++++++++++ Ver 1.0.190401 Begins ++++++++++ """
			# Following code added by SHIV on 2019/04/01
			item.business_activity = self.business_activity
			item.cost_center = self.cost_center
			item.warehouse = self.warehouse
			item.expense_account = get_expense_account(self.company, item.item_code)
			""" ++++++++++ Ver 1.0.190401 Ends ++++++++++++ """

			if self.business_activity == "Timber":
				if item.uom == "Cft":
					total_raw_material_qty += item.qty
			else:
				total_raw_material_qty += item.qty
				
		# production materials validation
		for item in self.get("items"):
			if self.business_activity == "Timber":
				if item.uom == "Cft":
					total_production_qty += item.qty
			else:
				total_production_qty += item.qty
				
			if item.reading_select == '6.1 - 12 ft (Length)(Post)':
				if item.item_code != '600271':
					frappe.throw("The reading "+str(item.reading_select)+" is only applicable for item 600271: Dangchung (6\'1\" to 12\' -Others) Post")
			
			elif item.reading_select == '12.1 - 17.11 ft (Length)(Post)':
				if item.item_code != '600272':
					frappe.throw("The reading "+str(item.reading_select)+" is only applicable for item 600272: Flag Post (12\'1\" to 17\'11\")- Others Post")

			elif item.reading_select == '18 ft and above (Length)(Post)':
				if item.item_code != '600273':
					frappe.throw("The reading "+str(item.reading_select)+" is only applicable for item 600273: Tsim (18\' Above -others) Post")
			
			else:
				if item.reading_select and item.item_code not in ('600040', '600023', '600077', '600271', '600272', '600273', '600346'):
					#frappe.msgprint(_("{}, {}").format(item.reading_select, item.item_code))
					frappe.throw(_("Row#{}: The reading {} is not applicable for the selected item").format(item.idx, item.reading_select))

			item.production_type = self.production_type
			item.item_name, item.item_group, item.item_sub_group, item.timber_species = frappe.db.get_value("Item", item.item_code, ["item_name", "item_group", "item_sub_group", "species"])
			if item.item_group != "Mineral Products":
				if item.reading_select == "5 ft and Above (Log)":
					item.reading = "5.5"
				elif item.reading_select == "5 ft Below (Log)":
					item.reading = "4.5"
				elif item.reading_select == "0 - 6 ft (Post)":
					item.reading = "5.5"
				
				elif item.reading_select == "0 - 6 ft (Pole)":
					item.reading = "5.5"

				elif item.reading_select == "6.1 - 12 ft (Pole)":
					item.reading = "10"
				elif item.reading_select == "12.1 - 17.11 ft (Pole)":
					item.reading = "15"
				elif item.reading_select == "18 ft Above (Pole)":
					item.reading = "19"
				elif item.reading_select == "0 - 6 ft (Hakaries)":
					item.reading = "5.5"
				elif item.reading_select == "1.2 - 2.11 ft (Pole)":
					item.reading = "1.5"
				elif item.reading_select == "4.11 ft and Below (Log)":
					item.reading = "3.5"
				elif item.reading_select == "6.1 - 12 ft (Length)(Post)":
					item.reading = "7"
				elif item.reading_select == "12.1 - 17.11 ft (Length)(Post)":
					item.reading = "14"
				elif item.reading_select == "18 ft and above (Length)(Post)":
					item.reading = "19"
				else:
					pass

			if item.item_code not in prod_items:
				frappe.throw(_("{0} is not a Production Item").format(item.item_code))
			if flt(item.qty) <= 0:
				frappe.throw(_("Quantity for <b>{0}</b> cannot be zero or less").format(item.item_code))
			if flt(item.cop) <= 0:
				frappe.throw(_("COP for <b>{0}</b> cannot be zero or less").format(item.item_code))
		
			# if self.production_type == "Planned":
			# 	continue
			# if item.item_sub_group == "Pole" and flt(item.qty_in_no) <= 0:
			# 	frappe.throw("Number of Poles is required for Adhoc Loggings")
			reading_required, par, min_val, max_val = frappe.db.get_value("Item Sub Group", item.item_sub_group, ["reading_required", "reading_parameter", "minimum_value", "maximum_value"])
			if reading_required:
				if not flt(min_val) <= flt(item.reading) <=  flt(max_val):
					frappe.throw("<b>{0}</b> reading should be between {1} and {2} for {3} for Adhoc Production".format(par, frappe.bold(min_val), frappe.bold(max_val), frappe.bold(item.item_code)))
			elif not item.reading:
				item.reading = 0
			
			in_inches = 0
			f = str(item.reading).split(".")
			in_inches = cint(f[0]) * 12
			if len(f) > 1:
				if cint(f[1]) > 11:
					frappe.throw("Inches should be smaller than 12 on row {0}".format(item.idx))
				in_inches += cint(f[1])
			item.reading_inches = in_inches

			""" ++++++++++ Ver 1.0.190401 Begins ++++++++++ """
			# Following code added by SHIV on 2019/04/01
			item.business_activity = self.business_activity
			item.cost_center = self.cost_center
			item.warehouse = self.warehouse
			item.expense_account = get_expense_account(self.company, item.item_code)
			""" ++++++++++ Ver 1.0.190401 Ends ++++++++++++ """

		############# Change applied by Thukten on reading  ########
		self.total_raw_material_qty = total_raw_material_qty
		self.total_production_qty = total_production_qty
		######### End Changes ###########
	'''
	########## Ver.2020.11.02 Ends ##########

	def check_cop(self):
		for a in self.items:
			branch = frappe.db.sql("select 1 from `tabCOP Branch` where parent = %s and branch = %s", (a.price_template, self.branch))
			if not branch:
				frappe.throw("Selected COP is not defined for your Branch")

			cop = frappe.db.sql("select cop_amount from `tabCOP Rate Item` where parent = %s and item_sub_group = %s", (a.price_template, str(frappe.db.get_value("Item", a.item_code, "item_sub_group"))), as_dict=1)
			if not cop:
				frappe.throw("COP Rate is not defined for your Item")
			a.cop = cop[0].cop_amount
			if flt(a.cop) <= 0:
				frappe.throw("COP Cannot be zero or less")

	# Added by Sonam Chophel on 10/03/2022
	# If cull qty is greater than 0 then document is necessary
	def check_cull_qty_file(self):
		for a in self.raw_materials:
			if a.cull_qty > 0 and not a.cull_qty_file:
				frappe.throw("Please Attach the relevant documents to support why there is Cull Quantity")

	""" ++++++++++ Ver 1.0.190401 Begins ++++++++++ """
	# update_stock_ledger() method added by SHIV on 2019/04/01
	def update_stock_ledger(self):
			sl_entries = []

			# make sl entries for source warehouse first, then do the target warehouse
			for d in self.get('raw_materials'):
					if cstr(d.warehouse):
							sl_entries.append(self.get_sl_entries(d, {
									"warehouse": cstr(d.warehouse),
									"actual_qty": -1 * flt(d.qty),
									"incoming_rate": 0
							}))
							
			for d in self.get('items'):
					if cstr(d.warehouse):
							sl_entries.append(self.get_sl_entries(d, {
									"warehouse": cstr(d.warehouse),
									"actual_qty": flt(d.qty),
									"incoming_rate": flt(d.cop, 2)
							}))

			if self.docstatus == 2:
					sl_entries.reverse()

			self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')

	# get_gl_entries() method added by SHIV on 2019/04/01
	def get_gl_entries(self, warehouse_account):
			gl_entries = super(Production, self).get_gl_entries(warehouse_account)
			return gl_entries
	""" ++++++++++ Ver 1.0.190401 Ends ++++++++++++ """

	def assign_default_dummy(self):
		self.pol_type = None
		self.stock_uom = None 

	""" ++++++++++ Ver.2020.11.02 Begins ++++++++++++ """
	# Following code is commented by SHIV on 2020/11/02 as the code is no more relevant 
	'''
	def make_products_sl_entry(self):
		sl_entries = []

		for a in self.items:
			sl_entries.append(prepare_sl(self,
				{
					"stock_uom": a.uom,
					"item_code": a.item_code,
					"actual_qty": a.qty,
					"warehouse": self.warehouse,
					"incoming_rate": flt(a.cop, 2)
				}))

		if sl_entries: 
			if self.docstatus == 2:
				sl_entries.reverse()

			self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')


	def make_products_gl_entry(self):
		gl_entries = []

		wh_account = frappe.db.get_value("Account", {"account_type": "Stock", "warehouse": self.warehouse}, "name")
		if not wh_account:
			frappe.throw(str(self.warehouse) + " is not linked to any account.")

		expense_account = get_settings_value("Production Account Settings", self.company, "default_production_account")
		if not expense_account:
						frappe.throw("Setup Default Production Account in Production Account Settings")

		for a in self.items:
			amount = flt(a.qty) * flt(a.cop)

			gl_entries.append(
				prepare_gl(self, {"account": wh_account,
						 "debit": flt(amount),
						 "debit_in_account_currency": flt(amount),
						 "cost_center": self.cost_center,
						 "business_activity": self.business_activity
						})
				)

			gl_entries.append(
				prepare_gl(self, {"account": expense_account,
						 "credit": flt(amount),
						 "credit_in_account_currency": flt(amount),
						 "cost_center": self.cost_center,
						 "business_activity": self.business_activity
						})
				)

		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries
			make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=True)


	def make_raw_material_stock_ledger(self):
		sl_entries = []

		for a in self.raw_materials:
			sl_entries.append(prepare_sl(self,
				{
					"stock_uom": a.uom,
					"item_code": a.item_code,
					"actual_qty": -1 * flt(a.qty),
					"warehouse": self.warehouse,
					"incoming_rate": 0
				}))

		if sl_entries: 
			if self.docstatus == 2:
				sl_entries.reverse()

			self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')

	def make_raw_material_gl_entry(self):
		gl_entries = []

		wh_account = frappe.db.get_value("Account", {"account_type": "Stock", "warehouse": self.warehouse}, "name")
		if not wh_account:
			frappe.throw(str(self.warehouse) + " is not linked to any account.")

		for a in self.raw_materials:
			stock_qty, map_rate = get_stock_balance(a.item_code, self.warehouse, self.posting_date, self.posting_time, with_valuation_rate=True)
						amount = flt(a.qty) * flt(map_rate)

			expense_account = frappe.db.get_value("Item", a.item_code, "expense_account")
			if not expense_account:
				frappe.throw("Set Budget Account in {0}".format(frappe.get_desk_link("Item", a.item_code)))		

			gl_entries.append(
				prepare_gl(self, {"account": wh_account,
						 "credit": flt(amount),
						 "credit_in_account_currency": flt(amount),
						 "cost_center": self.cost_center,
						 "business_activity": self.business_activity
						})
				)

			gl_entries.append(
				prepare_gl(self, {"account": expense_account,
						 "debit": flt(amount),
						 "debit_in_account_currency": flt(amount),
						 "cost_center": self.cost_center,
						 "business_activity": self.business_activity
						})
				)

		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries
			make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=True)
	'''
	""" ++++++++++ Ver.2020.11.02 Ends ++++++++++++ """

	def make_production_entry(self):
		for a in self.items:
			if a.is_rejected_item:
				continue
			doc = frappe.new_doc("Production Entry")
			doc.flags.ignore_permissions = 1
			doc.item_code = a.item_code
			doc.item_name = a.item_name
			doc.item_group = a.item_group
			doc.item_sub_group = a.item_sub_group
			doc.qty = a.qty
			doc.uom = a.uom
			doc.cop = a.cop
			doc.company = self.company
			doc.currency = self.currency
			doc.business_activity = self.business_activity
			doc.branch = self.branch
			doc.location = self.location
			doc.cost_center = self.cost_center
			doc.warehouse = self.warehouse
			doc.posting_date = str(self.posting_date) + " " + str(self.posting_time)
			doc.ref_doc = self.name
			doc.production_type = self.production_type
			doc.adhoc_production = self.adhoc_production
			doc.timber_species = a.timber_species
			doc.cable_line_no = self.cable_line_no
			doc.production_area = self.production_area
			if a.timber_species:
				doc.timber_class, doc.timber_type = frappe.db.get_value("Timber Species", a.timber_species, ["timber_class", "timber_type"])
			doc.submit()

	def delete_production_entry(self):
		frappe.db.sql("delete from `tabProduction Entry` where ref_doc = %s", self.name)

@frappe.whitelist()
def get_expense_account(company, item):
		expense_account = frappe.db.get_value("Production Account Settings", {"company": company}, "default_production_account")
		if not expense_account:
				expense_account = frappe.db.get_value("Item", item, "expense_account")
		return expense_account
