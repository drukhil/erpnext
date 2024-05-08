# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, cint

from frappe import msgprint, _
import frappe.defaults
from frappe.utils import datetime
from frappe.utils.data import get_first_day, get_last_day, add_years, date_diff, today, get_first_day, get_last_day
from frappe.model.mapper import get_mapped_doc
from erpnext.controllers.selling_controller import SellingController
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.naming import make_autoname
from erpnext.custom_autoname import get_auto_name
from erpnext.custom_utils import check_uncancelled_linked_doc, check_future_date
import datetime

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class DeliveryNote(SellingController):
	def __init__(self, arg1, arg2=None):
		super(DeliveryNote, self).__init__(arg1, arg2)
		self.status_updater = [{
			'source_dt': 'Delivery Note Item',
			'target_dt': 'Sales Order Item',
			'join_field': 'so_detail',
			'target_field': 'delivered_qty',
			'target_parent_dt': 'Sales Order',
			'target_parent_field': 'per_delivered',
			'target_ref_field': 'qty',
			'source_field': 'qty',
			'percent_join_field': 'against_sales_order',
			'status_field': 'delivery_status',
			'keyword': 'Delivered',
			'second_source_dt': 'Sales Invoice Item',
			'second_source_field': 'qty',
			'second_join_field': 'so_detail',
			'overflow_type': 'delivery',
			'second_source_extra_cond': """ and exists(select name from `tabSales Invoice`
				where name=`tabSales Invoice Item`.parent and update_stock = 1)"""
		},
		{
			'source_dt': 'Delivery Note Item',
			'target_dt': 'Sales Invoice Item',
			'join_field': 'si_detail',
			'target_field': 'delivered_qty',
			'target_parent_dt': 'Sales Invoice',
			'target_ref_field': 'qty',
			'source_field': 'qty',
			'percent_join_field': 'against_sales_invoice',
			'overflow_type': 'delivery',
			'no_tolerance': 1
		},
		{
			'source_dt': 'Delivery Note Item',
			'target_dt': 'Sales Order Item',
			'join_field': 'so_detail',
			'target_field': 'returned_qty',
			'target_parent_dt': 'Sales Order',
			'source_field': '-1 * qty',
			'extra_cond': """ and exists (select name from `tabDelivery Note` where name=`tabDelivery Note Item`.parent and is_return=1)"""
		}]

	def before_print(self):
		def toggle_print_hide(meta, fieldname):
			df = meta.get_field(fieldname)
			if self.get("print_without_amount"):
				df.set("__print_hide", 1)
			else:
				df.delete_key("__print_hide")

		item_meta = frappe.get_meta("Delivery Note Item")
		print_hide_fields = {
			"parent": ["grand_total", "rounded_total", "in_words", "currency", "total", "taxes"],
			"items": ["rate", "amount", "price_list_rate", "discount_percentage"]
		}

		for key, fieldname in print_hide_fields.items():
			for f in fieldname:
				toggle_print_hide(self.meta if key == "parent" else item_meta, f)

	def set_actual_qty(self):
		for d in self.get('items'):
			if d.item_code and d.warehouse:
				actual_qty = frappe.db.sql("""select actual_qty from `tabBin`
					where item_code = %s and warehouse = %s""", (d.item_code, d.warehouse))
				d.actual_qty = actual_qty and flt(actual_qty[0][0]) or 0

	def so_required(self):
		"""check in manage account if sales order required or not"""
		if frappe.db.get_value("Selling Settings", None, 'so_required') == 'Yes':
			 for d in self.get('items'):
				 if not d.against_sales_order:
					 frappe.throw(_("Sales Order required for Item {0}").format(d.item_code))

	def validate(self):
		if 'Sales Master' not in frappe.get_roles(frappe.session.user):
			today = datetime.datetime.now()
			DD = datetime.timedelta(days=3)
			earlier = today - DD
			date = earlier.strftime("%Y-%m-%d")
			if (self.posting_date < date or get_first_day(self.posting_date)!=get_first_day(today)):
				frappe.throw("You Cannot Save or Submit For Posting Date Beyond Past 3 Days or For Previous Month")
				frappe.validated = false
		check_future_date(self.posting_date)
		self.calculate_transportation()
		super(DeliveryNote, self).validate()
		# discount = additional = self.additional_cost = self.discount_or_cost_amount = 0
		# for d in self.items:
		# 	discount   += d.discount_amount
		# 	additional += d.additional_cost
		# if additional != 0:
		# 	self.additional_cost = additional
			# self.base_net_total = self.total + self.additional_cost
			# self.net_total = self.total + self.additional_cost
			
		# if discount != 0:
		# 	self.discount_or_cost_amount = discount 
			# self.base_net_total = self.total - self.discount_or_cost_amount
			# self.net_total = self.total - self.discount_or_cost_amount
		self.set_status()
		self.so_required()
		self.validate_proj_cust()
		self.check_close_sales_order("against_sales_order")
		self.validate_for_items()
		self.validate_warehouse()
		self.validate_uom_is_integer("stock_uom", "qty")
		self.validate_with_previous_doc()
		self.per_delivered = 100
		#TTPL Code
		self.check_transportation_detail()
		self.update_shipping_address()

		
		from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
		make_packing_list(self)

		self.update_current_stock()
		self.update_stock_qty()

		if not self.installation_status: self.installation_status = 'Not Installed'
		self.validate_conversion_factor()

	#TTPL Code
	def update_shipping_address(self):
		if self.customer_order:
			self.shipping_address_name = frappe.db.get_value("Customer Order", self.customer_order, "site_location")
		if self.customer:
			self.contact_mobile = frappe.db.get_value("Customer", self.customer, "mobile_no")
		
		
	def calculate_transportation(self):
		total_qty = 0
		for a in self.items:
			total_qty += flt(a.qty)

		self.total_quantity = total_qty
		self.transportation_charges = round(flt(self.total_quantity) * flt(self.total_distance) * flt(self.transportation_rate), 2)
		self.discount_amount = flt(self.discount_or_cost_amount) - flt(self.transportation_charges) - flt(self.loading_cost) - flt(self.additional_cost) - flt(self.challan_cost)
				
	def check_transportation_detail(self):
		if self.naming_series == 'Mineral Products':
			if not self.vehicle:
				frappe.throw("Transporter Detail Is Mandiatory For Mineral Products")
			#TTPL Code
			else:
				total_qty = 0.00
				for i in self.items:
					total_qty += i.qty
				if total_qty > 0:
					is_boulder = frappe.db.get_value("Vehicle", self.vehicle, "is_boulder")
					vehicle_capacity = frappe.db.get_value("Vehicle", self.vehicle, "vehicle_capacity")
					if is_boulder == 1:
						if total_qty > vehicle_capacity:
							frappe.throw("Vehicle Capacity is {0}, which is less than total quantity {1}".format(vehicle_capacity, self.total_quantity))
				transport_mode = frappe.db.get_value("Customer Order", self.customer_order, "transport_mode")	
				if self.select_vehicle_queue or transport_mode == "Common Pool":
					local_distance_limit = frappe.db.get_value("CRM Branch Setting", self.branch, "local_distance")
					if self.total_distance > flt(local_distance_limit):
						for a in frappe.db.sql("select name, vehicle, token from `tabLoad Request` where load_status = 'Queued' and crm_branch = '{0}' and vehicle_capacity = {1} order by requesting_date_time, token limit 1".format(self.branch, total_qty), as_dict=True):
							if a.vehicle == self.vehicle:
								self.load_request = a.name
							else:
								frappe.throw("Selected vehicle is already loaded or not from Queue List.")
						if not self.load_request:
							frappe.throw("Vehicle {0} is not registered for queue".format(self.vehicle))
		
	def validate_with_previous_doc(self):
		for fn in (("Sales Order", "against_sales_order", "so_detail"),
				("Sales Invoice", "against_sales_invoice", "si_detail")):
			if filter(None, [getattr(d, fn[1], None) for d in self.get("items")]):
				super(DeliveryNote, self).validate_with_previous_doc({
					fn[0]: {
						"ref_dn_field": fn[1],
						"compare_fields": [["customer", "="], ["company", "="], ["project", "="],
							["currency", "="]],
					},
				})

		if cint(frappe.db.get_single_value('Selling Settings', 'maintain_same_sales_rate')) and not self.is_return:
			self.validate_rate_with_reference_doc([["Sales Order", "against_sales_order", "so_detail"],
				["Sales Invoice", "against_sales_invoice", "si_detail"]])

	def validate_proj_cust(self):
		"""check for does customer belong to same project as entered.."""
		if self.project and self.customer:
			res = frappe.db.sql("""select name from `tabProject`
				where name = %s and (customer = %s or
					ifnull(customer,'')='')""", (self.project, self.customer))
			if not res:
				frappe.throw(_("Customer {0} does not belong to project {1}").format(self.customer, self.project))

	def validate_for_items(self):
		check_list, chk_dupl_itm = [], []
		if cint(frappe.db.get_single_value("Selling Settings", "allow_multiple_items")):
			return

		for d in self.get('items'):
			self.validate_warehouse_branch(d.warehouse, self.branch)
			e = [d.item_code, d.description, d.warehouse, d.against_sales_order or d.against_sales_invoice, d.batch_no or '']
			f = [d.item_code, d.description, d.against_sales_order or d.against_sales_invoice]

			if frappe.db.get_value("Item", d.item_code, "is_stock_item") == 1:
				if e in check_list:
					msgprint(_("Note: Item {0} entered multiple times").format(d.item_code))
				else:
					check_list.append(e)
			else:
				if f in chk_dupl_itm:
					msgprint(_("Note: Item {0} entered multiple times").format(d.item_code))
				else:
					chk_dupl_itm.append(f)
			if d.item_group == "Mineral Products":
				if d.location == "" or d.location == None:
					frappe.throw("Location inside the item table is mandatory for item "+str(d.item_code)+": "+str(d.item_name))

	def validate_warehouse(self):
		super(DeliveryNote, self).validate_warehouse()

		for d in self.get_item_list():
			if frappe.db.get_value("Item", d['item_code'], "is_stock_item") == 1:
				if not d['warehouse']:
					frappe.throw(_("Warehouse required for stock Item {0}").format(d["item_code"]))


	def update_current_stock(self):
		if self.get("_action") and self._action != "update_after_submit":
			for d in self.get('items'):
				d.actual_qty = frappe.db.get_value("Bin", {"item_code": d.item_code,
					"warehouse": d.warehouse}, "actual_qty")

			for d in self.get('packed_items'):
				bin_qty = frappe.db.get_value("Bin", {"item_code": d.item_code,
					"warehouse": d.warehouse}, ["actual_qty", "projected_qty"], as_dict=True)
				if bin_qty:
					d.actual_qty = flt(bin_qty.actual_qty)
					d.projected_qty = flt(bin_qty.projected_qty)

	def update_stock_qty(self):
		for a in self.items:
			if a.sales_uom == a.stock_uom:
				a.stock_qty = a.qty
			else:
				if a.conversion_factor == 1 and  a.sales_uom != a.stock_uom:
					frappe.throw("Conversion Factor cannot be 1 as the Stock UOM and Sales UOM are not same")
				if a.conversion_factor > 1:
					a.stock_qty = flt(a.qty * a.conversion_factor,2)

