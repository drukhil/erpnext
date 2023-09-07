# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate, money_in_words, getdate
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba
from erpnext.accounts.general_ledger import make_gl_entries
from frappe.utils.data import get_first_day, get_last_day, add_days
from erpnext.controllers.accounts_controller import AccountsController

class ProcessRentalBilling(AccountsController):
	def get_tenant_list(self, process_type=None):
		self.check_mandatory()
		rental_bill_date = self.fiscal_year + "-" + self.month + "-" + "01"
		month_start = get_first_day(rental_bill_date)
		month_end = get_last_day(rental_bill_date)
		condition = " and t1.building_category != 'Pilot Housing'"
		if self.dzongkhag:
			condition += " and t1.dzongkhag = '{dzongkhag}'".format(dzongkhag=self.dzongkhag)
		if self.ministry_agency:
			condition += " and t1.ministry_agency = '{ministry_agency}'".format(ministry_agency=self.ministry_agency)
		
		if process_type == "create":
			if self.tenant:
				condition += " and t1.name = '{tenant}'".format(tenant=self.tenant)
			tenant_list = frappe.db.sql("""
			       select t1.name
			       from `tabTenant Information` t1
			       where t1.docstatus = "1"
			       and (
					(t1.status="Allocated" and t1.allocated_date <= '{3}')
					or
					(t1.status="Surrendered" and t1.surrendered_date >= '{2}')
				   )
			       and t1.allocated_date <= '{3}'
				   {4}
			       and not exists(select 1
					      from `tabRental Bill` as t2
					      where t2.tenant = t1.name
					      and t2.docstatus != 2
					      and t2.fiscal_year = '{0}'
					      and t2.month = '{1}'
					      )
			       order by t1.ministry_agency, t1.department
			""".format(self.fiscal_year, self.month, month_start, month_end, condition), as_dict=True)
		elif process_type == "post_to_gl":
			if self.tenant:
				condition += " and t1.tenant = '{tenant}'".format(tenant=self.tenant)
			tenant_list = frappe.db.sql("""
								select t1.name 
								from `tabRental Bill` t1
								where t1.branch = '{branch}' 
								and t1.fiscal_year = '{fiscal_year}' 
								and t1.month = '{month}'
								and t1.docstatus = 1
								and t1.gl_entry = 0
								and t1.receivable_amount > 0
								{condition}
						""".format(branch=self.branch, fiscal_year=self.fiscal_year, month=self.month, condition=condition), as_dict=True)			
		else:
			if self.tenant:
				condition += " and t1.tenant = '{tenant}'".format(tenant=self.tenant)
			tenant_list = frappe.db.sql("""
                                select t1.name
                                from `tabRental Bill` as t1
                                where t1.fiscal_year = '{0}'
                                and t1.month = '{1}'
								and t1.branch = '{2}'
                                and t1.docstatus = 0
								{3}
                                order by t1.branch, t1.name
                        """.format(self.fiscal_year, self.month, self.branch, condition), as_dict=True)
		return tenant_list	

	def check_mandatory(self):
		for f in ['month', 'fiscal_year', 'dzongkhag']:
			if not self.get(f):
				frappe.throw(_("Please set {0}").format(f))

	
	def process_rental(self, process_type=None, name=None):
		self.check_permission('write')
		msg=""
		if name:
			try:
				if process_type == "create":
					bill_date = self.fiscal_year+"-"+self.month+"-"+"01"
					posting_date = get_last_day(bill_date) 
					if self.month == "01":
						prev_fiscal_year = int(self.fiscal_year) - 1
						prev_month = "12"
					else:
						prev_fiscal_year = self.fiscal_year
						if int(self.month) <= 10:	
							a = 0
							b = int(self.month) - 1
							prev_month = str(a) + str(b)
						else:
							prev_month = str(int(self.month) - 1)
					#customer_code = frappe.db.get_value("Customer", {"customer_id":name}, "customer_code")
					#bill_code = "NHDCL/" + customer_code + "/" + self.fiscal_year + self.month
					yearmonth = str(self.fiscal_year) + str(self.month)
					previous_bill_date = str(prev_fiscal_year)+"-"+str(prev_month)+"-"+"01"
					
					query = """
							select cid, tenant_name, customer_code, block_no, business_activity, flat_no, 
							ministry_agency, location, branch, department, dzongkhag, dungkhag, designation, 
							mobile_no, town_category, building_category, allocated_date, is_nhdcl_employee,
							(Case 
								WHEN building_category = 'Pilot Housing' Then original_monthly_instalment  
								Else rental_amount 
							End) as rental_amount
							from `tabTenant Information` t 
							inner join `tabTenant Rental Charges` r 
							on t.name = r.parent 
							where '{0}' between r.from_date and r.to_date
							and t.building_category != 'Pilot Housing'
							and (exists(select 1
									from `tabRental Bill` as t2
									where t2.tenant = t.name
									and t2.docstatus != 2 
									and t2.fiscal_year = '{2}'
									and t2.month = '{3}'
							) 
							or not exists(select 1
									from `tabRental Bill` as t3
									where t3.tenant = '{1}'
									and t3.docstatus != 2   
							)
							or '{4}' between t.m_start_date and t.m_end_date
							)
							and t.name = '{1}';
				
                            """.format(bill_date, name, prev_fiscal_year, prev_month, previous_bill_date)
					dtls = frappe.db.sql(query, as_dict=True)

					if dtls:
						for d in dtls:
							cost_center = frappe.db.get_value("Branch", d.branch, "cost_center") 
							company = frappe.db.get_value("Branch", d.branch, "company")
							rb = frappe.get_doc({
								"doctype": "Rental Bill",
								"tenant": str(name),
								"cid" : str(d.cid),
								"customer_code": str(d.customer_code),
								"posting_date": posting_date,
								"tenant_name": str(d.tenant_name),
								"block_no": d.block_no,
								"total_in_words": "",
								"fiscal_year": self.fiscal_year,
								"month": self.month,
								"flat_no": d.flat_no,
								"ministry_agency": d. ministry_agency,
								"location": d.location,
								"branch": d.branch,
								"department": d.department,
								"dzongkhag": d.dzongkhag,
								"dungkhag": d.dungkhag,
								"designation": d.designation,
								"mobile": d.mobile_no,
								"town_category": d.town_category,
								"building_category": d.building_category,
								"allocation_date": d.allocated_date,
								"yearmonth": yearmonth,
								"rent_amount": d.rental_amount,
								"receivable_amount": d.rental_amount,
								"cost_center": cost_center,
								"company": company,
								"is_nhdcl_employee": d.is_nhdcl_employee
							})
							rb.insert()
							rb_no = frappe.db.get_value("Rental Bill", {"tenant":name, "month":self.month, "fiscal_year": self.fiscal_year, "docstatus":0}, "name")
						msg = "Rental Bill Created Successfully for {0} amount Nu. {1}".format(d.tenant_name, d.rental_amount)
					else:
						msg = '<span style="color:red;"> FAILED. Previous month rentall bill might not have process or <br/> rental charges might be missing in tenant information</span>'
				elif process_type == "post_to_gl":
					bill_date = str(self.fiscal_year) + "-" + str(self.month) + "-" + "01"
					self.posting_date = get_last_day(bill_date)
					cost_center = frappe.db.get_value("Branch", self.branch, "cost_center")
					business_activity = frappe.db.get_single_value("Rental Setting", "business_activity")
					revenue_claim_account = frappe.db.get_single_value("Rental Account Setting", "revenue_claim_account")
					for a in frappe.db.sql("""
	                      	select
							  t.name as rental_bill, t.tenant, c.name as customer, t.receivable_amount, t.building_category
                              from `tabRental Bill` t left join `tabCustomer` c on t.customer_code = c.customer_code
                            where t.name = '{name}'
						""".format(name=name), as_dict=True):
						gl_entries = []
						pre_rent_account = frappe.db.get_single_value("Rental Account Setting", "pre_rent_account")
						pre_rent_amount = frappe.db.sql("""select (sum(credit) - sum(debit)) as pre_rent_amount
														from `tabGL Entry` 
														Where party_type='Customer' 
														and party = '{party}'
														and account = '{account}'
														""".format(party=a.customer, account=pre_rent_account))[0][0]
						pre_rent_adjustment_amount, balance_receivable_amount = 0,0
						if pre_rent_amount > 0:
							if a.receivable_amount <= pre_rent_amount:
								pre_rent_adjustment_amount = flt(a.receivable_amount)
							else:
								pre_rent_adjustment_amount = flt(pre_rent_amount)
								balance_receivable_amount = flt(a.receivable_amount) - flt(pre_rent_amount)

							gl_entries.append(
								self.get_gl_dict({
									"account": pre_rent_account,
									"debit": flt(pre_rent_adjustment_amount),
									"debit_in_account_currency": flt(pre_rent_adjustment_amount),
									"voucher_no": a.rental_bill,
									"voucher_type": "Rental Bill",
									"cost_center": cost_center,
									"party": a.customer,
									"party_type": "Customer",
									"company": self.company,
									"remarks": str(a.tenant) + " Monthly Rental Bill for Year " + str(self.fiscal_year) + " Month " + str(self.month),
									"business_activity": business_activity
								})
							)
						else:
							balance_receivable_amount = flt(a.receivable_amount)
						
						if balance_receivable_amount > 0:
							gl_entries.append(
								self.get_gl_dict({
									"account": revenue_claim_account,
									"debit": flt(balance_receivable_amount),
									"debit_in_account_currency": flt(balance_receivable_amount),
									"voucher_no": a.rental_bill,
									"voucher_type": "Rental Bill",
									"cost_center": cost_center,
									'party': a.customer,
									'party_type': 'Customer',
									"company": self.company,
									"remarks": str(a.tenant) + " Monthly Rental Bill for Year " + str(self.fiscal_year) + " Month " + str(self.month),
									"business_activity": business_activity
								})
							)
						credit_account = frappe.db.get_value("Rental Account Setting Item",{"building_category":a.building_category}, "account")
						gl_entries.append(
							self.get_gl_dict({
								"account": credit_account,
								"credit": flt(a.receivable_amount),
								"credit_in_account_currency": flt(a.receivable_amount),
								"voucher_no": a.rental_bill,
								"voucher_type": "Rental Bill",
								"cost_center": cost_center,
								"company": self.company,
								"remarks": str(a.tenant) + " Rental Bill for " + str(a.building_category) +" Year "+ str(self.fiscal_year) + " Month " +str(self.month),
								"business_activity": business_activity
								})
							)
						make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=False)
						
						doc = frappe.get_doc("Rental Bill", a.rental_bill)
						doc.db_set('gl_entry', 1)
						doc.db_set('adjusted_amount', flt(pre_rent_adjustment_amount))
						msg = "Rental Bill Successfully Posted to Accounts"
					format_string = 'href="#Form/Rental Bill/{0}"'.format(name)
					return '<tr><td><a {0}>{1}</a></td><td><a {0}>{2}</a></td></tr>'.format(format_string, name, msg)
				else:
					if process_type == "remove":
						rental_bill_status = frappe.db.get_value("Rental Bill", name, "docstatus")
						if rental_bill_status != 1:
							rb_list = frappe.db.sql("delete from `tabRental Bill` where name='{0}'".format(name))
							frappe.db.commit()
							msg = "Rental Bill Removed Successfully"
						else:
							msg = "Rental Bill not allowed to be removed as it already submitted"
					rb = frappe.get_doc("Rental Bill", name)
					rb.submit()
					msg = "Rental Bill Submitted Successfully"

				format_string = 'href="#Form/Rental Bill/{0}"'.format(name)
				return '<tr><td><a {0}>{1}</a></td><td><a {0}>{2}</a></td></tr>'.format(format_string, name, msg)
			except Exception, e:
				return '<div style="color:red;"> Error: Tenant CID :{1} - {0}</div>'.format(str(e), name)
