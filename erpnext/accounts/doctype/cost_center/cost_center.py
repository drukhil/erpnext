# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.utils import cint

class CostCenter(NestedSet):
	nsm_parent_field = 'parent_cost_center'

	def autoname(self):
		self.name = self.cost_center_name.strip() + ' - ' + \
			frappe.db.get_value("Company", self.company, "abbr")
			

	def validate(self):
		self.validate_mandatory()
		#self.create_customer()
		#self.check_ware_house()
		#self.check_cost_center()


	def on_update(self):
		self.create_branch()
		if frappe.local.flags.ignore_on_update:
			return
		else:
			super(CostCenter, self).on_update()

	def create_branch(self):
		if cint(self.is_group) == 1 or cint(self.branch_created) == 1:
			return
		company = frappe.defaults.get_defaults().company
		b = frappe.new_doc("Branch")
		b.branch = self.cost_center_name.strip()
		b.cost_center = self.name
		b.company = self.company
		b.address = "N.A"
		b.expense_bank_account = frappe.db.get_value("Company", company, "default_bank_account")
		if not frappe.db.get_value("Branch", {'name': b.name}):
			b.save()
		# self.create_customer(b.name)
		self.db_set("branch_created", 1)
		self.db_set("branch", b.name)

	def check_cost_center(self):
		if self.is_group:
			self.branch = ''
		else:
			if not self.branch:
				frappe.throw("Non-Group Cost Center should have a Branch linked")
			ccs = frappe.db.sql("select name from `tabCost Center` where branch = %s and name != %s", (self.branch, self.name), as_dict=True)
			if ccs:
				frappe.throw("Branch <b>" + str(self.branch) + "</b> is already linked to Cost Center <b>"+str(ccs[0].name)+"</b>")

	def check_ware_house(self):
		if not self.is_group and not self.warehouse:
			frappe.throw("Warehouse is mandatory for non-group cost center")

	def validate_mandatory(self):
		if self.cost_center_name != self.company and not self.parent_cost_center:
			frappe.throw(_("Please enter parent cost center"))
		elif self.cost_center_name == self.company and self.parent_cost_center:
			frappe.throw(_("Root cannot have a parent cost center"))
			
	def validate_accounts(self):
		if self.is_group==1 and self.get("budgets"):
			frappe.throw(_("Budget cannot be set for Group Cost Center"))
			
		check_acc_list = []
		for d in self.get('budgets'):
			if d.account:
				account_details = frappe.db.get_value("Account", d.account, 
					["is_group", "company", "report_type"], as_dict=1)
				if account_details.is_group:
					frappe.throw(_("Budget cannot be assigned against Group Account {0}").format(d.account))
				elif account_details.company != self.company:
					frappe.throw(_("Account {0} does not belongs to company {1}").format(d.account, self.company))
				elif account_details.report_type != "Profit and Loss" and account_details.report_type != "Balance Sheet":
					frappe.throw(_("Budget cannot be assigned against {0}, as it's not an Income or Expense account")
						.format(d.account))

				if [d.account, d.fiscal_year] in check_acc_list:
					frappe.throw(_("Account {0} has been entered more than once for fiscal year {1}")
						.format(d.account, d.fiscal_year))
				else:
					check_acc_list.append([d.account, d.fiscal_year])

	def convert_group_to_ledger(self):
		if self.check_if_child_exists():
			frappe.throw(_("Cannot convert Cost Center to ledger as it has child nodes"))
		elif self.check_gle_exists():
			frappe.throw(_("Cost Center with existing transactions can not be converted to ledger"))
		else:
			self.is_group = 0
			self.save()
			return 1

	def convert_ledger_to_group(self):
		if self.check_gle_exists():
			frappe.throw(_("Cost Center with existing transactions can not be converted to group"))
		else:
			self.is_group = 1
			self.save()
			return 1

	def check_gle_exists(self):
		return frappe.db.get_value("GL Entry", {"cost_center": self.name})

	def check_if_child_exists(self):
		return frappe.db.sql("select name from `tabCost Center` where \
			parent_cost_center = %s and docstatus != 2", self.name)

	def before_rename(self, olddn, newdn, merge=False):
		# Add company abbr if not provided
		from erpnext.setup.doctype.company.company import get_name_with_abbr
		new_cost_center = get_name_with_abbr(newdn, self.company)

		# Validate properties before merging
		super(CostCenter, self).before_rename(olddn, new_cost_center, merge, "is_group")

		return new_cost_center

	def after_rename(self, olddn, newdn, merge=False):
		if not merge:
			frappe.db.set_value("Cost Center", newdn, "cost_center_name",
				" - ".join(newdn.split(" - ")[:-1]))
		else:
			super(CostCenter, self).after_rename(olddn, newdn, merge)

	def on_trash(self):
		# checks gl entries and if child exists
		if self.check_gle_exists():
			frappe.throw(_("Cost Center with existing transaction can not be deleted"))
		if self.check_if_child_exists():
			frappe.throw(_("Cannot delete Cost Center as it has child nodes"))

		super(CostCenter, self).on_trash()

	def create_customer(self, branch):
                if self.name and branch and not self.is_group:
                        cus = frappe.db.get_value("Customer", {"cost_center": self.name}, "name")
                        if not cus:
                                doc = frappe.new_doc("Customer")
                                doc.flags.ignore_permissions = 1
                                doc.customer_name = str(self.cost_center_name.strip()).encode('utf-8')
                                doc.customer_type = "Domestic Customer"
                                doc.customer_group = "Internal"
                                doc.territory = "Bhutan"
                                doc.cost_center = self.name
                                doc.branch = branch
                                doc.save()
                        if cus:
                                customer = frappe.get_doc("Customer", cus)
                                customer.flags.ignore_permissions = 1
                                customer.branch = branch
                                customer.save()

                                if self.is_disabled:
                                        customer.db_set("disabled", 1)

