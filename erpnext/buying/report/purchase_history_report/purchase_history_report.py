# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr

def execute(filters=None):
	validate_filters(filters);
	columns = get_columns();
	queries = construct_query(filters);
	data = get_data(queries, filters);

	return columns, data

def get_data(query, filters=None):
	data = []
	datas = frappe.db.sql(query, (filters.from_date, filters.to_date), as_dict=True);
	for d in datas:
		row = [d.mr_name, d.mr_title, d.mr_date, d.mr_status, d.mr_qty, d.mr_warehouse, d.mr_cost_center, d.sq_name, d.sq_title, d.sq_date, d.sq_discount, d.sq_rate, d.sq_amount, d.sq_discount_percentage, d.po_name, d.po_title, d.po_date, d.po_status, d.vendor, d.item_name, d.item_code, d.po_qty, d.po_rate, d.po_amount, d.po_discount_percentage, d.po_received_qty, d.po_returned_qty, d.po_billed_amt, d.pr_qi, d.pr_qi_date, d.pr_name, d.pr_date, d.actual_receipt_date,(getdate(d.actual_receipt_date) -getdate(d.pr_date)).days or 0, d.transporter_name, d.lr_no, d.pr_bill_no, d.pr_bill_date, d.pr_rejected_warehouse, d.pr_status, d.pr_received_qty, d.pr_rejected_qty, d.pr_qty, d.pr_rate, d.pr_amount, d.pi_name, d.pi_date, d.pi_bill_no, d.pi_bill_date, d.pi_tds_type, d.tds_taxable_amount, d.pi_tds_type, d.tds_amount, d.write_off_amount, d.write_off_description, d.pi_qty, d.pi_amount, d.outstanding_amount]
		data.append(row);
	return data

def construct_query(filters=None):
	query = """select * from
	(select * from
	(select * from (select mr.name as mr_name, mr.title as mr_title, mr.transaction_date as mr_date, mr.status as mr_status, mri.qty as mr_qty, mri.warehouse as mr_warehouse, mri.cost_center as mr_cost_center
		from `tabMaterial Request` mr, `tabMaterial Request Item` mri
		where mr.name = mri.parent and mr.docstatus = 1) as tab_mr
		left join
		(select sq.name as sq_name, sq.title as sq_title, sq.transaction_date as sq_date, sq.discount_amount as sq_discount, sqi.rate as sq_rate, sqi.amount as sq_amount, sqi.discount_percentage as sq_discount_percentage, sqi.material_request as sq_mr
			from `tabSupplier Quotation` sq, `tabSupplier Quotation Item` sqi
			where sq.name = sqi.parent and sq.docstatus = 1) as tab_sq
		on tab_sq.sq_mr = tab_mr.mr_name) as tab_before_orders
	right join
	(select po.name as po_name, po.title as po_title, po.transaction_date as po_date, po.status as po_status, po.supplier as vendor,
			poi.item_name, poi.item_code, poi.qty as po_qty, poi.rate as po_rate, poi.amount as po_amount, poi.discount_percentage as po_discount_percentage, poi.received_qty as po_received_qty, poi.returned_qty as po_returned_qty, poi.billed_amt as po_billed_amt, poi.material_request
			from `tabPurchase Order` po, `tabPurchase Order Item` poi
			where po.name = poi.parent and po.docstatus = 1) as tab_orders
	on tab_orders.material_request = tab_before_orders.mr_name) as tab_final
	left join
	(select * from
			(select (select qi.name from `tabQuality Inspection` qi where qi.purchase_receipt_no = pr.name) as pr_qi, (select qi.report_date from `tabQuality Inspection` qi where qi.purchase_receipt_no = pr.name) as pr_qi_date, pr.name as pr_name, pr.posting_date as pr_date, pr.actual_receipt_date, pr.transporter_name, pr.lr_no, pr.bill_no as pr_bill_no, pr.bill_date as pr_bill_date, pr.rejected_warehouse as pr_rejected_warehouse, pr.status as pr_status,
				pri.received_qty as pr_received_qty, pri.rejected_qty as pr_rejected_qty, pri.qty as pr_qty, pri.rate as pr_rate, pri.amount as pr_amount, pri.purchase_order
				from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pri
				where pr.name = pri.parent and pr.docstatus = 1) as tab_receipt
			left join
			(select pi.name as pi_name, pi.posting_date as pi_date, pi.bill_no as pi_bill_no, pi.bill_date as pi_bill_date, pi.tds_taxable_amount, pi.type as pi_tds_type, pi.tds_amount, pi.write_off_amount, pi.write_off_description, pi.outstanding_amount, 
				pii.qty as pi_qty, pii.amount as pi_amount, pii.purchase_receipt as pi_receipt
				from `tabPurchase Invoice` pi, `tabPurchase Invoice Item` pii
				where pi.name = pii.parent and pi.docstatus = 1) as tab_invoice
			on tab_invoice.pi_receipt = tab_receipt.pr_name) as tab_after_orders
	on tab_final.po_name = tab_after_orders.purchase_order
	where tab_final.po_date between %s and %s
	order by po_date desc
	"""
	return query;

