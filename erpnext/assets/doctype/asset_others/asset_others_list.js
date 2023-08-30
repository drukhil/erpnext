frappe.listview_settings['Asset Others'] = {
        add_fields: ["employee_name", "status"],
        get_indicator: function(doc) {
                if(doc.status == 'In-Use') {
			return [__("In-Use"), "green", "status,=,In-Use"];
                } else if(doc.status=="Returned") {
                        return [__("Returned"), "orange", "status,=,Returned"];
                }  else if(doc.status == "Damaged", 2) {
                        return [__("Damaged"), "red", "status,=,Damaged"];
                } 
        }
};
