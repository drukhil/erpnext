# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

class Equipment(Document):
	def before_save(self):
		for i, item in enumerate(sorted(self.operators, key=lambda item: item.start_date), start=1):
			item.idx = i

	def validate(self):
		if self.asset_code:
			doc = frappe.get_doc("Asset", self.asset_code)
			doc.db_set("equipment_number", self.name)

		if not self.equipment_number:
			self.equipment_number = self.name
		'''if self.equipment_history:
			self.set("equipment_history", {})'''
		if not self.from_date:
			self.from_date = nowdate()

		if not self.equipment_history:
                        self.create_equipment_history(branch = self.branch, on_date = self.from_date, ref_doc = self.name, purpose = 'Submit')
		
		if len(self.operators) > 1:
			for a in range(len(self.operators)-1):
				self.operators[a].end_date = frappe.utils.data.add_days(getdate(self.operators[a + 1].start_date), -1)
			self.operators[len(self.operators) - 1].end_date = ''

		if self.is_disabled == 1:
                        last_row = self.equipment_history[len(self.equipment_history) - 1]
                        if not last_row.to_date:
                                last_row.to_date = getdate(nowdate())
		if self.not_cdcl == 0:
			if not self.asset_code:
				frappe.throw("Asset Code is mandatory, Please Fill the Asset Code!")
		self.set_name()
                if self.maintain_in_others_asset:
			if not self.custodian:
				frappe.theow("Custodian is Required For Others Equipment")
                        others = frappe.db.sql(""" select name from `tabAsset Others` where serial_number = '{0}'""".format(self.name))
                        if not others:
                                self.create_asset_others()
		
	def create_asset_others(self):
                if not frappe.db.exists("Organization", self.owned_by):
			org = frappe.new_doc("Organization")
			org.organization = self.owned_by
			org.save()

		doc = frappe.new_doc("Asset Others")
                doc.asset_category = 'Machinery & Equipment(6 Years)'
                doc.asset_name = self.equipment_number
                doc.model = self.equipment_model
                doc.brand = self.equipment_type
                doc.serial_number = self.name
                doc.from_date = self.from_date
                doc.owned_by = self.owned_by
                doc.status = 'In-Use'
                doc.branch = self.branch
                #doc.issued_to = self.get("operators")[0].operator
                doc.issued_to = self.custodian
		doc.save()
                frappe.msgprint("Added In Others Asset List")

	def create_equipment_history(self, branch, on_date, ref_doc, purpose):
                from_date = on_date
                if purpose == "Cancel":
                        to_remove = []
                        for a in self.equipment_history:
                                if a.reference_document == ref_doc:
                                        to_remove.append(a)

                        [self.remove(d) for d in to_remove]
                        self.set_to_date()
                        return

                if not self.equipment_history:
                        self.append("equipment_history",{
                                                "branch": self.branch,
                                                "from_date": from_date,
                                                "reference_document": ref_doc
                        })
                else:
                        #doc = frappe.get_doc(self.doctype,self.name)
                        ln = len(self.equipment_history)-1	
                        if self.branch != self.equipment_history[ln].branch:
                                self.append("equipment_history",{
                                                "branch": self.branch,
                                                "from_date": from_date,
                                                "reference_document": ref_doc
                        })
                self.set_to_date()


	def set_to_date(self):
                if len(self.equipment_history) > 1:
                        for a in range(len(self.equipment_history)-1):
                                self.equipment_history[a].to_date = frappe.utils.data.add_days(getdate(self.equipment_history[a + 1].from_date), -1)
                else:
                        self.equipment_history[0].to_date = None

	def set_name(self):
		for a in self.operators:
			if a.employee_type == "Employee":
				a.operator_name = frappe.db.get_value("Employee", a.operator, "employee_name")
			if a.employee_type == "Muster Roll Employee":
				a.operator_name = frappe.db.get_value("Muster Roll Employee", a.operator, "person_name")

	def validate_asset(self):
		if self.asset_code:
			equipments = frappe.db.sql("select name from tabEquipment where asset_code = %s and name != %s", (self.asset_code, self.name), as_dict=True)
			if equipments:
				frappe.throw("The Asset is already linked to another equipment")
	
@frappe.whitelist()
def get_yards(equipment):
	t, m = frappe.db.get_value("Equipment", equipment, ['equipment_type', 'equipment_model'])
	data = frappe.db.sql("select lph, kph from `tabHire Charge Parameter` where equipment_type = %s and equipment_model = %s", (t, m), as_dict=True)
	if not data:
		frappe.throw("Setup yardstick for " + str(m))
	return data

@frappe.whitelist()
def get_equipment_types(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("select distinct a.equipment_type as equipment_type from `tabEquipment` a where a.branch = \'"+ str(filters.get("branch")) +"\'")

@frappe.whitelist()
def get_equipments(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("select a.equipment as name from `tabHiring Approval Details` a where docstatus = 1 and a.parent = \'"+ str(filters.get("ehf_name")) +"\'")

def sync_branch_asset():
	objs = frappe.db.sql("select e.name, a.branch from tabEquipment e, tabAsset a where e.asset_code = a.name and e.branch != a.branch", as_dict=True)
	for a in objs:
		frappe.db.sql("update tabEquipment set branch = %s where name = %s", (a.branch, a.name))