def update_stock_qty(self):
	for a in self.items:
		if a.sales_uom == a.stock_uom:
			a.stock_qty = a.qty
		else:
			if a.conversion_factor == 1 and  a.sales_uom != a.stock_uom:
				frappe.throw("Conversion Factor cannot be 1 as the Stock UOM and Sales UOM are not same")
			if a.conversion_factor > 1:
				a.stock_qty = flt(a.qty * a.conversion_factor,2)

def update_stock_qty(self):
	for a in self.items:
		if a.sales_uom == a.stock_uom:
			a.stock_qty = a.qty
		else:
			if a.conversion_factor == 1 and  a.sales_uom != a.stock_uom:
				frappe.throw("Conversion Factor cannot be 1 as the Stock UOM and Sales UOM are not same")
			if a.conversion_factor > 1:
				a.stock_qty = flt(a.qty * a.conversion_factor,2)

def update_stock_qty(self):
	for a in self.items:
		if a.sales_uom == a.stock_uom:
			a.stock_qty = a.qty
		else:
			if a.conversion_factor == 1 and  a.sales_uom != a.stock_uom:
				frappe.throw("Conversion Factor cannot be 1 as the Stock UOM and Sales UOM are not same")
			if a.conversion_factor > 1:
				a.stock_qty = flt(a.qty * a.conversion_factor,2)


	def validate_conversion_factor(self):
		for a in self.items:
			if a.sales_uom != a.stock_uom and flt(a.stock_qty,2) != flt(a.qty * a.conversion_factor,2):
				a.stock_qty = flt(a.qty * a.conversion_factor)
				frappe.msgprint("Stock Quantity set to {} due conversion factor".format(flt(a.qty * a.conversion_factor,2)))
			else:
				frappe.msgprint("Stock Qty is after Conversion is {} {}".format(a.stock_qty, a.stock_uom))

	def on_submit(self):
		self.validate_packed_qty()
		# Check for Approving Authority
		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype, self.company, self.base_grand_total, self)
		
		#Creation of DC and Update Load Request
		self.create_delivery_confirmation()

		# update delivered qty in sales order
		self.update_prevdoc_status()
		self.update_billing_status()
		if self.is_return:
			self.dupdate_return_status()

		if not self.is_return:
			self.check_credit_limit()


		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		self.update_stock_ledger()
		self.make_gl_entries()

	def on_cancel(self):
		check_uncancelled_linked_doc(self.doctype, self.name)
		self.check_close_sales_order("against_sales_order")
		self.check_next_docstatus()

		self.update_prevdoc_status()
		self.update_billing_status()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		self.update_stock_ledger()

		self.cancel_packing_slips()

		self.make_gl_entries_on_cancel()

		if self.is_return:
			self.dupdate_return_status()

	def dupdate_return_status(self):
		actual_qty = frappe.db.sql("""
				select dni.item_code, sum(ifnull(dni.qty,0)) as qty from `tabDelivery Note` dn, `tabDelivery Note Item` dni
				where dn.name = dni.parent and dn.docstatus =1 and dn.name = '{0}' group by dni.item_code
			""".format(self.return_against), as_dict = 1)
		returned_qty = frappe.db.sql("""
				select dni.item_code, sum(ifnull(dni.qty,0)) as qty from `tabDelivery Note` dn, `tabDelivery Note Item` dni
				where dn.name = dni.parent and dn.docstatus =1 and dn.return_against = '{0}' group by dni.item_code
			""".format(self.return_against), as_dict =1)
	
			
		ref_qty = actual_qty and actual_qty[0].qty or 0.0
		ret_qty = returned_qty and -flt(returned_qty[0].qty) or 0.0
		per_delivered = ((ref_qty - ret_qty)/ref_qty)*100
		frappe.db.sql(""" update `tabDelivery Note` set per_delivered = {0} where name = '{1}'""".format(per_delivered, self.name))
		frappe.db.sql("""update `tabDelivery Note` set per_delivered  = {0} where name = '{1}'""".format(per_delivered, self.return_against))
		target = frappe.get_doc("Delivery Note", self.return_against)
		target.set_status(update=True)
		return per_delivered
	def check_credit_limit(self):
		from erpnext.selling.doctype.customer.customer import check_credit_limit

		validate_against_credit_limit = False
		for d in self.get("items"):
			if not (d.against_sales_order or d.against_sales_invoice):
				validate_against_credit_limit = True
				break
		if validate_against_credit_limit:
			check_credit_limit(self.customer, self.company)

	def validate_packed_qty(self):
		"""
			Validate that if packed qty exists, it should be equal to qty
		"""
		if not any([flt(d.get('packed_qty')) for d in self.get("items")]):
			return
		has_error = False
		for d in self.get("items"):
			if flt(d.get('qty')) != flt(d.get('packed_qty')):
				frappe.msgprint(_("Packed quantity must equal quantity for Item {0} in row {1}").format(d.item_code, d.idx))
				has_error = True
		if has_error:
			raise frappe.ValidationError

	def check_next_docstatus(self):
		submit_rv = frappe.db.sql("""select t1.name
			from `tabSales Invoice` t1,`tabSales Invoice Item` t2
			where t1.name = t2.parent and t2.delivery_note = %s and t1.docstatus = 1""",
			(self.name))
		if submit_rv:
			frappe.throw(_("Sales Invoice {0} has already been submitted").format(submit_rv[0][0]))

		submit_in = frappe.db.sql("""select t1.name
			from `tabInstallation Note` t1, `tabInstallation Note Item` t2
			where t1.name = t2.parent and t2.prevdoc_docname = %s and t1.docstatus = 1""",
			(self.name))
		if submit_in:
			frappe.throw(_("Installation Note {0} has already been submitted").format(submit_in[0][0]))

	def cancel_packing_slips(self):
		"""
			Cancel submitted packing slips related to this delivery note
		"""
		res = frappe.db.sql("""SELECT name FROM `tabPacking Slip` WHERE delivery_note = %s
			AND docstatus = 1""", self.name)

		if res:
			for r in res:
				ps = frappe.get_doc('Packing Slip', r[0])
				ps.cancel()
			frappe.msgprint(_("Packing Slip(s) cancelled"))

	def update_status(self, status):
		self.set_status(update=True, status=status)
		self.notify_update()
		clear_doctype_notifications(self)

	def update_billing_status(self, update_modified=True):
		updated_delivery_notes = [self.name]
		for d in self.get("items"):
			if d.si_detail and not d.so_detail:
				d.db_set('billed_amt', d.amount, update_modified=update_modified)
			elif d.so_detail:
				updated_delivery_notes += update_billed_amount_based_on_so(d.so_detail, update_modified)

		for dn in set(updated_delivery_notes):
			dn_doc = self if (dn == self.name) else frappe.get_doc("Delivery Note", dn)
			dn_doc.update_billing_percentage(update_modified=update_modified)

		self.load_from_db()

	#TTPL Code
	def create_delivery_confirmation(self):
		now = datetime.datetime.now()
		if self.customer_order:
			total_qty = 0.00
			for i in self.items:
				total_qty += i.qty

			doc = frappe.get_doc("Customer Order", self.customer_order)

			# Update Load Request Queue if transport mode is Common Pool
			# TTPL New Update
			if doc.transport_mode == "Common Pool":
				if self.load_request:
					queue_status = frappe.db.get_value("Load Request", self.load_request, "load_status")
					if queue_status == "Queued":
						frappe.db.sql("update `tabLoad Request` set load_status = 'Loaded', customer='{0}', customer_name = '{1}', location = '{2}', contact_mobile = '{3}', delivery_note = '{4}' where name = '{5}'".format(self.customer, self.customer_name, self.shipping_address_name, self.contact_mobile, self.name, self.load_request))
					else:
						frappe.throw("Cannot select Vehicle status in Load Request(Queue) with {0}".format(queue_status))
				else:
					frappe.throw("Vehicle is not selected from Load Request Queue or Load Request is missing")
			
			# Create Delivery Confirmation document
			dc_doc = frappe.new_doc("Delivery Confirmation")
			dc_doc.branch = self.branch
			dc_doc.confirmation_status = "In Transit"
			dc_doc.exit_date_time = now
			dc_doc.delivery_note = self.name
			dc_doc.user = doc.user
			dc_doc.customer = doc.customer
			dc_doc.vehicle = self.vehicle
			dc_doc.drivers_name = self.drivers_name
			dc_doc.contact_no = self.contact_no
			dc_doc.customer_order = self.customer_order
			dc_doc.transport_mode = doc.transport_mode	
			dc_doc.qty = total_qty
			dc_doc.save(ignore_permissions=True)
			dc_doc.submit()



