# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, now, today, add_days, add_to_date, get_datetime
from frappe.model.document import Document
from erpnext.crm_utils import get_branch_rate, get_branch_location, get_vehicles, get_limit_details
from erpnext.crm_api import init_payment
from frappe.core.doctype.user.user import send_sms
from erpnext.crm_utils import add_user_roles, remove_user_roles

class CustomerOrder(Document):
	def validate(self):
		self.check_for_duplicates()

		if self.selection_based_on == "Lot":
			self.validate_lot_allotment()
		elif self.selection_based_on == "Measurement":
			self.validate_sawn_timber()
		else:
			self.get_item_details()
			self.update_item_rate()
			self.validate_transportation()
			
		self.update_payable_amount()
		self.validate_quantity_limits()
		self.update_user_details()
		self.create_customer()
		self.get_site_details()
		#self.disallow_making_order() commented by Thukten to allow other types of sand delivery

	#Disallow making orders if previous order are not delivered
	def disallow_making_order(self):
		for a in frappe.db.sql("""
						select co.name
						from `tabSales Order` so
						inner join `tabCustomer Order` co
						on so.name=co.sales_order
						where co.customer="{}"
						and so.status = "To Deliver and Bill"
						and so.docstatus=1
						and co.product_category="Sand"
						and co.site="{}"
						""".format(self.customer, self.site), as_dict=True):
			if a.name:
				frappe.throw("Making order not allowed for {} as the previous order {} is still not delivered".format(self.product_category, a.name))

	def before_submit(self):
		self.posting_date = now()

	def on_submit(self):
		self.update_site()
		if self.selection_based_on == "Measurement":
			self.update_sawn_balance()
		self.make_sales_order()
		self.sendsms()

	def on_cancel(self):
		self.update_site()

	def create_customer(self):
		""" create Customer entry automatically if the order doesn't require site """
		if frappe.db.exists("Customer", {"customer_id": self.user}):
			return

		if self.product_category == "Timber" and self.product_group == "Sawn Timber" and flt(self.total_quantity) <= 25:
			pass
		elif frappe.db.exists('Product Category', {'name': self.product_category, 'site_required': 0}):
			pass
		else:
			return

		doc = frappe.new_doc("Customer")
		ua  = frappe.get_doc("User Account", self.user)
		customer_address = [ua.first_name, ua.last_name, ua.billing_address_line1, ua.billing_address_line2,
					ua.billing_dzongkhag, ua.billing_gewog, ua.billing_pincode]
		customer_address = [i for i in customer_address if i]
		customer_address = "\n".join(customer_address) if customer_address else doc.customer_details
		doc.customer_name = ua.full_name if ua.full_name else frappe.db.get_value("User", self.user, "full_name")	
		doc.customer_type = "Domestic Customer"
		doc.customer_group= "Domestic"
		doc.territory	  = "Bhutan"
		doc.customer_id	  = ua.user
		doc.dzongkhag	  = ua.billing_dzongkhag
		doc.mobile_no	  = ua.mobile_no
		doc.customer_details = customer_address
		doc.save(ignore_permissions=True)
		
		add_user_roles(self.user, "CRM Customer")
		self.customer	  = doc.name

	def check_for_duplicates(self):
		if self.site:
	 		if frappe.db.sql("""select count(*) from `tabCustomer Order` where user = "{}" and site = "{}" 
		 		and docstatus = 0 and name != "{}" """.format(self.user, self.site, self.name))[0][0]:
		 		frappe.throw(_("New orders not allowed as you already have unpaid order(s). Please complete the payment/cancel the previous order(s)"))
		else:
			if frappe.db.sql("""select count(*) from `tabCustomer Order` where user = "{}"
				and docstatus = 0 and name != "{}" """.format(self.user, self.name))[0][0]:
				frappe.throw(_("New orders not allowed as you already have unpaid order(s). Please complete the payment/cancel the previous order(s)"))

	def update_user_details(self):
		if frappe.db.exists("User Account", self.user):
			doc = frappe.get_doc("User Account", self.user)
			self.full_name = doc.full_name
			self.mobile_no = doc.mobile_no
			self.alternate_mobile_no = doc.alternate_mobile_no

	def sendsms(self,msg=None):
		if self.docstatus == 1:
			msg = "Your order for {0} is placed successfully. Tran Ref No {1}".\
				format(str(self.item_name)+", Quantity "+str(self.total_quantity)+" "+str(self.uom),self.name)

		mobile_no = frappe.db.get_value("User", self.user, "mobile_no")
		if mobile_no:
			send_sms(mobile_no, msg)

	def initiate_payment(self):
		if self.bank_code and self.bank_account:
			init_payment(self.name, self.bank_code, self.bank_account, flt(self.total_balance_amount))

	#to fetch the challan cost from lot allotment Kinley Dorji 2020/11/30
	def validate_lot_allotment(self):
		challan_cost = 0
		for i in self.lots:
			c = frappe.db.get_value("Lot Allotment",self.lot_allotment_no,"challan_cost")
			if c != 0:
				challan_cost = c
		self.challan_cost = challan_cost
		self.branch = frappe.db.get_value("Lot Allotment",self.lot_allotment_no,"branch")
	
	def validate_sawn_timber(self):
		entries = []
		for d in self.sawns:
			entries.append(str(d.item)+str(d.size)+str(d.length))
		n_dup = set(entries)
		
		if len(entries) != len(n_dup):
			frappe.throw("There cannot be duplicate sawn timber with same measurements"+str(entries))		

	def validate_quantity_limits(self):
		# quantity validations
		if not flt(self.total_quantity):
			frappe.throw(_("Total Quantity cannot be empty "+str(self.total_quantity)))
		elif self.product_category == "Timber" and self.product_group == "Sawn Timber" and flt(self.total_quantity) <= 25:
			return

		# frappe.errprint("CUSTOM_ERROR_LOG: "+str(self.product_category)+str(self.product_group)+str(self.total_quantity))
		self.site_item_name = None
		self.total_available_quantity = None
		limits = get_limit_details(self.product_category, self.user, self.site, self.branch, self.item, self.selection_based_on)
		if limits:
			# frappe.errprint("limits"+str(limits))
			self.site_item_name = limits.site_item_name
			self.total_available_quantity = flt(limits.total_available_quantity,2) if flt(limits.total_available_quantity,2) >= 0 else flt(self.total_quantity,2)
		if flt(self.total_quantity,2) > flt(self.total_available_quantity,2):
			frappe.throw(_("You have crossed your overall quota by quantity {0} {1}")\
				.format(flt(self.total_quantity,2)-flt(self.total_available_quantity,2), self.uom),title="Insufficient Balance")
		if 'has_limit' in limits:
			limits 		= limits.has_limit
			self.order_limit_type = limits.limit_type
			if limits.limit_type == "Quantity":
				balance 			= 0
				self.daily_quantity_limit 	= 0
				self.daily_available_quantity	= 0
				self.weekly_quantity_limit 	= 0
				self.weekly_available_quantity	= 0
				self.monthly_quantity_limit 	= 0
				self.monthly_available_quantity	= 0
				self.yearly_quantity_limit 	= 0
				self.yearly_available_quantity	= 0
				if flt(limits.daily_quantity_limit,2):
					balance = flt(limits.daily_quantity_limit,2)-flt(limits.daily_ordered_quantity,2)
					self.daily_quantity_limit 	= flt(limits.daily_quantity_limit,2)
					self.daily_available_quantity 	= flt(balance,2)
					if flt(balance,2) < flt(self.total_quantity,2):
						frappe.throw(_("You have crossed your daily quota by quantity {0} {1}")\
							.format(flt(self.total_quantity,2)-flt(balance,2), self.uom),title="Insufficient Balance")
				if flt(limits.weekly_quantity_limit,2):
					balance = flt(limits.weekly_quantity_limit,2)-flt(limits.weekly_ordered_quantity,2)
					self.weekly_quantity_limit 	= flt(limits.weekly_quantity_limit,2)
					self.weekly_available_quantity 	= flt(balance,2)
					if flt(balance,2) < flt(self.total_quantity,2):
						frappe.throw(_("You have crossed your weekly quota by quantity {0} {1}")\
							.format(flt(self.total_quantity,2)-flt(balance,2), self.uom),title="Insufficient Balance")
				if flt(limits.monthly_quantity_limit,2):
					balance = flt(limits.monthly_quantity_limit,2)-flt(limits.monthly_ordered_quantity,2)
					self.monthly_quantity_limit 	= flt(limits.monthly_quantity_limit,2)
					self.monthly_available_quantity = flt(balance,2)
					if flt(balance,2) < flt(self.total_quantity,2):
						frappe.throw(_("You have crossed your monthly quota by quantity {0} {1}")\
							.format(flt(self.total_quantity,2)-flt(balance,2), self.uom),title="Insufficient Balance")
				if flt(limits.yearly_quantity_limit,2):
					balance = flt(limits.yearly_quantity_limit,2)-flt(limits.yearly_ordered_quantity,2)
					self.yearly_quantity_limit 	= flt(limits.yearly_quantity_limit,2)
					self.yearly_available_quantity 	= flt(balance,2)
					if flt(balance,2) < flt(self.total_quantity,2):
						frappe.throw(_("You have crossed your yearly quota by quantity {0} {1}")\
							.format(flt(self.total_quantity,2)-flt(balance,2), self.uom),title="Insufficient Balance")
			elif limits.limit_type == "Truck Loads":
				balance 			= 0
				self.daily_quantity_limit_count 	= 0
				self.daily_available_quantity_count	= 0
				self.weekly_quantity_limit_count 	= 0
				self.weekly_available_quantity_count	= 0
				self.monthly_quantity_limit_count 	= 0
				self.monthly_available_quantity_count	= 0
				self.yearly_quantity_limit_count 	= 0
				self.yearly_available_quantity_count	= 0
				if flt(limits.daily_quantity_limit_count,2):
					balance = flt(limits.daily_quantity_limit_count,2)-flt(limits.daily_ordered_quantity_count,2)
					self.daily_quantity_limit_count 	= flt(limits.daily_quantity_limit_count,2)
					self.daily_available_quantity_count 	= flt(balance,2)
					if flt(balance,2) < flt(self.noof_truck_load,2):
						frappe.throw(_("You have crossed your daily quota by {0} truck load(s)")\
							.format(flt(self.noof_truck_load,2)-flt(balance,2)),title="Insufficient Balance")
				if flt(limits.weekly_quantity_limit_count,2):
					balance = flt(limits.weekly_quantity_limit_count,2)-flt(limits.weekly_ordered_quantity_count,2)
					self.weekly_quantity_limit_count 	= flt(limits.weekly_quantity_limit_count,2)
					self.weekly_available_quantity_count 	= flt(balance,2)
					if flt(balance,2) < flt(self.noof_truck_load,2):
						frappe.throw(_("You have crossed your weekly quota by {0} truck load(s)")\
							.format(flt(self.noof_truck_load,2)-flt(balance,2)),title="Insufficient Balance")
				if flt(limits.monthly_quantity_limit_count,2):
					balance = flt(limits.monthly_quantity_limit_count,2)-flt(limits.monthly_ordered_quantity_count,2)
					self.monthly_quantity_limit_count 	= flt(limits.monthly_quantity_limit_count,2)
					self.monthly_available_quantity_count   = flt(balance,2)
					if flt(balance,2) < flt(self.noof_truck_load,2):
						frappe.throw(_("You have crossed your monthly quota by {0} truck load(s)")\
							.format(flt(self.noof_truck_load,2)-flt(balance,2)),title="Insufficient Balance")
				if flt(limits.yearly_quantity_limit_count,2):
					balance = flt(limits.yearly_quantity_limit_count,2)-flt(limits.yearly_ordered_quantity_count,2)
					self.yearly_quantity_limit_count 	= flt(limits.yearly_quantity_limit_count,2)
					self.yearly_available_quantity_count 	= flt(balance,2)
					if flt(balance,2) < flt(self.noof_truck_load,2):
						frappe.throw(_("You have crossed your yearly quota by {0} truck load(s)")\
							.format(flt(self.noof_truck_load,2)-flt(balance,2)),title="Insufficient Balance")

	def get_item_details(self):
		if not self.item:
			frappe.throw(_("Item is mandatory"))

		item = frappe.get_doc("Item", self.item)
		self.item_name		= item.item_name
		self.item_sub_group 	= item.item_sub_group
		self.uom		= item.stock_uom
		
		self.total_available_quantity = 0

		# if condition is added on the existing block of code by SHIV on 2020/11/19
		if self.site and frappe.db.exists('Product Category', {'name': self.product_category, 'site_required': 1}):
			# following line is replanced with subsequent one to accommodate Phase-II by SHIV on 2020/11/19
			#if frappe.db.exists("Site Item", {"parent": self.site, "item_sub_group": self.item_sub_group}):
			if frappe.db.exists("Site Item", {"parent": self.site, "product_category": self.product_category}):
				# following line is replaced with subsequent one to accommodate Phase-II by SHIV on 2020/11/19
				#doc = frappe.get_doc("Site Item", {"parent": self.site, "item_sub_group": self.item_sub_group})
				doc = frappe.get_doc("Site Item", {"parent": self.site, "product_category": self.product_category})
				self.site_item_name     = doc.name
				self.total_available_quantity = flt(doc.balance_quantity)
			else:
				frappe.throw(_("Material {0} not found under Site").format(self.item_sub_group))

	def update_site(self):
		""" update Site Item quantity """
		#if self.approval_status == "Rejected":
		#	return
		#elif self.approval_status == "Pending":
		#	frappe.throw(_("Request cannot be submitted in <b>Pending</b> status"))
	
		# following condition is added by SHIV on 2020/11/23 to accommodate Phase-II
		# do not update Site for product categories which do not require site
		if self.site:
			pass
		elif not frappe.db.exists('Product Category', {'name': self.product_category, 'site_required': 1}):
			return

		if self.product_category == "Timber" and self.product_group == "Sawn Timber" and flt(self.total_quantity) <= 25:
			return

		# following line is replaced with subsequent one to accommodate Phase-II by SHIV on 2020/11/20
		#doc = frappe.get_doc("Site Item", {"parent": self.site, "item_sub_group": self.item_sub_group})
		doc = frappe.get_doc("Site Item", {"parent": self.site, "product_category": self.product_category})
		total_quantity = -1*flt(self.total_quantity) if self.docstatus == 2 else flt(self.total_quantity)
		doc.ordered_quantity = flt(doc.ordered_quantity) + flt(total_quantity)
		doc.balance_quantity = flt(doc.expected_quantity) + flt(doc.extended_quantity) - flt(doc.ordered_quantity)
		doc.save(ignore_permissions=True)

		'''
		# update available_balance for all orders in draft mode
		for i in frappe.get_all('Customer Order', fields=["name"], filters={'user': self.user, 'item_sub_group': self.item_sub_group, 'docstatus': 0}):
			co = frappe.get_doc('Customer Order': i.name)
			co.balance_quantity = flt(doc.balance_quantity)
			co.save(ignore_permissions=True)
		'''
	
	#Method to update sawn balance in Standard Sawn Balance doctype by creating new record //Kinley Dorji 2021/01/16
	def update_sawn_balance(self):
		for i in self.sawns:
			doc = frappe.db.sql("select balance_qty, balance_cft, qty, unit_cft, total_cft from `tabStandard Sawn Balance` where branch = '{}' and item = {} and size = '{}' and length = '{}' and docstatus = 1 order by posting_date desc limit 1".format(self.branch, i.item, i.size, i.length),as_dict=True)
			if not doc:
				frappe.throw("No Balance For Item "+frappe.db.get_value("Item",i.item,"item_name"))
			total_qty = -1*flt(i.qty) if self.docstatus == 1 else flt(i.qty)
			total_cft = -1*flt(i.total_cft) if self.docstatus == 1 else flt(i.total_cft)
			balance_qty = 0
			balance_cft = 0
			unit_cft = None
			qty = 0
			total_cft = 0
			for d in doc:
				if d.balance_qty == 0:
					frappe.throw("No Balance For Item "+frappe.db.get_value("Item",i.item,"item_name"))
				else:
					balance_qty = flt(d.balance_qty) + flt(total_qty)
					balance_cft = flt(d.balance_cft) + flt(total_cft)
					qty = d.qty
					unit_cft = flt(d.unit_cft)
					total_cft = flt(d.total_cft)
			n_doc = frappe.new_doc('Standard Sawn Balance')
			n_doc.branch = self.branch
			n_doc.item = i.item
			n_doc.item_name = frappe.get_value("Item",i.item,"item_name")
			n_doc.size = i.size
			n_doc.length = i.length
			n_doc.balance_qty = balance_qty
			n_doc.balance_cft = balance_cft
			n_doc.qty = qty
			n_doc.unit_cft = unit_cft
			n_doc.total_cft = total_cft
			n_doc.save(ignore_permissions=True)
			n_doc.submit()
			
	def update_distance(self):
		distance = 0
		if self.transport_mode == "Common Pool":
			distance = frappe.db.get_value("Site Distance", {"parent":self.site,"item":self.item,"branch":self.branch}, "distance")
			self.distance = flt(distance) 
			if not flt(distance):
				frappe.throw(_("Distance not available between {0} and site location").format(self.branch))

	def make_sales_order(self):
		if self.selection_based_on != "Measurement":
			if frappe.db.exists("Site Type", {"name": self.site_type, "payment_required": 1}) \
				and not frappe.db.exists("Customer Payment", {"customer_order": self.name, "docstatus": 1}):
				frappe.throw(_("You need to make payment first to place the order"))
		if self.selection_based_on == "Lot":
			lot_items = []
		elif self.selection_based_on == "Measurement":
			sawn_items = []
		else:
			item = frappe.get_doc("Item", self.item)
		
		if self.selection_based_on != "Lot": 
			wh = frappe.db.get_value("CRM Branch Setting", {"branch": self.branch}, "default_warehouse")
			if not wh:
				frappe.throw(_("Default warehouse is not linked for the branch {0}").format(self.branch))
		if not(self.selection_based_on == "Lot" or self.selection_based_on == "Measurement"):
			if frappe.db.exists("Business Activity", item.item_sub_group):
				business_activity = item.item_sub_group
			else:
				business_activity = frappe.db.get_value("Business Activity", {"is_default": 1})
		
		if self.selection_based_on != "Lot" and self.selection_based_on != "Measurement":
			doc = frappe.get_doc({
				"doctype": "Sales Order",
				"branch": self.branch,
				"site": self.site,
				"customer_order": self.name,
				"title": "Sale of {0}({2}) via {1}".format(self.item_sub_group, self.name, self.transport_mode),	
				"naming_series": item.item_group,
				"customer": self.customer,
				"transaction_date": now(),
				"order_type": "Sales",
				"currency": "BTN",
				"conversion_rate": 1,
				"price_list_currency": "BTN",
				"plc_conversion_rate": 1,
				"rate_template": self.transportation_rate if self.transport_mode == "Common Pool" else None,
				"total_distance": flt(self.distance) if self.transport_mode == "Common Pool" else 0,
				"transportation_charges": self.total_transportation_rate if self.transport_mode == "Common Pool" else None,
				"transportation_rate": self.transport_rate if self.transport_mode == "Common Pool" else None,
				"total_quantity": self.total_quantity if self.transport_mode == "Common Pool" else None,	
				"delivery_date": add_days(now(), cint(self.lead_time)),
				"items": [{
					"item_code": self.item,
					"item_name": self.item_name,
					"price_template": self.selling_price,
					"qty": flt(self.total_quantity),
					"rate": flt(self.item_rate),
					"warehouse": wh,
					"business_activity": frappe.db.get_value("Item", self.item, "business_activity")
				}]
			})
			doc.save(ignore_permissions=True)
			doc.submit()
		elif self.selection_based_on == "Lot":
			discount = additional = 0
			for i in self.lots:
				if i.discount != None:
					discount += i.discount
				if i.additional != None:
					additional += i.additional
				lot_list = frappe.db.sql("""
					select a.item, a.item_name, a.lot_number, c.warehouse, a.total_volume, a.total_pieces,
					a.price_list_rate, a.rate, a.amount, a.price_template from
					`tabLot Allotment Details` a, `tabLot Allotment` b, `tabLot List` c
					where b.name = a.parent and b.name = '{}' and
					a.lot_number = '{}' and a.lot_number = c.name and b.docstatus = 1
				""".format(self.lot_allotment_no, i.lot_number), as_dict=True)
				for a in lot_list:
					item_l = frappe.get_doc("Item", a.item)
					if frappe.db.exists("Business Activity", item_l.item_sub_group):
						business_activity_l = item_l.item_sub_group
					else:
						business_activity_l = frappe.db.get_value("Business Activity", {"is_default": 1})
					lot_items.append({"item": a.item, "item_name": a.item_name, "lot_number":a.lot_number, "warehouse": a.warehouse, "total_volume":a.total_volume, "total_pieces":a.total_pieces, "price_template":a.price_template, "price_list_rate":a.price_list_rate, "rate":a.rate, "amount":a.amount, "discount_amount":a.discount_amount, "additional_cost":a.additional_cost, "business_activity":business_activity_l})
			doc = frappe.get_doc({
				"doctype": "Sales Order",
				"branch": self.branch,
				"site": self.site,
				"customer_order": self.name,
				"title": "Sale of {0}({1})".format(self.product_group, self.name),	
				"naming_series": "Timber Products",
				"customer": self.customer,
				"transaction_date": now(),
				"order_type": "Sales",
				"currency": "BTN",
				"conversion_rate": 1,
				"price_list_currency": "BTN",
				"plc_conversion_rate": 1,
				"rate_template": self.transportation_rate if self.transport_mode == "Common Pool" else None,
				"total_distance": flt(self.distance) if self.transport_mode == "Common Pool" else 0,
				"transportation_charges": self.total_transportation_rate if self.transport_mode == "Common Pool" else None,
				"transportation_rate": self.transport_rate if self.transport_mode == "Common Pool" else None,
				"total_quantity": self.total_quantity,	
				"delivery_date": add_days(now(), cint(self.lead_time)),
				"discount_or_cost_amount": discount,
				"additional_cost": additional,
				"challan_cost": self.challan_cost
			})
			# frappe.throw(str(lot_items[0]["item"]))
			for d in lot_items:
				doc.append('items', {
					"item_code": d["item"],
					"item_name": d["item_name"],
					"lot_number": d["lot_number"],
					"price_template": d["price_template"],
					"qty": flt(d["total_volume"], 2),
					"price_list_rate": flt(d["price_list_rate"], 2),
					"rate": flt(d["rate"], 2),
					"amount": flt(d["amount"], 2),
					"total_pieces": d["total_pieces"],
					"warehouse": d["warehouse"],
					"business_activity": frappe.db.get_value("Item", d["item"], "business_activity")
				})
			doc.save(ignore_permissions=True)
			doc.submit()
		elif self.selection_based_on == "Measurement":
			doc = frappe.get_doc({
				"doctype": "Sales Order",
				"branch": self.branch,
				"site": self.site,
				"customer_order": self.name,
				"title": "Sale of {0}({1})".format(self.product_group, self.name),	
				"naming_series": "Timber Products",
				"customer": self.customer,
				"transaction_date": now(),
				"order_type": "Sales",
				"currency": "BTN",
				"conversion_rate": 1,
				"price_list_currency": "BTN",
				"plc_conversion_rate": 1,
				"rate_template": self.transportation_rate if self.transport_mode == "Common Pool" else None,
				"total_distance": flt(self.distance) if self.transport_mode == "Common Pool" else 0,
				"transportation_charges": self.total_transportation_rate if self.transport_mode == "Common Pool" else None,
				"transportation_rate": self.transport_rate if self.transport_mode == "Common Pool" else None,
				"total_quantity": self.total_quantity,	
				"delivery_date": add_days(now(), cint(self.lead_time)),
				"challan_cost": self.challan_cost if self.challan_cost else None
			})
			# frappe.throw(str(lot_items[0]["item"]))
			for d in self.sawns:
				item_s = frappe.get_doc("Item", d.item)
				if frappe.db.exists("Business Activity", item_s.item_sub_group):
					business_activity_s = item_s.item_sub_group
				else:
					business_activity_s = frappe.db.get_value("Business Activity", {"is_default": 1})				
				doc.append('items', {
					"item_code": d.item,
					"item_name": d.item_name,
					"price_template": d.price_template,
					"qty": flt(d.total_cft, 2),
					"price_list_rate": flt(d.rate, 2),
					"rate": flt(d.rate, 2),
					"amount": flt(d.amount, 2),
					"total_pieces": d.qty,
					"warehouse": wh,
					"business_activity": frappe.db.get_value("Item", d.item, "business_activity")
				})
			doc.save(ignore_permissions=True)
			doc.submit()
		self.db_set("sales_order", doc.name)

	def get_site_details(self):
		''' populate site related information '''
		if not self.product_category:
			frappe.throw(_("Please select the product category first"))

		if self.site:
			doc = frappe.get_doc("Site", self.site) 
			self.site_type	= doc.site_type
			self.latitude	= doc.latitude
			self.longitude	= doc.longitude
			self.dzongkhag	= doc.dzongkhag
			self.plot_no	= doc.plot_no
			self.site_location	= doc.location
			self.construction_start_date = doc.construction_start_date
			self.construction_end_date = doc.construction_end_date
			if doc.extension_till_date and doc.extension_till_date > doc.construction_end_date:
				self.construction_end_date = doc.extension_till_date

			if self.construction_start_date and self.construction_end_date \
				and not (str(self.construction_start_date) <= str(today()) <= str(self.construction_end_date)):
				frappe.throw(_("You can place the orders only within the approved construction dates i.e., between {} and {}")\
					.format(self.construction_start_date, self.construction_end_date))
		else:
			if frappe.db.exists("Product Category", {"name": self.product_category, "site_required": 1}):
				if self.product_category == "Timber" and self.product_group == "Sawn Timber" and flt(self.total_quantity) <= 25:
					pass
				else:
					frappe.throw(_("Please select a Site first"))

		if not frappe.db.exists("Customer", {"customer_id": self.user}):
			frappe.throw(_("Customer account not found"))
		self.customer = frappe.db.get_value("Customer", {"customer_id": self.user})

	def validate_transportation(self):
		noof_truck_load = 0

		# following condition added by SHIV on 2020/11/23 to accommodate Phase-II
		# validations for product categories where transport mode is not required
		if frappe.db.exists('Product Category', {'name': self.product_category, 'transport_mode_required': 0}):
			if flt(self.quantity) <= 0:
				frappe.throw(_("Invalid Quantity"))
			self.noof_truck_load = 0
			return

		if not self.transport_mode:
			frappe.throw(_("Please select preferred Transport Mode"))
		elif self.transport_mode == "Common Pool":
			if not flt(self.transport_rate):
				frappe.throw(_("Transportation Rate is not defined for {0}").format(self.branch))

			for i in self.get("pool_vehicles"):
				if flt(i.noof_truck_load) < 0:
					frappe.throw(_("Row#{0}: No.of Truck Loads cannot be a negative value").format(i.idx))
				noof_truck_load += flt(i.noof_truck_load)
		elif self.transport_mode == "Others":
			for i in self.get("pool_vehicles"):
				if flt(i.noof_truck_load) < 0:
					frappe.throw(_("Row#{0}: No.of Truck Loads cannot be a negative value").format(i.idx))
				noof_truck_load += flt(i.noof_truck_load)
		else:
			#get_vehicles(self.user, self.site, self.transport_mode)
			for i in self.get("vehicles"):
				if self.transport_mode == "Private Pool":
					if not cint(frappe.db.get_value("Site", self.site, "allow_private_pool")):
						frappe.throw(_("Private Pool transportation is not permitted for this site"))
					if not frappe.db.exists("Site Private Pool", {"parent": self.site, "vehicle": i.vehicle}):
						frappe.throw(_("Row#{0}: Vehicle {1} is not registered as private pool for site {2}")\
							.format(i.idx,i.vehicle,self.site))

				if self.transport_mode == "Self Owned Transport":
					if not frappe.db.exists("Vehicle", {"user": self.user, "name": i.vehicle}):
						frappe.throw(_("Row#{0}: Vehicle {1} is not registered under your account").format(i.idx,i.vehicle))

				if flt(i.noof_truck_load) < 0:
					frappe.throw(_("Row#{0}: No.of Truck Loads cannot be a negative value for vehicle {1}").format(i.idx,i.vehicle))
				noof_truck_load += flt(i.noof_truck_load)

			if self.transport_mode == "Self Owned Transport" and not frappe.db.exists("Vehicle", {"user": self.user}):
				frappe.throw(_("No vehicle found under your account. Please register your vehicle first"))
			if not self.get("vehicles"):
				frappe.throw(_("You need to select atleast one vehicle for {}").format(self.transport_mode))
		self.noof_truck_load = flt(noof_truck_load)

	def update_item_rate(self):
		''' update item_rate based on selected branch '''
		if not self.branch:
			frappe.throw(_("Material Source Branch is mandatory"))
		elif not self.item:
			frappe.throw(_("Material is mandatory"))
		elif not self.location:
			frappe.throw(_("Material Source Location is mandatory"))

		# get branch details
		item = get_branch_rate(site=self.site, branch=self.branch, item=self.item)
		if item:
			self.lead_time 		 = item[0].lead_time
			self.has_common_pool	 = item[0].has_common_pool
			self.transportation_rate = item[0].tr_name
			self.transport_rate 	 = item[0].tr_rate
			self.distance		 = item[0].distance
		else:
			self.lead_time 		 = 0
			self.has_common_pool	 = 0
			self.transportation_rate = None
			self.transport_rate 	 = 0
			self.distance		 = 0

		# get location based rate details
		item = get_branch_location(site=self.site, item=self.item, branch=self.branch, location=self.location)
		if item:
			self.selling_price = None
			if len(item) > 1:
				for i in item:
					if i.location:
						self.location = i.location
						self.selling_price = i.selling_price
						self.item_rate = i.item_rate
						break
			if not self.selling_price:
				self.location	   = item[0].location
				self.selling_price = item[0].selling_price
				self.item_rate 	   = item[0].item_rate
		else:
			self.selling_price	 = None
			self.item_rate 		 = 0

		if not self.selling_price:
			frappe.throw(_("Selling Price not available"))
		if not self.transport_mode and frappe.db.exists('Product Category', {'name': self.product_category, 'transport_mode_required': 1}):
			frappe.throw(_("Please choose a Transport Mode"))
		if not cint(self.has_common_pool) and self.transport_mode == "Common Pool":
			frappe.throw(_("Selected Warehouse does not offer transportation facility. Choose another Warehouse \
				or consider using Self Owned Transport"))

	def update_payable_amount(self):
		''' update total payable amount '''
		import math
		#Added Selection Based On Check by Kinley Dorji 2020/11/30
		if self.selection_based_on != "Lot" and self.selection_based_on != "Measurement":
			tbl = self.get("pool_vehicles") if self.transport_mode in("Common Pool","Others") else self.get("vehicles")
			total_quantity   	  = 0
			total_transportation_rate = 0

			if frappe.db.exists('Product Category', {'name': self.product_category, 'transport_mode_required': 1}):
				for i in tbl:
					i.quantity	  = flt(i.vehicle_capacity) * flt(i.noof_truck_load)
					total_quantity	 += i.quantity

				if self.transport_mode == "Common Pool":
					total_transportation_rate = flt(self.distance) * flt(total_quantity) * flt(self.transport_rate) 
			else:
				total_quantity = flt(self.quantity)
				total_transportation_rate = 0

			self.total_quantity  	   	= total_quantity
			self.total_item_rate 	  	= flt(total_quantity) * flt(self.item_rate)
			self.total_transportation_rate	= flt(total_transportation_rate) 
			self.total_payable_amount  	= flt(flt(self.total_item_rate) + flt(self.total_transportation_rate),2)
			#if flt(self.total_payable_amount,2) - math.floor(flt(self.total_payable_amount,2)) != 0.50:
			#	self.total_payable_amount = round(self.total_payable_amount)

			self.total_balance_amount	= flt(self.total_payable_amount,2)
		
		elif self.selection_based_on == "Lot":
			self.total_payable_amount = self.total_quantity = 0
			for i in self.lots:
				self.total_payable_amount += flt(i.payable_amount, 2)
				self.total_quantity += flt(i.total_volume, 2)
			self.total_payable_amount += self.challan_cost
			self.total_balance_amount = self.total_payable_amount
			self.quantity = self.total_quantity
		
		else:
			self.total_payable_amount = self.total_quantity = 0
			for i in self.sawns:
				self.total_payable_amount += flt(i.amount, 2)
				self.total_quantity += flt(i.total_cft, 2)
			self.total_balance_amount = self.total_payable_amount
			self.quantity = self.total_quantity

	def get_lots(self, lot_allotment_no = None):
		data = []
		if lot_allotment_no != None:
			lots = frappe.db.sql("""
				select a.lot_number, a.total_volume, a.discount, a.additional, a.payable_amount, a.pieces
				from `tabLot Allotment Lots` a, `tabLot Allotment` b
				where b.name = a.parent and b.name = '{}' and b.docstatus = 1
			""".format(lot_allotment_no),as_dict=True)
		if lots:
			for a in lots:
				data.append({"lot_number": a.lot_number, "total_volume": a.total_volume, "discount":a.discount, "additional":a.discount, "payable_amount": a.payable_amount, "pieces": a.pieces})
			return data
		else:
			frappe.throw("No Lots Alloted")
