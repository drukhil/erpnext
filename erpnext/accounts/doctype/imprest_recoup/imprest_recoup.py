# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, get_datetime, get_url, nowdate, now_datetime, money_in_words
from erpnext.accounts.doctype.imprest_receipt.imprest_receipt import get_opening_balance, update_dependencies
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.custom_utils import check_future_date, get_branch_cc, prepare_gl, prepare_sli
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.utils import get_account_currency
from erpnext.controllers.stock_controller import StockController
from erpnext.custom_workflow import set_user_imprest

class ImprestRecoup(StockController):
	def validate(self):
                self.validate_defaults()
                self.update_defaults()
                self.update_amounts()
                self.validate_amounts()
		self.clearance_date = None
		self.warehouse = frappe.get_doc("Cost Center", self.cost_center).warehouse
		self.check_mandiatory()
		#Custom Funcntion to add the footprints
		set_user_imprest(self)

	def check_mandiatory(self):
		for a in self.get('items'):
			if a.maintain_stock_asset:
				if not a.item:
					frappe.throw("Item Not Selected at Row {0}".format(a.idx))
				doc = frappe.get_doc("Item", a.item)
				a.uom = doc.stock_uom
				a.particulars = doc.item_name
				a.budget_account = doc.expense_account

			else:
				if not a.cost_center:
					frappe.throw("Cost Center is not selected at Row {0}".format(a.idx))
        def on_submit(self):
                for t in frappe.get_all("Imprest Recoup", ["name"], {"branch": self.branch, "imprest_type": self.imprest_type, "entry_date":("<",self.entry_date),"docstatus":0}):
                        msg = '<b>Reference# : <a href="#Form/Imprest Recoup/{0}">{0}</a></b>'.format(t.name)
                        frappe.throw(_("Found unclosed entries. Previous entries needs to be either closed or cancelled in order to determine opening balance for the current transaction.<br>{0}").format(msg),title="Invalid Operation")
                self.make_gl_entry()
		self.update_stock_ledger()
		self.post_receipt_entry()
                update_dependencies(self.branch, self.imprest_type, self.entry_date)
		self.consume_budget()
       		self.update_asset()
		if self.final_settlement and self.opening_balance:
			self.make_adjustment_jv() 

        def on_cancel(self):
		if self.clearance_date:
                        frappe.throw("Already done bank reconciliation.")

                for t in frappe.get_all("Imprest Receipt", ["name"], {"name": self.imprest_receipt, "docstatus":1}):
                        msg = '<b>Reference# : <a href="#Form/Imprest Receipt/{0}">{0}</a></b>'.format(t.name)
                        frappe.throw(_("You need to cancel dependent Imprest Receipt entry first.<br>{0}").format(msg),title="Invalid Operation")
                        
		self.update_stock_ledger()
		self.make_gl_entry()
                update_dependencies(self.branch, self.imprest_type, self.entry_date)
		self.cancel_budget_entry()
		self.delete_asset()
		if self.final_settlement and self.opening_balance:
			self.delete_adjustment_gl_entries()

        def validate_defaults(self):
                if frappe.db.get_value("Branch Imprest Item", {"parent": self.branch, "imprest_type": self.imprest_type}, "imprest_status") == "Closed":
                        frappe.throw(_("Entries are not permitted for the closed imprest type <b>`{0}`</b>.").format(self.imprest_type), title="Imprest closed")
        
        def update_defaults(self):
                # Update posting_date
                #if not self.posting_date:
                if not self.get_db_value("entry_date"):
                        self.entry_date = now_datetime()
                

                if self.docstatus == 0 and self.workflow_state == "Recouped":
                        self.workflow_state = "Waiting Recoupment"

                #self.posting_date = nowdate() #Shiv 2019/01/02, Temporarily replaced with the following to enable backdating as requested by Dorji,BTL
		self.posting_date = nowdate() if not self.posting_date else self.posting_date

                # Update items
                self.purchase_amount = 0.0
                for i in self.items:
                        i.amount = flt(i.quantity)*flt(i.rate)
                        if flt(i.quantity) <= 0.0:
                                frappe.throw(_("Row#{0} : Please input valid data for quantity.").format(i.idx),title="Invalid Quantity")
                        elif flt(i.rate) <= 0.0:
                                frappe.throw(_("Row#{0} : Please input valid data for rate.").format(i.idx),title="Invalid Rate")
                        elif flt(i.amount) < 0.0:
                                frappe.throw(_("Row#{0} : Amount cannot be a negative value.").format(i.idx),title="Invalid Amount")
                        

                        self.purchase_amount += flt(i.amount)
                self.purchase_amount = round(self.purchase_amount, 2)
                
        def update_amounts(self):
                opening_balance = get_opening_balance(self.branch, self.imprest_type, self.name, self.entry_date)
		if flt(opening_balance) != flt(self.opening_balance):
                        #frappe.msgprint(_("Opening balance has been changed from Nu.{0}/- to Nu.{1}/-").format(flt(self.opening_balance),flt(opening_balance)),title="Change in values")
                        self.opening_balance = flt(opening_balance)

                self.closing_balance = flt(self.opening_balance)+flt(self.receipt_amount)-flt(self.purchase_amount)

        def validate_amounts(self):
                if flt(self.opening_balance) <= 0:
                        frappe.throw("Insufficient Opening balance...",title="Insufficient Balance")
                elif flt(self.purchase_amount) < 0:
                        frappe.throw("Purchase amount cannot be a negative value.",title="Invalid Data")
                elif not self.purchase_amount:
                        frappe.throw("Purchase amount cannot be empty.",title="Invalid Data")
                elif flt(self.closing_balance) < 0:
                        frappe.throw("Closing balance cannot be less than value zero.",title="Invalid Data")
                        
                # Validate against imprest limit set under branch
                imprest_limit = frappe.db.get_value("Branch Imprest Item", {"parent": self.branch, "imprest_type": self.imprest_type}, "imprest_limit")
                if not imprest_limit:
                        frappe.throw("Please set imprest limit for the branch.", title="Insufficient Balance")
                else:
                        if flt(self.closing_balance) > flt(imprest_limit):
                                frappe.throw(_("Closing balance cannot exceed imprest limit Nu.{0}/-.").format(flt(imprest_limit)),title="Invalid Data")

        def post_receipt_entry(self):
                if self.purchase_amount:
                        doc = frappe.new_doc("Imprest Receipt")
                        doc.update({
                                "doctype": "Imprest Receipt",
                                "company": self.company,
                                "branch": self.branch,
                                "title": "Recoupment for "+str(self.name),
                                "entry_date": now_datetime(),
				"imprest_type": self.imprest_type,
                                "amount": flt(self.purchase_amount,2),
                                "revenue_bank_account": self.revenue_bank_account,
                                "pay_to_recd_from": self.pay_to_recd_from,
                                "select_cheque_lot": self.select_cheque_lot,
                                "cheque_no": self.cheque_no,
                                "cheque_date": self.cheque_date,
                                "imprest_recoup": self.name,
                                "workflow_state": "Approved"
                        })
                        doc.save(ignore_permissions = True)
                        doc.submit()
                        #self.imprest_receipt = doc.name
                        self.db_set("imprest_receipt", doc.name)
                else:
                        frappe.throw(_("Purchase amount cannot be empty."),title="Invalid Data")
        
	def make_gl_entry(self):
                gl_entries = []
		rev_gl = frappe.db.get_value(doctype="Branch",filters=self.branch,fieldname="revenue_bank_account", as_dict=True)
		if not rev_gl.revenue_bank_account:
                        frappe.throw(_("Bank Account GL is not defined in Branch '{0}'.").format(self.branch),title="Data Not found")
		bank_account = rev_gl.revenue_bank_account
		if self.final_settlement:
			if not self.settlement_account:
                                frappe.throw(_("Settlement Account cannot be blank for final settlement."), title="Missing Data")

			account_type    = frappe.db.get_value("Account", self.settlement_account, "account_type") if not self.settlement_account_type else self.settlement_account_type


                        if account_type != "Payable" and account_type != "Receivable" and self.party:
                                frappe.throw(_("Party is not allowed against Non-payable or Non-receivable accounts."), title="Invalid Data")

                        if (account_type == "Payable" or account_type == "Receivable") and not self.party:
                                frappe.throw(_("Party is mandatory."), title="Missing Data")
	
			bank_account = self.settlement_account

		#stock_items = self.get_stock_items()
		wh = frappe.get_doc("Cost Center", self.cost_center).warehouse
                wh_account = frappe.db.get_value("Account", {"account_type": "Stock", "warehouse": wh}, "name")
                if not wh_account:
                        frappe.throw(str(self.warehouse) + " is not linked to any account.")

                stock_rbnb = self.get_company_default("stock_received_but_not_billed")
                stock_arbnb = self.get_company_default("stock_asset_received_but_not_billed")
                stock_rbnb_currency  = get_account_currency(stock_rbnb) if stock_rbnb else ""
                stock_arbnb_currency = get_account_currency(stock_arbnb) if stock_arbnb else ""
                
		for a in frappe.db.sql(""" select sum(amount) as amount, cost_center, budget_account from `tabImprest Recoup Item` 
				where parent = '{0}' and maintain_stock_asset = 0 and docstatus = 1 
				group by budget_account, cost_center""".format(self.name), as_dict =1):
                        if a.amount and a.cost_center and a.budget_account:
				gl_entries.append(
                                	prepare_gl(self, {"account": a.budget_account,
                                                 "debit": flt(a.amount),
                                                 "debit_in_account_currency": flt(a.amount),
                                                 "cost_center": a.cost_center
                                                })
                                	)


		for b in frappe.db.sql(""" select sum(amount) as amount, item, budget_account from `tabImprest Recoup Item` 
				where parent = '{0}' and maintain_stock_asset = 1 and docstatus = 1 group by item""".format(self.name), as_dict = 1):
			if b.item and frappe.db.exists("Item", {"name": b.item, "is_stock_item": 1}):
				gl_entries.append(
					prepare_gl(self, {"account": wh_account,
							 "debit": flt(b.amount),
							 "debit_in_account_currency": flt(b.amount),
							 "cost_center": self.cost_center
							})
					)


			if b.item and frappe.db.exists("Item", {"name": b.item, "is_fixed_asset": 1}):
				gl_entries.append(
					prepare_gl(self, {"account": stock_arbnb,
                                                 "debit": flt(b.amount),
                                                 "debit_in_account_currency": flt(b.amount),
                                                 "cost_center": self.cost_center
                                                })
                                )

		gl_entries.append(
                                prepare_gl(self, {"account": bank_account,
						 "party_type": self.party_type,
					         "party": self.party,
                                                 "credit": flt(self.purchase_amount),
                                                 "credit_in_account_currency": flt(self.purchase_amount),
                                                 "cost_center": self.cost_center
                                                })
                                )


		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries
                        make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=True)

	def update_stock_ledger(self):
		sl_entries = []
		wh = frappe.get_doc("Cost Center", self.cost_center).warehouse
		for a in self.get("items"):
			if a.item and frappe.db.exists("Item", {"name": a.item, "is_stock_item": 1}):
			       sl_entries.append(
					prepare_sli(self, {
						"item_code": a.item,
						"actual_qty": flt(a.quantity),
						"warehouse": wh,
						"stock_uom": a.uom,
						"incoming_rate": round(flt(a.rate), 2)
					}))

			if self.docstatus == 2:
				sl_entries.reverse()

                self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')
 
        # Update the Committedd Budget for checking budget availability
        ##
        def consume_budget(self):
                for i in self.items:
			if not i.maintain_stock_asset:
				bud_obj = frappe.get_doc({
					"doctype": "Committed Budget",
					"account": i.budget_account,
					"cost_center": self.cost_center,
					"po_no": self.name,
					"po_date": self.posting_date,
					"amount": i.amount,
					"poi_name": self.name,
					"date": frappe.utils.nowdate()
					})
				bud_obj.flags.ignore_permissions = 1
				bud_obj.submit()

				consume = frappe.get_doc({
					"doctype": "Consumed Budget",
					"account": i.budget_account,
					"cost_center": self.cost_center,
					"po_no": self.name,
					"po_date": self.posting_date,
					"amount": i.amount,
					"pii_name": self.name,
					"com_ref": bud_obj.name,
					"date": frappe.utils.nowdate()})
				consume.flags.ignore_permissions=1
				consume.submit()


	##
        # Cancel budget check entry
        ##
        def cancel_budget_entry(self):
                frappe.db.sql("delete from `tabCommitted Budget` where po_no = %s", self.name)
                frappe.db.sql("delete from `tabConsumed Budget` where po_no = %s", self.name)

	
	def update_asset(self):
                for a in self.items:
			if a.maintain_stock_asset:
				item_group = frappe.db.get_value("Item", a.item, "item_group")
				if item_group and item_group == "Fixed Asset":
					ae = frappe.new_doc("Asset Received Entries")
					ae.flags.ignore_permissions = 1
					ae.item_code = a.item
					ae.item_name = a.particulars
					ae.qty = a.quantity
					ae.received_date = self.posting_date
					ae.ref_doc = self.name
					ae.reference_doctype = self.doctype
					ae.branch = self.branch
					ae.submit()

        ##
        #  Delete asset entries
        ##
        def delete_asset(self):
                frappe.db.sql("delete from `tabAsset Received Entries` where ref_doc = %s", self.name)


	def make_adjustment_jv(self):
		expense_bank_account = frappe.get_doc("Branch", self.branch).expense_bank_account
		if not expense_bank_account:
			frappe.throw("Set Up Expense Bank Account in Branch")
                if self.final_settlement and self.closing_balance:
                        je = frappe.new_doc("Journal Entry")
                        je.flags.ignore_permissions = 1
                        je.update({
                                "voucher_type": "Bank Entry",
                                "company": self.company,
                                "remark": "Imprest Adjustment" + self.name,
                                "user_remark": "Imprest Adjustment" + self.name,
                                "posting_date": self.posting_date,
                                "branch": self.branch
                                })

                        #credit account update
                        je.append("accounts", {
                                "account": self.settlement_account,
                                "credit_in_account_currency": self.opening_balance,
                                "reference_type": self.doctype,
                                "reference_name": self.name,
                                "cost_center": self.cost_center
                                })

                        #debit account update
                        je.append("accounts", {
                                "account": expense_bank_account,
                                "debit_in_account_currency": self.opening_balance,
                                "reference_type": self.doctype,
                                "reference_name": self.name,
                                "cost_center": self.cost_center
                                })
                        je.save();
		frappe.msgprint("Asjustment Journal Created <b> {0} </b> ".format(je.name))

	def delete_adjustment_gl_entries(self):
                gl_list = frappe.db.sql(""" select distinct je.name as journal_entry from `tabJournal Entry Account` as jea, `tabJournal Entry` as je where je.voucher_type = 'Bank Entry' and je.name = jea.parent and jea.reference_name = %s and je.docstatus = 1""", self.name, as_dict=True)
                if gl_list:
                        for gl in gl_list:
                                frappe.get_doc("Journal Entry", gl.journal_entry).cancel()