def update_billed_amount_based_on_so(so_detail, update_modified=True):
	# Billed against Sales Order directly
	billed_against_so = frappe.db.sql("""select sum(amount) from `tabSales Invoice Item`
		where so_detail=%s and (dn_detail is null or dn_detail = '') and docstatus=1""", so_detail)
	billed_against_so = billed_against_so and billed_against_so[0][0] or 0

	# Get all Delivery Note Item rows against the Sales Order Item row
	dn_details = frappe.db.sql("""select dn_item.name, dn_item.amount, dn_item.si_detail, dn_item.parent
		from `tabDelivery Note Item` dn_item, `tabDelivery Note` dn
		where dn.name=dn_item.parent and dn_item.so_detail=%s
			and dn.docstatus=1 and dn.is_return = 0
		order by dn.posting_date asc, dn.posting_time asc, dn.name asc""", so_detail, as_dict=1)

	updated_dn = []
	for dnd in dn_details:
		billed_amt_agianst_dn = 0

		# If delivered against Sales Invoice
		if dnd.si_detail:
			billed_amt_agianst_dn = flt(dnd.amount)
			billed_against_so -= billed_amt_agianst_dn
		else:
			# Get billed amount directly against Delivery Note
			billed_amt_agianst_dn = frappe.db.sql("""select sum(amount) from `tabSales Invoice Item`
				where dn_detail=%s and docstatus=1""", dnd.name)
			billed_amt_agianst_dn = billed_amt_agianst_dn and billed_amt_agianst_dn[0][0] or 0

		# Distribute billed amount directly against SO between DNs based on FIFO
		if billed_against_so and billed_amt_agianst_dn < dnd.amount:
			pending_to_bill = flt(dnd.amount) - billed_amt_agianst_dn
			if pending_to_bill <= billed_against_so:
				billed_amt_agianst_dn += pending_to_bill
				billed_against_so -= pending_to_bill
			else:
				billed_amt_agianst_dn += billed_against_so
				billed_against_so = 0

		frappe.db.set_value("Delivery Note Item", dnd.name, "billed_amt", billed_amt_agianst_dn, update_modified=update_modified)

		updated_dn.append(dnd.parent)

	return updated_dn