def validate_filters(filters):

	if not filters.fiscal_year:
		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))

	fiscal_year = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"], as_dict=True)
	if not fiscal_year:
		frappe.throw(_("Fiscal Year {0} does not exist").format(filters.fiscal_year))
	else:
		filters.year_start_date = getdate(fiscal_year.year_start_date)
		filters.year_end_date = getdate(fiscal_year.year_end_date)

	if not filters.from_date:
		filters.from_date = filters.year_start_date

	if not filters.to_date:
		filters.to_date = filters.year_end_date

	filters.from_date = getdate(filters.from_date)
	filters.to_date = getdate(filters.to_date)

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

	if (filters.from_date < filters.year_start_date) or (filters.from_date > filters.year_end_date):
		frappe.msgprint(_("From Date should be within the Fiscal Year. Assuming From Date = {0}")\
			.format(formatdate(filters.year_start_date)))

		filters.from_date = filters.year_start_date

	if (filters.to_date < filters.year_start_date) or (filters.to_date > filters.year_end_date):
		frappe.msgprint(_("To Date should be within the Fiscal Year. Assuming To Date = {0}")\
			.format(formatdate(filters.year_end_date)))
		filters.to_date = filters.year_end_date


def get_columns():
	return [
		{
		  "fieldname": "mr_name",
		  "label": "MR No",
		  "fieldtype": "Link",
		  "options": "Material Request",
		  "width": 150
		},
		{
		  "fieldname": "mr_title",
		  "label": "MR Title",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "mr_date",
		  "label": "MR Date",
		  "fieldtype": "Date",
		  "width": 100
		},
		{
		  "fieldname": "mr_status",
		  "label": "MR Status",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "mr_qty",
		  "label": "MR Qty",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "mr_warehouse",
		  "label": "MR Warehouse",
		  "fieldtype": "Link",
		  "options": "Warehouse",
		  "width": 200
		},
		{
		  "fieldname": "mr_cost_center",
		  "label": "MR Cost Center",
		  "fieldtype": "Link",
		  "options": "Cost Center",
		  "width": 200
		},
		{
		  "fieldname": "sq_name",
		  "label": "SQ Name",
		  "fieldtype": "Link",
		  "options": "Supplier Quotation",
		  "width": 150
		},
		{
		  "fieldname": "sq_title",
		  "label": "SQ Title",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "sq_date",
		  "label": "SQ Date",
		  "fieldtype": "Date",
		  "width": 100
		},
		{
		  "fieldname": "sq_discount",
		  "label": "SQ Discount",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "sq_rate",
		  "label": "SQ Rate",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "sq_amount",
		  "label": "SQ Amount",
		  "fieldtype": "Currency",
		  "width": 150
		},
		{
		  "fieldname": "sq_discount_percentage",
		  "label": "SQ Discount %",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "po_name",
		  "label": "PO Name",
		  "fieldtype": "Link",
		  "options": "Purchase Order",
		  "width": 200
		},
		{
		  "fieldname": "po_title",
		  "label": "PO Title",
		  "fieldtype": "Data",
		  "width": 200
		},
		{
		  "fieldname": "po_date",
		  "label": "PO date",
		  "fieldtype": "Date",
		  "width": 100
		},
		
		{
		  "fieldname": "po_status",
		  "label": "PO Status",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "vendor",
		  "label": "Vendor",
		  "fieldtype": "Link",
		  "options": "Supplier",
		  "width": 150
		},
		{
		  "fieldname": "item_name",
		  "label": "Material Name",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "item_code",
		  "label": "Material Code",
		  "fieldtype": "Link",
		  "options": "Item",
		  "width": 150
		},
		{
		  "fieldname": "po_qty",
		  "label": "PO Qty",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "po_rate",
		  "label": "PO Rate",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "po_amount",
		  "label": "PO Amount",
		  "fieldtype": "Currency",
		  "width": 150
		},
		{
		  "fieldname": "po_discount_percentage",
		  "label": "PO Discount %",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "po_received_qty",
		  "label": "PO Received Qty",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "po_returned_qty",
		  "label": "PO Returned Qty",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "po_billed_amt",
		  "label": "PO Billed Amt",
		  "fieldtype": "Currency",
		  "width": 200
		},
		{
		  "fieldname": "pr_qi",
		  "label": "QI No",
		  "fieldtype": "Link",
		  "options": "Quality Inspection",
		  "width": 150
		},
		{
		  "fieldname": "pr_qi_date",
		  "label": "QI date",
		  "fieldtype": "Date",
		  "width": 150
		},
		{
		  "fieldname": "pr_name",
		  "label": "PR Name",
		  "fieldtype": "Link",
		  "options": "Purchase Receipt",
		  "width": 200
		},
		{
		  "fieldname": "pr_date",
		  "label": "PR Date",
		  "fieldtype": "Date",
		  "width": 150
		},
		{
		  "fieldname": "actual_receipt_date",
		  "label": "Actual Rec Date",
		  "fieldtype": "Date",
		  "width": 150
		},
		{
		  "fieldname": "no_of_days",
		  "label": "No. of Days",
		  "fieldtype": "Data",
		  "width": 80
		},
		
		{
		  "fieldname": "transporter_name",
		  "label": "Transporter",
		  "fieldtype": "Link",
		  "options": "Supplier",
		  "width": 150
		},
		{
		  "fieldname": "lr_no",
		  "label": "Vehicle No",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "pr_bill_no",
		  "label": "Vendor Bill",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "pr_bill_date",
		  "label": "Bill Date",
		  "fieldtype": "Date",
		  "width": 150
		},
		{
		  "fieldname": "pr_rejected_warehouse",
		  "label": "Rejected WH",
		  "fieldtype": "Link",
		  "options": "Warehouse",
		  "width": 150
		},
		{
		  "fieldname": "pr_status",
		  "label": "PR Status",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "pr_received_qty",
		  "label": "PR Received Qty",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "pr_rejected_qty",
		  "label": "PR Rej Qty",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "pr_qty",
		  "label": "PR Qty",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "pr_rate",
		  "label": "PR Rate",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "pr_amount",
		  "label": "PR Amount",
		  "fieldtype": "Currency",
		  "width": 150
		},
		{
		  "fieldname": "pi_name",
		  "label": "PI Name",
		  "fieldtype": "Link",
		  "options": "Purchase Invoice",
		  "width": 150
		},
		{
		  "fieldname": "pi_date",
		  "label": "PI Date",
		  "fieldtype": "Date",
		  "width": 150
		},
		{
		  "fieldname": "pi_bill_no",
		  "label": "Vendor PI",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "pi_bill_date",
		  "label": "Vendor PI Date",
		  "fieldtype": "Date",
		  "width": 150
		},
		{
		  "fieldname": "tds_taxable_amount",
		  "label": "Taxable Amount",
		  "fieldtype": "Currency",
		  "width": 200
		},
		{
		  "fieldname": "pi_tds_type",
		  "label": "TDS Type",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "tds_amount",
		  "label": "TDS Amount",
		  "fieldtype": "Currency",
		  "width": 150
		},
		{
		  "fieldname": "write_off_amount",
		  "label": "Fine Amount",
		  "fieldtype": "Currency",
		  "width": 150
		},
		{
		  "fieldname": "write_off_description",
		  "label": "Fine Reason",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "pi_qty",
		  "label": "PI Qty",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "pi_amount",
		  "label": "PI Amount",
		  "fieldtype": "Currency",
		  "width": 150
		},
		{
		  "fieldname": "outstanding_amount",
		  "label": "Outstanding Amount",
		  "fieldtype": "Currency",
		  "width": 200
		},
	]
