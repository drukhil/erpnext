frappe.listview_settings['Invoice'] = {
        add_fields: ["docstatus", "paid"],
        has_indicator_for_draft: 1,
        get_indicator: function(doc) {
                if(doc.paid==0 && doc.docstatus ==0) {
                        return ["Draft", "red", "paid,=,0"];
                }

		if(doc.paid==0 && doc.docstatus ==1) {
			return ["Over Due", "darkgray", "paud,=,0"]
		}
                if(doc.paid == 1) {
                                return ["Received", "green", "paid=,1"];
                        }
                        }
};

