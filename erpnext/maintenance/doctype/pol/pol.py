# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
'''
------------------------------------------------------------------------------------------------------------------------------------------
Version          Author         Ticket#           CreatedOn          ModifiedOn          Remarks
------------ --------------- --------------- ------------------ -------------------  -----------------------------------------------------
2.0.190509       SHIV		                                     2019/05/09         Refined process for making SL and GL entries
------------------------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, flt, fmt_money, formatdate, nowtime, getdate
from erpnext.accounts.utils import get_fiscal_year
from erpnext.custom_utils import check_future_date, get_branch_cc, prepare_gl, prepare_sl, check_budget_available
from erpnext.controllers.stock_controller import StockController
from erpnext.maintenance.maintenance_utils import get_without_fuel_hire

class POL(StockController):
	def validate(self):
		check_future_date(self.posting_date)
		self.validate_dc()
		self.validate_warehouse()
		#self.set_warehouse()
		self.check_on_dry_hire()
		self.validate_data()
		self.validate_posting_time()
		self.validate_uom_is_integer("stock_uom", "qty")
		self.validate_item()
#
	def on_submit(self):
		self.validate_dc()
		self.validate_data()
		self.check_on_dry_hire()
		self.check_budget()
		if getdate(self.posting_date) > getdate("2018-03-31"):
			self.update_stock_ledger()
		""" ++++++++++ Ver 2.0.190509 Begins ++++++++++ """
		# Ver 2.0.190509, Following method commented by SHIV on 2019/05/20 
		#self.update_general_ledger(1)

		# Ver 2.0.190509, Following method added by SHIV on 2019/05/20
		self.make_gl_entries()
		""" ++++++++++ Ver 2.0.190509 Ends ++++++++++++ """
		self.make_pol_entry()

	def on_cancel(self):
		if getdate(self.posting_date) > getdate("2018-03-31"):
			self.update_stock_ledger()
		""" ++++++++++ Ver 2.0.190509 Begins ++++++++++ """
		# Ver 2.0.190509, Following method commented by SHIV on 2019/05/20 
		#self.update_general_ledger(1)

		# Ver 2.0.190509, Following method added by SHIV on 2019/05/20
		self.make_gl_entries_on_cancel()
		""" ++++++++++ Ver 2.0.190509 Ends ++++++++++++ """
		
		docstatus = frappe.db.get_value("Journal Entry", self.jv, "docstatus")
		if docstatus and docstatus != 2:
			frappe.throw("Cancel the Journal Entry " + str(self.jv) + " and proceed.")

		self.db_set("jv", None)

		self.cancel_budget_entry()
		self.delete_pol_entry()

	def validate_dc(self):
		is_container, no_own_tank = frappe.db.get_value("Equipment Type", frappe.db.get_value("Equipment", self.equipment, "equipment_type") , ["is_container", "no_own_tank"])
		if not self.direct_consumption and not is_container:
			frappe.throw("Non 'Direct Consumption' Receive POL is allowed only for Container Equipments")

		if self.direct_consumption and no_own_tank:
                        frappe.throw("Direct Consumption not permitted for Equipments without own Tank")

	def validate_warehouse(self):
                self.validate_warehouse_branch(self.warehouse, self.branch)
                self.validate_warehouse_branch(self.equipment_warehouse, self.equipment_branch)
                if self.hiring_branch:
                        self.validate_warehouse_branch(self.hiring_warehouse, self.hiring_branch)	

	def set_warehouse(self):
		#cc = get_branch_cc(self.equipment_branch)
		equipment_warehouse = frappe.db.get_value("Cost Center", cc, "warehouse")
		if not equipment_warehouse:
			frappe.throw("No Warehouse is linked with Cost Center <b>" + str(cc) + "</b>")
		self.equipment_warehouse = equipment_warehouse

	def check_on_dry_hire(self):
                record = get_without_fuel_hire(self.equipment, self.posting_date, self.posting_time)
                if record:
                        data = record[0]
                        self.hiring_cost_center = data.cc
                        self.hiring_branch =  data.br
                        self.hiring_warehouse = frappe.db.get_value("Cost Center", data.cc, "warehouse")
                else:
                        self.hiring_cost_center = None
                        self.hiring_branch =  None
                        self.hiring_warehouse = None

	def validate_data(self):
		if not self.fuelbook_branch or not self.equipment_branch:
			frappe.throw("Fuelbook and Equipment Branch are mandatory")

		if flt(self.qty) <= 0 or flt(self.rate) <= 0:
			frappe.throw("Quantity and Rate should be greater than 0")

		if not self.warehouse:
			frappe.throw("Warehouse is Mandatory. Set the Warehouse in Cost Center")

		if not self.equipment_category:
			frappe.throw("Equipment Category Missing")

		if self.branch != self.fuelbook_branch:
			frappe.throw("Transaction Branch and Fuelbook Branch should be same")
	
		if self.book_type == "Own":
			if self.fuelbook != frappe.db.get_value("Equipment", self.equipment, "fuelbook"):
				frappe.throw("Fuelbook (<b>" + str(self.fuelbook) + "</b>) is not registered to <b>" + str(self.equipment) + "</b>")

	def validate_item(self):
		is_stock, is_hsd, is_pol = frappe.db.get_value("Item", self.pol_type, ["is_stock_item", "is_hsd_item", "is_pol_item"])
		if not is_stock:
			frappe.throw(str(self.item_name) + " is not a stock item")

		if not is_hsd and not is_pol:
			frappe.throw(str(self.item_name) + " is not a HSD/POL item")
	
	def check_budget(self):
		if self.hiring_cost_center:
                        cc = self.hiring_cost_center
                else:
                        cc = get_branch_cc(self.equipment_branch)

		account = frappe.db.get_value("Equipment Category", self.equipment_category, "budget_account")
		if not self.is_hsd_item:
			account = frappe.db.get_value("Item", self.pol_type, "expense_account")

		check_budget_available(cc, account, self.posting_date, self.total_amount)
		self.consume_budget(cc, account)

	##
	# Update the Committedd Budget for checking budget availability
	##
	def consume_budget(self, cc, account):
		bud_obj = frappe.get_doc({
			"doctype": "Committed Budget",
			"account": account,
			"cost_center": cc,
			"po_no": self.name,
			"po_date": self.posting_date,
			"amount": self.total_amount,
			"item_code": self.pol_type,
			"poi_name": self.name,
			"date": frappe.utils.nowdate()
			})
		bud_obj.flags.ignore_permissions = 1
		bud_obj.submit()

		consume = frappe.get_doc({
			"doctype": "Consumed Budget",
			"account": account,
			"cost_center": cc,
			"po_no": self.name,
			"po_date": self.posting_date,
			"amount": self.total_amount,
			"pii_name": self.name,
			"item_code": self.pol_type,
			"com_ref": bud_obj.name,
			"date": frappe.utils.nowdate()})
		consume.flags.ignore_permissions=1
		consume.submit()

        """ ++++++++++ Ver 2.0.190509 Begins ++++++++++ """
        # Ver 2.0.190509, Following method added by SHIV on 2019/05/14
	def update_stock_ledger(self):
                # Stock entry for direct_consumption is disabled due to MAP related issues
		if self.direct_consumption:
			return
	
		if self.hiring_warehouse:
                        wh = self.hiring_warehouse
                else:
                        wh = self.equipment_warehouse

		sl_entries = []
		sl_entries.append(self.get_sl_entries(self, {
                                        "item_code": self.pol_type,
					"actual_qty": flt(self.qty), 
					"warehouse": wh, 
					"incoming_rate": round(flt(self.total_amount) / flt(self.qty) , 2)
				}))

		if self.docstatus == 2:
			sl_entries.reverse()

		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')

        # Ver 2.0.190509, Following method commented by SHIV on 2019/05/14

        # Ver 2.0.190509, Following method created by SHIV on 2019/05/20
        def get_gl_entries(self, warehouse_account):
		gl_entries = []
		
		creditor_account = frappe.db.get_value("Company", self.company, "default_payable_account")
		if not creditor_account:
			frappe.throw("Set Default Payable Account in Company")

		expense_account = self.get_expense_account()

		if self.hiring_cost_center:
                        cost_center = self.hiring_cost_center
                else:
                        cost_center = get_branch_cc(self.equipment_branch)

		gl_entries.append(
			self.get_gl_dict({"account": expense_account,
					 "debit": flt(self.total_amount),
					 "debit_in_account_currency": flt(self.total_amount),
					 "cost_center": cost_center,
			})
		)

		gl_entries.append(
			self.get_gl_dict({"account": creditor_account,
					 "credit": flt(self.total_amount),
					 "credit_in_account_currency": flt(self.total_amount),
					 "cost_center": self.cost_center,
					 "party_type": "Supplier",
					 "party": self.supplier,
					 "against_voucher": self.name,
                                         "against_voucher_type": self.doctype,
			})
		)

		if self.hiring_branch:
                        comparing_branch = self.hiring_branch
                else:
                        comparing_branch = self.equipment_branch

		if comparing_branch != self.fuelbook_branch:
			ic_account = frappe.db.get_single_value("Accounts Settings", "intra_company_account")
			if not ic_account:
				frappe.throw("Setup Intra-Company Account in Accounts Settings")

			customer_cc = get_branch_cc(comparing_branch)

			gl_entries.append(
				self.get_gl_dict({"account": ic_account,
						 "credit": flt(self.total_amount),
						 "credit_in_account_currency": flt(self.total_amount),
						 "cost_center": customer_cc,
				})
			)

			gl_entries.append(
				self.get_gl_dict({"account": ic_account,
						 "debit": flt(self.total_amount),
						 "debit_in_account_currency": flt(self.total_amount),
						 "cost_center": self.cost_center,
				})
			)

		return gl_entries
        
        # Ver 2.0.190509, following code commented by SHIV on 2019/05/21

	def get_expense_account(self):
		if self.direct_consumption or getdate(self.posting_date) <= getdate("2018-03-31"):
			if self.is_hsd_item:
				expense_account = frappe.db.get_value("Equipment Category", self.equipment_category, "budget_account")
			else:
				expense_account = frappe.db.get_value("Item", self.pol_type, "expense_account")

			if not expense_account:
				frappe.throw("Set Budget Account in Equipment Category or Item Master")		
		else:
			if self.hiring_warehouse:
                                wh = self.hiring_warehouse
                        else:
                                wh = self.equipment_warehouse
                        expense_account = frappe.db.get_value("Account", {"account_type": "Stock", "warehouse": wh}, "name")
                        if not expense_account:
                                frappe.throw(str(wh) + " is not linked to any account.")

		return expense_account

	##
	# Cancel budget check entry
	##
	def cancel_budget_entry(self):
		frappe.db.sql("delete from `tabCommitted Budget` where po_no = %s", self.name)
		frappe.db.sql("delete from `tabConsumed Budget` where po_no = %s", self.name)

	##
	# make necessary journal entry
	##
	def post_journal_entry(self):
		veh_cat = frappe.db.get_value("Equipment", self.equipment, "equipment_category")
		if veh_cat:
			if veh_cat == "Pool Vehicle":
				pol_account = frappe.db.get_single_value("Maintenance Accounts Settings", "pool_vehicle_pol_expenses")
			else:
				pol_account = frappe.db.get_single_value("Maintenance Accounts Settings", "default_pol_expense_account")
		else:
			frappe.throw("Can not determine machine category")
		#expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		expense_bank_account = frappe.db.get_value("Company", frappe.defaults.get_user_default("Company"), "default_payable_account")
		if not expense_bank_account:
 			frappe.throw("No Default Payable Account set in Company")

		if expense_bank_account and pol_account:
			je = frappe.new_doc("Journal Entry")
			je.flags.ignore_permissions = 1 
			je.title = "POL (" + self.pol_type + " for " + self.equipment_number + ")"
			je.voucher_type = 'Bank Entry'
			je.naming_series = 'Bank Payment Voucher'
			je.remark = 'Payment against : ' + self.name;
			je.posting_date = self.posting_date
			je.branch = self.branch

			je.append("accounts", {
					"account": pol_account,
					"cost_center": self.cost_center,
					"reference_type": "POL",
					"reference_name": self.name,
					"debit_in_account_currency": flt(self.total_amount),
					"debit": flt(self.total_amount),
				})

			je.append("accounts", {
					"account": expense_bank_account,
					"cost_center": self.cost_center,
					"party_type": "Supplier",
					"party": self.supplier,
					"credit_in_account_currency": flt(self.total_amount),
					"credit": flt(self.total_amount),
				})

			je.insert()
			self.db_set("jv", je.name)
		else:
			frappe.throw("Define POL expense account in Maintenance Setting or Expense Bank in Branch")
		
	def make_pol_entry(self):
		if getdate(self.posting_date) <= getdate("2018-03-31"):
                        return
		container = frappe.db.get_value("Equipment Type", frappe.db.get_value("Equipment", self.equipment, "equipment_type"), "is_container")
		if self.equipment_branch == self.fuelbook_branch:
			own = 1
		else:
			own = 0

		con = frappe.new_doc("POL Entry")
		con.flags.ignore_permissions = 1	
		con.equipment = self.equipment
		con.pol_type = self.pol_type
		con.branch = self.equipment_branch
		con.date = self.posting_date
		con.posting_time = self.posting_time
		con.qty = self.qty
		con.reference_type = "POL"
		con.reference_name = self.name
		con.is_opening = 0
		con.own_cost_center = own
		if container:
			con.type = "Stock"
			con.submit()
		
		if self.direct_consumption:
			con1 = frappe.new_doc("POL Entry")
			con1.flags.ignore_permissions = 1	
			con1.equipment = self.equipment
			con1.pol_type = self.pol_type
			con1.branch = self.equipment_branch
			con1.date = self.posting_date
			con1.posting_time = self.posting_time
			con1.qty = self.qty
			con1.reference_type = "POL"
			con1.reference_name = self.name
			con1.type = "Receive"
			con1.is_opening = 0
			con1.own_cost_center = own
			con1.submit()
			
			if container:
				con2 = frappe.new_doc("POL Entry")
				con2.flags.ignore_permissions = 1	
				con2.equipment = self.equipment
				con2.pol_type = self.pol_type
				con2.branch = self.equipment_branch
				con2.date = self.posting_date
				con2.posting_time = self.posting_time
				con2.qty = self.qty
				con2.reference_type = "POL"
				con2.reference_name = self.name
				con2.type = "Issue"
				con2.is_opening = 0
				con2.own_cost_center = own
				con2.submit()


	def delete_pol_entry(self):
		frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", self.name)

