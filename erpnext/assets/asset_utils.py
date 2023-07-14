from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import msgprint
from frappe.utils import flt, cint

def check_valid_asset_transfer(asset, posting_date):
	doc_list = frappe.db.sql("select name from `tabAsset Movement` where docstatus = 1 and asset = %s and posting_date >= %s", (asset, posting_date), as_dict=1)
	for a in doc_list:
		frappe.throw("Cannot modify asset <b>"+ str(asset) +"</b> since the asset has already been modified at through Asset Movement, Do check the posting Dates" + str(a.name))	

	doc_list = frappe.db.sql("select a.name from `tabBulk Asset Transfer` a, `tabBulk Asset Transfer Item` b where a.name = b.parent and a.docstatus = 1 and b.asset_code = %s and a.posting_date >= %s", (asset, posting_date), as_dict=1)
	for a in doc_list:
		frappe.throw("Cannot modify asset <b>"+ str(asset) +"</b> since the asset has already been modified at through Bulk Asset Transfer " + str(a.name))	



