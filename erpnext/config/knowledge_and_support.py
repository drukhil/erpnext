from __future__ import unicode_literals
from frappe import _

def get_data():
        return [
                {
                        "label": _("Raise Ticket"),
                        "items": [
                                {
                                        "type": "doctype",
                                        "name": "Issue List",
                                        "description": "Raise Tickets",
                                        "label": "Raise Tickets",
                                        "hide_count": False
                                }
                ]
                },
                {
                        "label": _("Ticket Status"),
                        "items": [
                                {
                                        "type": "report",
                                        "is_query_report": True,
                                        "name": "Ticket Status",
                                        "doctype": "Issue List"
                                }

                ]
                }

        ]

