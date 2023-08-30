# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DelinkAssetandIssue(Document):
	def on_submit(self):
		frappe.db.sql(""" update `tabAsset Issue Details` set reference_code = " "  where reference_code = '{}' """.format(self.asset))
		
		

		

	
