# Copyright (c) 2016, Druk Holding & Investments Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _

#
# Fetching latest Loss Tolerance
#

@frappe.whitelist()
def get_loss_tolerance(): 
	loss_tolerance = frappe.db.sql("select name,loss_tolerance from `tabLoss Tolerance` order by creation desc limit 1;");
	msgprint(_("Fetching Loss Tolerance Details: {0}").format(loss_tolerance))
	return (loss_tolerance);



