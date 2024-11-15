# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

'''
------------------------------------------------------------------------------------------------------------------------------------------
Version          Author         Ticket#           CreatedOn          ModifiedOn          Remarks
------------ --------------- --------------- ------------------ -------------------  -----------------------------------------------------
3.0               SHIV		                   28/01/2019                          Original Version
------------------------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_link_to_form
#from erpnext.hr.doctype.approver_settings.approver_settings import get_final_approver
from erpnext.hr.hr_custom_functions import get_officiating_employee


def validate_workflow_states(doc):
	approver_field = {
			"Travel Authorization": ["supervisor",""],
                        "Travel Claim": ["supervisor",""],
			"Leave Encashment": ["approver", "approver_name"],
                        "Employee Separation": ["approver", "approver_name"],
			"Salary Advance": ["advance_approver","advance_approver_name","advance_approver_designation"],
			"Leave Application": ["leave_approver","leave_approver_name"],
			"Employee Benefits": ["benefit_approver","benefit_approver_name"],
                        "Request EL Allocation": ["approver", "approver_name"],
			"Overtime Authorization": ["approver", "approver_name"],
			"Overtime Claim": ["approver", "approver_name"],
	}
	
	if not approver_field.has_key(doc.doctype) or not frappe.db.exists("Workflow", {"document_type": doc.doctype, "is_active": 1}):
		return
	document_approver = approver_field[doc.doctype]
	employee          = frappe.db.get_value("Employee", doc.employee, ["user_id","employee_name","designation","name"])
	reports_to        = frappe.db.get_value("Employee", frappe.db.get_value("Employee", doc.employee, "reports_to"), ["user_id","employee_name","designation","name"])
	if not reports_to:
		frappe.throw("Set Up Reports to in Employee Master")

	'''final_approver    = frappe.db.get_value("Employee", {"user_id": get_final_approver(doc.branch)}, ["user_id","employee_name","designation","name"])
	workflow_state    = doc.get("workflow_state").lower()'''
	

#LA, TA, OT 
def verify_workflow(doc):
        reports_to  = frappe.db.get_value("Employee", frappe.db.get_value("Employee", doc.employee, "reports_to"), ["user_id","employee_name","designation","name"])
        if not reports_to:
                frappe.throw("Set Up Reports to in Employee Master")

        final_approver  = frappe.db.get_value("Employee", frappe.db.get_value("Employee", doc.employee, "second_approver"), ["user_id","employee_name","designation","name"])
        if not final_approver:
                frappe.throw("Set Up Reports to in Employee Master")

	
        verifier_officiating = get_officiating_employee(reports_to[3]) 
        approver_officiating = get_officiating_employee(final_approver[3])
	
	
        verifier = frappe.get_doc("Employee", verifier_officiating[0].officiate).user_id if verifier_officiating else reports_to[0]
        approver = frappe.get_doc("Employee", approver_officiating[0].officiate).user_id if approver_officiating else final_approver[0]	
		
        hr_approver = frappe.db.get_value("Employee", frappe.db.get_single_value("HR Settings", "hr_approver"), "user_id")
        if not hr_approver:
                frappe.throw(_("Missing HR Approver user set from HR Setting."))
        
        if doc.workflow_state == "Waiting Approval":
                if frappe.session.user not in (doc.owner, hr_approver, "Administrator"):
                        doc.workflow_state = "Draft"
                        frappe.throw("Only Mr/Mrs. <b> '{0}' </b>  can Apply/Reapply this Document".format(frappe.get_doc("User", frappe.db.get_value("Employee", doc.employee, "user_id")).full_name))
                doc.workflow_state = "Waiting Approval"
                doc.docstatus = 0

        if doc.workflow_state == "Verified":
                if frappe.session.user not in (verifier, hr_approver, "Administrator"):
                        doc.workflow_state = "Waiting Approval"
                        frappe.throw("Only Mr/Mrs. <b> {0} </b> can verify this Document".format(frappe.get_doc("User", verifier).full_name))
                doc.workflow_state == "Verified"
                doc.docstatus = 0
                doc.verifier = frappe.session.user

        if doc.workflow_state == "Approved":
                if frappe.session.user not in (approver, hr_approver, "Administrator"):
                        doc.workflow_state = "Verified"
                        doc.docstatus = 0
                        frappe.throw("Only Mr/Mrs. <b> {0} </b> can approve this Documentmt".format(frappe.get_doc("User", approver).full_name))
                if doc.get_db_value("workflow_state") != "Verified":
                        doc.workflow_state = "Verified"
                        doc.docstatus = 0
                        frappe.throw("Only Verified Document Can be approved")
                doc.workflow_state = "Approved"
                doc.docstatus = 1
                doc.w_approver = frappe.session.user

        if doc.workflow_state in ("Rejected", "Cancelled"):
                if doc.get_db_value("workflow_state") == 'Waiting Approval':
                        if frappe.session.user not in (verifier, hr_approver, "Administrator"):
                                doc.workflow_state = 'Waiting Approval'
                                frappe.throw("Only Mr/Mrs. <b> {0} </b> can reject this document".format(frappe.get_doc("User", verifier).full_name))

                elif doc.get_db_value("workflow_state") in ('Verified', 'Approved'):
                        if frappe.session.user not in (approver, hr_approver, "Administrator"):
                                doc.workflow_state = doc.get_db_value("workflow_state")
                                frappe.throw("Only Mr/Mrs. <b> {0} </b> can reject/cancel this Document".format(frappe.get_doc("User", approver).full_name))
                doc.rejector = frappe.session.user

#Travel Claim
def verify_workflow_tc(doc):
	reports_to  = frappe.db.get_value("Employee", frappe.db.get_value("Employee", doc.employee, "reports_to"), ["user_id","employee_name","designation","name"])
        if not reports_to:
                frappe.throw("Set Up Reports to in Employee Master")

        final_approver  = frappe.db.get_value("Employee", frappe.db.get_value("Employee", doc.employee, "second_approver"), ["user_id","employee_name","designation","name"])
        if not final_approver:
                frappe.throw("Set Up Reports to in Employee Master")


	hr_user = frappe.db.get_single_value("HR Settings", "hr_approver")
        if not hr_user:
                frappe.throw("Set Up HR Approver in HR Settings")
        hr_approver = frappe.db.get_value("Employee", hr_user, ["user_id","employee_name","designation","name"])


        verifier_officiating = get_officiating_employee(reports_to[3])
        approver_officiating = get_officiating_employee(final_approver[3])
	hr_officiating = get_officiating_employee(hr_approver[3])

	verifier = frappe.get_doc("Employee", verifier_officiating[0].officiate).user_id if verifier_officiating else reports_to[0]
        approver = frappe.get_doc("Employee", approver_officiating[0].officiate).user_id if approver_officiating else final_approver[0]	
       	approver_hr = frappe.get_doc("Employee", hr_officiating[0].officiate).user_id if hr_officiating else  hr_approver[0]
 

        if doc.workflow_state == "Waiting Approval":
                if doc.owner != frappe.session.user:
                        doc.workflow_state = "Draft"
                        frappe.throw("Only Mr/Mrs. <b> {0} </b>  can Apply/Reapply this Document".format(frappe.get_doc("User", doc.owner).full_name))
                doc.workflow_state = "Waiting Approval"
                doc.docstatus = 0

        if doc.workflow_state == "Verified By Supervisor":
		if frappe.session.user not in (verifier, hr_approver[3]):
                        doc.workflow_state = "Waiting Approval"
                        frappe.throw("Only Mr/Mrs. <b> {0} </b> can verify this Document".format(frappe.get_doc("User", verifier).full_name))
                doc.workflow_state = "Verified By Supervisor"
                doc.docstatus = 0
		doc.verifier = verifier


	if doc.workflow_state == "Waiting HR Verification":
                # if approver != frappe.session.user:
                #         doc.workflow_state = "Verified By Supervisor"
                #         frappe.throw("Only Mr/Mrs.. <b> {0} </b> can Approve this Document".format(frappe.get_doc("User", approver).full_name))
                doc.workflow_state = "Waiting HR Verification"
                doc.docstatus = 0
                doc.approver = approver

 
	if doc.workflow_state == "Approved":
		if frappe.session.user not in ('sonamyangchen@gyalsunginfra.bt', 'phuntsho@gyalsunginfra.bt'):
			doc.workflow_state = "Waiting HR Verification"
			frappe.throw("Only Mr/Mrs. <b> Sonam Yangchen/Phuntsho  </b> can approve this Document")
		doc.workflow_state = "Approved"
		doc.docstatus = 1
		doc.hr_approver = approver_hr
	
	if doc.workflow_state in ("Rejected", "Cancelled"):
                if doc.get_db_value("workflow_state") == 'Waiting Approval':
			if frappe.session.user not in (verifier, hr_approver[3]):
                                doc.workflow_state = 'Waiting Approval'
                                frappe.throw("Only Mr/Mrs. <b> {0} </b> can Reject this Document".format(frappe.get_doc("User", verifier).full_name))

		elif doc.get_db_value("workflow_state") in ('Verified', 'Approved'):
			if frappe.session.user not in (approver, hr_approver[3]):
				doc.workflow_state = doc.get_db_value("workflow_state")
			frappe.throw("Only <b> Mr/Mrs. {0} </b> can reject/cancel this Document".format(frappe.get_doc("User", approver).full_name))
		doc.rejector = frappe.session.user

@frappe.whitelist()
#def approver_list(doctype, txt, searchfield, start, page_len, filters):	
def approver_list(doc, employee, action):
        reports_to  = frappe.db.get_value("Employee", frappe.db.get_value("Employee", employee, "reports_to"), ["user_id","employee_name","designation","name"])
        if not reports_to:
                frappe.throw("Set Up Reports to in Employee Master")

        final_approver  = frappe.db.get_value("Employee", frappe.db.get_value("Employee", employee, "second_approver"), ["user_id","employee_name","designation","name"])
        if not final_approver:
                frappe.throw("Set Up Reports to in Employee Master")

        hr_user = frappe.db.get_single_value("HR Settings", "hr_approver")
        if not hr_user:
                frappe.throw("Set Up HR Approver in HR Settings")
        hr_approver = frappe.db.get_value("Employee", hr_user, ["user_id","employee_name","designation","name"])

        verifier_officiating = get_officiating_employee(reports_to[3])
        approver_officiating = get_officiating_employee(final_approver[3])
        hr_officiating = get_officiating_employee(hr_approver[3])

	verifier = frappe.get_doc("Employee", verifier_officiating[0].officiate).user_id if verifier_officiating else reports_to[0]
        approver = frappe.get_doc("Employee", approver_officiating[0].officiate).user_id if approver_officiating else final_approver[0]
        approver_hr = frappe.get_doc("Employee", hr_officiating[0].officiate).user_id if hr_officiating else  hr_approver[3]

	#approver_list.setdefault('verifier', verifier)
	#approver_list.setdefault('approver', approver)
	#approver_list.setdefault('approver_hr', approver_hr)	
	
	#set Verifier
@frappe.whitelist()
def validate_separation_workflow(doc):
        user = frappe.session.user
	user_roles = frappe.get_roles(user)
        reports_to  = frappe.db.get_value("Employee", frappe.db.get_value("Employee", doc.employee, "reports_to"), ["user_id","employee_name","designation","name"])
        if not reports_to:
                frappe.throw("Set Up Reports to in Employee Master")


        verifier_officiating = get_officiating_employee(reports_to[3])
        verifier = frappe.get_doc("Employee", verifier_officiating[0].officiate).user_id if verifier_officiating else reports_to[0]
        
        subject = "Employee Separation(ERP)"
	if doc.workflow_state == "Draft":
                if doc.owner != frappe.session.user:
                        frappe.throw("Only Mr/Mrs. <b> '{0}' </b>  can Save this Document".format(frappe.get_doc("User", doc.owner).full_name))
	
	if doc.workflow_state == "Waiting Approval":
                # if doc.owner != frappe.session.user:
                #         doc.workflow_state = "Draft"
                #         frappe.throw("Only Mr/Mrs. <b> '{0}' </b>  can Apply/Reapply this Document".format(frappe.get_doc("User", doc.owner).full_name))
                doc.workflow_state = "Waiting Approval"
                doc.docstatus = 0
                doc.approver = reports_to[0]
                doc.approver_name = reports_to[1]
                message = """Dear Sir/Madam, <br>  {0} has requested you to Approve the Employee Separation <b> {1}. Check ERP System for More Info. </b> <br> Thank You""".format(frappe.get_doc("User", doc.owner).full_name, str(get_link_to_form("Employee Separation", doc.name)))
                try:
                        frappe.sendmail(recipients=verifier, sender=None, subject=subject, message=message)
			frappe.sendmail(recipients= doc.owner, sender = None, subject = subject, message = "Employee Separation {0} verified".format(str(get_link_to_form("Employee Separation", doc.name))))
                except:
                        pass

	if doc.workflow_state == "Approved":
                
                if verifier != frappe.session.user:
                        doc.workflow_state = "Waiting Approval"
                        doc.docstatus = 0
                        frappe.throw("Only Mr/Mrs. <b> {0} </b> can approve this Documentmt".format(frappe.get_doc("User", verifier).full_name))
                doc.workflow_state == "Approved"
                doc.docstatus = 1
                doc.approver = frappe.session.user
		message = """Dear Sir/Madam, <br>  {0} has requested you to Approve the Employee Separation <b> {1}. Check ERP System for More Info. </b> <br> Thank You""".format(frappe.get_doc("User", doc.owner).full_name, str(get_link_to_form("Employee Separation", doc.name)))
                try:
		        frappe.sendmail(recipients= doc.owner, sender = None, subject = subject, message = "Employee Separation {0} verified".format(str(get_link_to_form("Employee Separation", doc.name))))
                except:
                        pass
        if doc.workflow_state == "Rejected":
                message = """Dear Sir/Madam, <br> {0} has rejected the Employee Separation <b> {1}. Check ERP System for More Info. </b> <br> Thank You""".format(frappe.get_doc("User", doc.owner).full_name, str(get_link_to_form("Employee Separation", doc.name)))
                if verifier != frappe.session.user:
                        doc.workflow_state = "Waiting Approval"
                        doc.docstatus = 0
                        frappe.throw("Only Mr/Mrs. <b> {0} </b> can reject this Documentmt".format(frappe.get_doc("User", verifier).full_name))
                try:
                        frappe.sendmail(recipients=doc.owner, sender=None, subject=subject, message=message)
                except:
                        pass
        if doc.workflow_state == "Cancelled":
                message = """Dear Sir/Madam, <br> {0} has Cancelled the Employee Separation <b> {1}. Check ERP System for More Info. </b> <br> Thank You""".format(frappe.get_doc("User", doc.owner).full_name, str(get_link_to_form("Employee Separation", doc.name)))
                if "HR Manager" not in user_roles:
                        doc.workflow_state = 'Waiting Approval'
                        frappe.throw("Only HR Manager role can reject this document")

                try:
                        frappe.sendmail(recipients=doc.owner, sender=None, subject=subject, message=message)
                except:
                        pass


@frappe.whitelist()
def verify_mr_workflow(doc):
        user = frappe.session.user
	user_roles = frappe.get_roles(user)

        employee = frappe.db.get_value("Employee", {'user_id': doc.owner}, 'name')
        reports_to  = frappe.db.get_value("Employee", frappe.db.get_value("Employee", employee, "reports_to"), ["user_id","employee_name","designation","name"])
        if not reports_to:
                frappe.throw("Set Up Reports to in Employee Master")

        final_approver  = frappe.db.get_value("Employee", frappe.db.get_value("Employee", employee, "second_approver"), ["user_id","employee_name","designation","name"])
        if not final_approver:
                frappe.throw("Set Up Reports to in Employee Master")


        verifier_officiating = get_officiating_employee(reports_to[3])
        approver_officiating = get_officiating_employee(final_approver[3])

	verifier = frappe.get_doc("Employee", verifier_officiating[0].officiate).user_id if verifier_officiating else reports_to[0]
        approver = frappe.get_doc("Employee", approver_officiating[0].officiate).user_id if approver_officiating else final_approver[0]
	
	#Email
	subject = "Material Request(ERP)"
	if doc.workflow_state == "Draft":
                if doc.owner != frappe.session.user:
                        frappe.throw("Only Mr/Mrs. <b> '{0}' </b>  can Save this Document".format(frappe.get_doc("User", doc.owner).full_name))
	
	if doc.workflow_state == "Waiting Approval":
                # if doc.owner != frappe.session.user:
                #         doc.workflow_state = "Draft"
                #         frappe.throw("Only Mr/Mrs. <b> '{0}' </b>  can Apply/Reapply this Document".format(frappe.get_doc("User", doc.owner).full_name))
                if doc.title1 =="Material Request":
                        doc.workflow_state = "Waiting Approval"
                else:
                        doc.workflow_state = "Waiting For Verification"
                doc.docstatus = 0
		
        if doc.workflow_state =="Verified":
                if verifier != frappe.session.user:
                        doc.workflow_state = "Verified By Supervisor"
                        doc.docstatus = 0
                        frappe.throw("Only Mr/Mrs. <b> {0} </b> can verify this Documentmt".format(frappe.get_doc("User", verifier).full_name))
                doc.workflow_state = "Verified"
                doc.docstatus = 0
                doc.verifier = frappe.session.user
                message = """Dear Sir/Madam, <br>  {0} has requested you to Verified the Material Request <b> {1}. Check ERP System for More Info. </b> <br> Thank You""".format(frappe.get_doc("User", doc.owner).full_name, str(get_link_to_form("Material Request", doc.name)))
                try:
                        frappe.sendmail(recipients=approver, sender=None, subject=subject, message=message)
			frappe.sendmail(recipients= doc.owner, sender = None, subject = subject, message = "Material Request {0} verified".format(str(get_link_to_form("Material Request", doc.name))))
                except:
                        pass

        if doc.workflow_state == "Verified By Supervisor":
                if "MR Verifier" not in user_roles:
                        doc.workflow_state = "Waiting Approval"
                        frappe.throw("Only MR Verifier role can verify this Document")
                doc.workflow_state == "Verified By Supervisor"
                doc.docstatus = 0
                doc.verifier = frappe.session.user
		message = """Dear Sir/Madam, <br>  {0} has requested you to Verified the Material Request <b> {1}. Check ERP System for More Info. </b> <br> Thank You""".format(frappe.get_doc("User", doc.owner).full_name, str(get_link_to_form("Material Request", doc.name)))
                try:
                        frappe.sendmail(recipients=approver, sender=None, subject=subject, message=message)
			frappe.sendmail(recipients= doc.owner, sender = None, subject = subject, message = "Material Request {0} verified".format(str(get_link_to_form("Material Request", doc.name))))
                except:
                        pass

	if doc.workflow_state == "Approved":
                if doc.title1 =="Material Request":
                        if "MR Approver" not in user_roles:
                                doc.workflow_state = "Waiting Approval"
                                frappe.throw("Only MR Approver role can Approved this Document")
                else:
                        if approver != frappe.session.user:
                                doc.workflow_state = "Verified"
                                doc.docstatus = 0
                                frappe.throw("Only Mr/Mrs. <b> {0} </b> can approve this Documentmt".format(frappe.get_doc("User", approver).full_name))
                        if doc.get_db_value("workflow_state") != "Verified":
                                doc.docstatus = 0
                                frappe.throw("Only Verified Document Can be approved")
                doc.workflow_state == "Approved"
                doc.docstatus = 1
                doc.w_approver = frappe.session.user
		message = """Dear Sir/Madam, <br>  {0} has requested you to Approve the Material Request <b> {1}. Check ERP System for More Info. </b> <br> Thank You""".format(frappe.get_doc("User", doc.owner).full_name, str(get_link_to_form("Material Request", doc.name)))
                try:
                        frappe.sendmail(recipients=approver, sender=None, subject=subject, message=message)
			frappe.sendmail(recipients= doc.owner, sender = None, subject = subject, message = "Material Request {0} verified".format(str(get_link_to_form("Material Request", doc.name))))
                except:
                        pass

        if doc.workflow_state in ("Rejected", "Cancelled"):
                if doc.get_db_value("workflow_state") == 'Waiting Approval':
                        if "MR Verifier" not in user_roles:
                                doc.workflow_state = 'Waiting Approval'
                                frappe.throw("Only MR Verifier role can reject this document")
                
                elif doc.get_db_value("workflow_state") == 'Waiting For Verification':
                        if verifier != frappe.session.user:
                                frappe.throw("Only Mr/Mrs. <b> {0} </b> can reject/cancel this Document".format(frappe.get_doc("User", verifier).full_name))

                elif doc.get_db_value("workflow_state") in ('Verified By Supervisor', 'Approved'):
                        if doc.title1 =="Material Request":
                                if "MR Approver" not in user_roles:
                                        doc.workflow_state = 'Approved'
                                        frappe.throw("Only MR Approver role can reject this document")
                        else:
                                if approver != frappe.session.user:
                                        doc.workflow_state = doc.get_db_value("workflow_state")
                                        frappe.throw("Only Mr/Mrs. <b> {0} </b> can reject/cancel this Document".format(frappe.get_doc("User", approver).full_name))
                doc.rejector = frappe.session.user
		message = """Dear {0},  Your Material Request {1} is <b> {2} </b>. Check ERP System for More Info. <br> Thank You""".format(frappe.get_doc("User", doc.owner).full_name, str(get_link_to_form("Material Request", doc.name)), doc.workflow_state)
                try:
                        frappe.sendmail(recipients=doc.owner, sender=None, subject=subject, message=message)
                except:
                        pass

#accounts 
def set_user_imprest(doc):
        #emp = frappe.get_doc("Employee", {'user_id': frappe.session.user}).name
        #officiating = get_officiating_employee(emp)
        #usr = officiating if officiating else frappe.session.user
        if not frappe.db.exists("Workflow", {"document_type": doc.doctype, "is_active": 1}):
                return
        usr = frappe.session.user
        if doc.workflow_state == "Waiting Approval":
                doc.applied_by = usr
                doc.workflow_state = "Waiting Approval"
                doc.docstatus = 0


	if doc.workflow_state == "Waiting Recoupment":
                doc.approved_by = usr
                doc.workflow_state = "Waiting Recoupment"
                doc.docstatus = 0

        if doc.workflow_state == "Recouped":
                doc.verified_by = usr
                doc.workflow_state == "Recouped"
                doc.docstatus = 1


#accounts 
def set_user(doc):
        #emp = frappe.get_doc("Employee", {'user_id': frappe.session.user}).name
        #officiating = get_officiating_employee(emp)
        #usr = officiating if officiating else frappe.session.user
        if not frappe.db.exists("Workflow", {"document_type": doc.doctype, "is_active": 1}):

                return
        usr = frappe.session.user
        if doc.workflow_state == "Waiting Approval":
                doc.applied_by = usr
                doc.workflow_state = "Waiting Approval"
                doc.docstatus = 0

        if doc.workflow_state == "Verified":
                doc.verified_by = usr
                doc.workflow_state == "Verified"
                doc.docstatus = 0

        if doc.workflow_state == "Approved":
                doc.approved_by = usr
                doc.workflow_state = "Approved"
                doc.docstatus = 1	