def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Shipments'),
	})
	return list_context

def get_invoiced_qty_map(delivery_note):
	"""returns a map: {dn_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for dn_detail, qty in frappe.db.sql("""select dn_detail, qty from `tabSales Invoice Item`
		where delivery_note=%s and docstatus=1""", delivery_note):
			if not invoiced_qty_map.get(dn_detail):
				invoiced_qty_map[dn_detail] = 0
			invoiced_qty_map[dn_detail] += qty

	return invoiced_qty_map

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def update_accounts(source, target):
		target.is_pos = 0
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")

		if len(target.get("items")) == 0:
			frappe.throw(_("All these items have already been invoiced"))

		target.run_method("calculate_taxes_and_totals")

	def update_item(source_doc, target_doc, source_parent):
		#target_doc.qty = source_doc.qty - invoiced_qty_map.get(source_doc.name, 0)
		returned_qty = frappe.db.sql("select b.qty, b.item_code from `tabDelivery Note` a, `tabDelivery Note Item` b  where a.name = b.parent and a.is_return = 1 and a.return_against = \'" + str(source_parent.name) + "\' and a.docstatus = 1;", as_dict=True)
		if returned_qty:
			for a in returned_qty:
				if a.item_code == source_doc.item_code:
					target_doc.qty = source_doc.qty - invoiced_qty_map.get(source_doc.name, 0) + a.qty
		else:
			target_doc.qty = source_doc.qty - invoiced_qty_map.get(source_doc.name, 0)
		target_doc.name_tolerance = "Default"

	doc = get_mapped_doc("Delivery Note", source_name, 	{
		"Delivery Note": {
			"doctype": "Sales Invoice",
			"field_map": {
				"naming_series" : "naming_series",
				"loading_rate" : "rate_per_unit",
				"loading_cost" : "total_loading_amount"  
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Delivery Note Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"name": "dn_detail",
				"parent": "delivery_note",
				"so_detail": "so_detail",
				"against_sales_order": "sales_order",
				"serial_no": "serial_no",
				"cost_center": "cost_center"
			},
			"postprocess": update_item,
			"filter": lambda d: abs(d.qty) - abs(invoiced_qty_map.get(d.name, 0))<=0
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"field_map": {
				"incentives": "incentives"
			},
			"add_if_empty": True
		}
	}, target_doc, update_accounts)

	return doc

@frappe.whitelist()
def make_installation_note(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.installed_qty)
		target.serial_no = obj.serial_no

	doclist = get_mapped_doc("Delivery Note", source_name, 	{
		"Delivery Note": {
			"doctype": "Installation Note",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Delivery Note Item": {
			"doctype": "Installation Note Item",
			"field_map": {
				"name": "prevdoc_detail_docname",
				"parent": "prevdoc_docname",
				"parenttype": "prevdoc_doctype",
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.installed_qty < doc.qty
		}
	}, target_doc)

	return doclist

@frappe.whitelist()
def make_packing_slip(source_name, target_doc=None):
	doclist = get_mapped_doc("Delivery Note", source_name, 	{
		"Delivery Note": {
			"doctype": "Packing Slip",
			"field_map": {
				"name": "delivery_note",
				"letter_head": "letter_head"
			},
			"validation": {
				"docstatus": ["=", 0]
			}
		}
	}, target_doc)

	return doclist


@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc
	return make_return_doc("Delivery Note", source_name, target_doc)


@frappe.whitelist()
def update_delivery_note_status(docname, status):
	dn = frappe.get_doc("Delivery Note", docname)
	dn.update_status(status)
