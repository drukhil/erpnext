// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Supplier Monitoring', {
	refresh: function(frm) {

	},
	setup: function(frm) {
		frm.set_query("purchase_order", function(){
			return {
				filters: [
					["docstatus", "=", 1]
				]
			}
		});
	},
	purchase_order: function(frm){
		if (!cur_frm.doc.purchase_order) return
		get_items(frm)
	}
});
function get_items(cur_frm) {
	
		frappe.call({
				method: "get_items",
				doc: cur_frm.doc,
				args: {
					"po": cur_frm.doc.purchase_order
			   },
				callback: function(r) {
							cur_frm.refresh_field("items");
							cur_frm.refresh_fields();
		},
		freeze: true,
		freeze_message: "Loading Items..... Please Wait"
		})
	
}
frappe.ui.form.on("Supplier Monitoring Item", {
	
	received_date: function(frm, doctype, name) {
				var item = locals[doctype][name]
				var at = frm.doc.items || [];
		        	var days_delayed = 0.0
		        	if(item.schedule_date) {
					calculate_duration(frm, doctype, name, item.schedule_date, item.received_date, item.new_delivery_date, cur_frm.doc.extension_date, cur_frm.doc.give_extension);
				}	
				// cur_frm.set_value('days_delayed', days_delayed)
			},
	
	received_quantity: function(frm, doctype, name) {
		var item = locals[doctype][name]
		frappe.model.set_value(doctype, name, "balance_quantity", (item.qty-item.received_quantity));
		frappe.model.set_value(doctype, name, "received_amount", (parseFloat(item.rate)*item.received_quantity))
		frappe.model.set_value(doctype, name, "undelivered_amount", (parseFloat(item.rate)*item.balance_quantity))
		frappe.model.set_value(doctype, name, "liquidated_damage", (parseFloat(item.received_amount)*(item.days_delayed) *.001))

			
	}

});
frappe.ui.form.on("Supplier Monitoring", "refresh", function(frm) {
    cur_frm.set_query("purchase_order", function() {
        return {
            "filters": {
		"docstatus": 1
		
            }
        };
    });
})

function calculate_duration(cur_frm, doctype, name, from_date, to_date, new_from_date, extension_date, give_extension) {
	frappe.call({
			method: "erpnext.buying.doctype.supplier_monitoring.supplier_monitoring.calculate_durations",
			 args: {
					"from_date": from_date,
					"to_date": to_date,
					"new_from_date": new_from_date,
					"extension_date": extension_date,
					"give_extension": give_extension
			   },
			callback: function(r) {
					console.log(r.message)
				   if(r.message){
					   frappe.model.set_value(doctype, name, 'days_delayed', r.message);
					   cur_frm.refresh_field()
					}
			}
	})
	}