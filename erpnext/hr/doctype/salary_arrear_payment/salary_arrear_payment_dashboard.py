from __future__ import unicode_literals
from frappe import _

data = {
		'fieldname': 'salary_arrear_payment',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name'
		},
		'transactions': [
			{
				'label': _('Related'),
				'items': ['Journal Entry',]
			}
		]
	}