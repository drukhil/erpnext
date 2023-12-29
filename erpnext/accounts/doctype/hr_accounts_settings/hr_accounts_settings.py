# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class HRAccountsSettings(Document):
	def get_bank_account(branch=None):
		default_bank_account = frappe.db.get_single_value('HR Accounts Settings', 'default_bank_account')
		expense_bank_account = None
		if branch:
			expense_bank_account = frappe.db.get_value('Branch', branch, 'expense_bank_account')

		if not expense_bank_account and not default_bank_account:
			frappe.throw(_("Please set <b>Bank Expense Account</b> under <b>Branch</b> master"))
		return default_bank_account if default_bank_account else expense_bank_account
