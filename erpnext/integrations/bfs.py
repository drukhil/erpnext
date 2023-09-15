from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, get_bench_path, get_datetime
import sys
import time
import json
import urllib
import urlparse
import requests
import os.path
from datetime import datetime
from base64 import (
    b64encode,
    b64decode,
)
from Crypto.Hash import SHA256, SHA
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA

class BFSSecure:
	def __init__(self):
		self.customer_order = None
		self.op		  = None
		self.order_no	  = None
		self.transaction_id 	  = None
		self.transaction_time 	  = None
		self.transaction_time_fmt = None
		self.bfs_settings = frappe.get_doc('BFS Settings')
		self.benfId 	  = self.bfs_settings.mobile_beneficiary_id
		self.url 	  = self.bfs_settings.mobile_api_url
		self.private_key  = self.bfs_settings.mobile_private_key_path
		self.mobile_rc	  = {i.response_code:i.response_desc for i in self.bfs_settings.get('mobile_rc')}
		self.bank_code	  = None
		self.bank_account = None
		self.amount	  = 0
		self.otp	  = None
	
	def create_online_payment(self, customer_order, bank_code, bank_account, amount):
		self.customer_order = customer_order
		self.bank_code	 = bank_code
		self.bank_account= bank_account
		self.amount	 = flt(amount)

		if flt(self.amount) < 0:
			frappe.throw(_("Amount cannot be a negative value"))
		elif not frappe.db.exists('Customer Order', self.customer_order):
			frappe.throw(_("Customer Order {0} not found").format(self.customer_order))

		co = frappe.get_doc("Customer Order", customer_order)
		if co.product_category=="Timber" and co.product_group=="Timber Prime Products" and co.total_payable_amount==co.total_balance_amount:
				self.amount = flt(co.total_balance_amount * 0.2, 2) # Advance of 20% Payment for Timber Prime Product
		else:
			self.amount = flt(co.total_balance_amount)
		co.save(ignore_permissions=True)

		transaction_time = get_datetime().strftime("%Y%m%d%H%M%S")
		if flt(self.amount) > 0:
			op = frappe.new_doc('Online Payment')
			op.update({
				'user': co.user,
				'customer_order': self.customer_order,
				'bank_code': self.bank_code,
				'bank_account': self.bank_account,
				'amount': flt(self.amount,2),
				'transaction_time': transaction_time
			}).save(ignore_permissions=True)
			self.op 	= op
			self.order_no	= op.name
			self.transaction_time = transaction_time
			frappe.db.commit()

	def get_online_payment(self, customer_order):
		self.customer_order = customer_order
		op = frappe.db.sql("""
			select name, transaction_id, transaction_time,
				bank_code, bank_account, amount
			from `tabOnline Payment`
			where customer_order = "{0}"
			order by creation desc
			limit 1
		""".format(self.customer_order),as_dict=True)

		if op:
			self.order_no	      = op[0].name
			self.transaction_id   = op[0].transaction_id
			self.transaction_time = get_datetime(op[0].transaction_time).strftime("%Y%m%d%H%M%S")
			self.transaction_time_fmt = op[0].transaction_time
			self.bank_code	      = op[0].bank_code
			self.bank_account     = op[0].bank_account 
			self.amount	      = flt(op[0].amount,2)
			self.op = frappe.get_doc('Online Payment', op[0].name)
		else:
			frappe.throw(_("Invalid order number"))

	def update_online_payment(self, message):
		self.op.response  = message.get('response')
		self.op.status 	  = message.get('status')
		self.op.error_msg = message.get('error_msg')
		self.op.transaction_id = self.transaction_id
		self.op.save(ignore_permissions=True)
		frappe.db.commit()

	def auth_request(self, customer_order, bank_code, bank_account, amount):
		''' Authorization Request '''
		print
		print '****************************'
		print '*            AR            *'
		print '****************************'
		self.create_online_payment(customer_order, bank_code, bank_account, amount)

		payload      = self.get_payload('AR')
		res 	     = frappe._dict()
		out 	     = frappe._dict()	
		response     = None
		error_msg    = None
		status	     = None

		print 'PAYLOAD'
		print payload

		start_time   = time.time()
		request      =  self.post_request(payload, timeout=10)
		elapsed_time = time.time() - start_time
		print
		print 'Elapsed time to BFS: {0}'.format(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
		if request.get('error'):
			response  = None
			error_msg = "Authorization Request Failed: {0}".format(request.get('error'))
			status    = 'Failed'
		else:
			print '==========> AR RESPONSE <=========='
			print request.res.text
			response = request.res.text
			res = urlparse.parse_qs(request.res.text)
			print '******* BEGIN, urlparse.parse_qs(request.res.text) ********'
			print res
			print '******* END, urlparse.parse_qs(request.res.text) ********'
			if res.get('bfs_msgType') and res.get('bfs_msgType')[0] == 'RC':
				if res.get('bfs_responseCode') and res.get('bfs_responseCode')[0] == '00':
					error_msg = None
					status = 'Pending'
					self.transaction_id = res.get('bfs_bfsTxnId')[0]
				else:
					error_msg = res.get('bfs_responseDesc')[0]
					status = 'Failed'
			else:
				error_msg = 'Authorization Request Failed: RC not received'
				status	  = 'Failed'
		out = frappe._dict({'response': response, 
			'error_msg': error_msg, 
			'status': status}) 
		self.update_online_payment(out)
		return out

	def auth_status(self, customer_order):
		''' Authorization Status '''
		self.get_online_payment(customer_order)
		payload      = self.get_payload('AS')
		res 	     = frappe._dict()
		out 	     = frappe._dict()	
		response     = None
		error_msg    = None
		status	     = None

		print 'PAYLOAD'
		print payload

		start_time = time.time()
		request =  self.post_request(payload, timeout=10)
		elapsed_time = time.time() - start_time
		print
		print 'Elapsed time to BFS: {0}'.format(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
		print request

	def account_inquiry(self):
		''' Account Inquiry '''
		print
		print '****************************'
		print '*            AE            *'
		print '****************************'
		payload      = self.get_payload('AE')
		res 	     = frappe._dict()
		out 	     = frappe._dict()	
		response     = None
		error_msg    = None
		status	     = None

		print 'PAYLOAD'
		print payload

		start_time = time.time()
		request =  self.post_request(payload, timeout=20)
		elapsed_time = time.time() - start_time
		print
		print 'Elapsed time to BFS: {0}'.format(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
		if request.get('error'):
			response  = None
			error_msg = "Account Inquiry Failed: {0}".format(request.get('error'))
			status    = 'Failed'
		else:
			print '==========> AE RESPONSE <=========='
			print request.res.text
			response = request.res.text
			res 	 = urlparse.parse_qs(request.res.text)
			if res.get('bfs_msgType') and res.get('bfs_msgType')[0] == 'EC':
				if res.get('bfs_responseCode') and res.get('bfs_responseCode')[0] == '00':
					error_msg = None
					status = 'Pending'
				else:
					error_msg = res.get('bfs_responseDesc')[0]
					status = 'Failed'
			else:
				error_msg = 'Account Inquiry Failed: EC not received'
				status	  = 'Failed'
		out = frappe._dict({'response': response, 
			'error_msg': error_msg, 
			'status': status}) 
		self.update_online_payment(out)
		return out

	def debit_request(self, customer_order, otp):
		''' Debit Request '''
		print
		print '****************************'
		print '*            DR            *'
		print '****************************'
		self.otp     = otp
		self.get_online_payment(customer_order)

		payload      = self.get_payload('DR')
		res 	     = frappe._dict()
		out 	     = frappe._dict()	
		response     = None
		error_msg    = None
		status	     = None

		print 'PAYLOAD'
		print payload

		start_time = time.time()
		request =  self.post_request(payload, timeout=45)
		elapsed_time = time.time() - start_time
		print
		print 'Elapsed time to BFS: {0}'.format(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
		if request.get('error'):
			response  = None
			error_msg = "Debit Request Failed: {0}".format(request.get('error'))
			status    = 'Failed'
		else:
			print '==========> AC RESPONSE <=========='
			print request.res.text
			response = request.res.text
			res 	 = urlparse.parse_qs(request.res.text)
			if res.get('bfs_msgType') and res.get('bfs_msgType')[0] == 'AC':
				if res.get('bfs_debitAuthCode') and res.get('bfs_debitAuthCode')[0] == '00':
					error_msg = None
					status = 'Successful'
				else:
					status = 'Failed'
					if res.get('bfs_debitAuthCode') and self.mobile_rc.get(res.get('bfs_debitAuthCode')):
						error_msg = self.mobile_rc.get(res.get('bfs_debitAuthCode'))
					else:
						if res.get('bfs_debitAuthCode'):
							error_msg = 'DR Error: Unknown AC response code {0}'.format(res.get('bfs_debitAuthCode'))
						else:
							error_msg = 'DR Error: Unknown AC response code'
			else:
				error_msg = 'Debit Request Failed: AC not received'
				status	  = 'Failed'
		out = frappe._dict({'response': response, 
			'error_msg': error_msg, 
			'status': status}) 
		self.update_online_payment(out)
		return out

	def get_payload(self, req_type):
		''' generate url based on request type '''
		if req_type in ('AR', 'AS'):
			params = [
				{'key': 'msgType', 'value': req_type},
				{'key': 'benfTxnTime', 'value': self.transaction_time},
				{'key': 'orderNo', 'value': self.order_no},
				{'key': 'benfId', 'value': self.benfId},
				{'key': 'benfBankCode', 'value': '01'},
				{'key': 'txnCurrency', 'value': 'BTN'},
				{'key': 'txnAmount', 'value': self.amount},
				{'key': 'remitterEmail', 'value': 'sivasankar.k2003@gmail.com'},
				{'key': 'paymentDesc', 'value': self.customer_order},
				{'key': 'version', 'value': 1.0}
			]
		elif req_type == 'AE':
			params = [
				{'key': 'msgType', 'value': req_type},
				{'key': 'bfsTxnId', 'value': self.transaction_id},
				{'key': 'benfId', 'value': self.benfId},
				{'key': 'remitterBankId', 'value': self.bank_code},
				{'key': 'remitterAccNo', 'value': self.bank_account},
			]
		elif req_type == 'DR':
			params = [
				{'key': 'msgType', 'value': req_type},
				{'key': 'bfsTxnId', 'value': self.transaction_id},
				{'key': 'benfId', 'value': self.benfId},
				{'key': 'remitterOtp', 'value': self.otp},
			]
		params_sorted = sorted(params, key=lambda k: k['key']) 
		keys 	 = "|".join(['bfs_'+str(i['key']) for i in params_sorted])
		values 	 = "|".join([str(i['value']) for i in params_sorted])
		final 	 = {'bfs_'+str(i['key']):i['value'] for i in params_sorted}

		# get checksum
		checksum = self.get_checksum(values)
		final.update({'bfs_checkSum':checksum})
		return final

	def post_request(self, payload, timeout):
		''' make post request '''
		print
		print '==========> POST REQUEST <=========='
		res 	= None
		out 	= frappe._dict()
		headers = {'Content-type': 'application/x-www-form-urlencoded'}

		''' TRY WITHOUT SESSION
		with requests.Session() as s:
			try:
                                res = s.post(self.url, headers=headers, data=payload, timeout=timeout)
				print 'RES'
				print res.text
			except requests.exceptions.Timeout as e:
				print 'EXCEPTION requests.exceptions.Timeout'
				print str(e)
			except requests.exceptions.RequestException as e:
				out.update({'error': e})
				print 'EXCEPTION requests.exceptions.RequestException'
				print str(e)
				#sys.exit(1)
		'''
		try:
			res = requests.post(self.url, headers=headers, data=payload, timeout=timeout, verify=True)
			print 'RES'
			print res.text
		except requests.exceptions.Timeout as e:
			out.update({'error': str(e)})
			print 'EXCEPTION requests.exceptions.Timeout'
			print str(e)
		except requests.exceptions.RequestException as e:
			out.update({'error': str(e)})
			print 'EXCEPTION requests.exceptions.RequestException'
			print str(e)
			#sys.exit(1)

		if res:
			if res.status_code == 200:
				out.update({'res': res})
			else:
				out.update({'error': res.text})
		else:
			if not out.get('error'):
				out.update({'error': 'Request failed!!!'})
		return out

	def get_checksum(self, message):
		''' sign the message with SHA1 '''
		private_key_src = os.path.join(str(get_bench_path()), self.private_key)

		#digest = SHA256.new()
		digest = SHA.new()
		digest.update(message)

		# Read shared key from file
		private_key = False
		with open (private_key_src, "r") as myfile:
		    private_key = RSA.importKey(myfile.read())

		# Load private key and sign message
		signer = PKCS1_v1_5.new(private_key)
		sig = signer.sign(digest)

		# Load public key and verify message
		verifier = PKCS1_v1_5.new(private_key.publickey())
		verified = verifier.verify(digest, sig)
		#assert verified, 'Signature verification failed'
		#print 'Successfully verified message'
		if not verified:
			frappe.throw(_("Signature verification failed"))

		return sig.encode('hex').upper()	

