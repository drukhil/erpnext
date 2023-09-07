// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("equipment", "fuelbook", "fuelbook")
cur_frm.add_fetch("fuelbook", "branch", "fuelbook_branch")
cur_frm.add_fetch("fuelbook_branch", "cost_center", "cost_center")

frappe.ui.form.on('POL Advance', {
    onload: function (frm) {
        set_party_type(frm);
        // frm.set_query("party", function() {
        // 	return {
        // 		"filters": {
        // 			"is_pol_supplier": 1
        // 		}
        // 	};
        // });
        cur_frm.set_query("select_cheque_lot", function () {
            return {
                "filters": [
                    ["status", "!=", "Used"],
                    ["docstatus", "=", "1"],
                    /*		["branch", "=", frm.doc.branch] */
                ]
            }
        });
    },
    select_cheque_lot: function (frm) {
        if (frm.doc.select_cheque_lot) {
            frappe.call({
                method: "erpnext.accounts.doctype.cheque_lot.cheque_lot.get_cheque_no_and_date",
                args: {
                    'name': frm.doc.select_cheque_lot
                },
                callback: function (r) {
                    if (r.message) {
                        cur_frm.set_value("cheque_no", r.message[0].reference_no);
                        cur_frm.set_value("cheque_date", r.message[1].reference_date);
                    }
                }
            });

        }
    },
    paty_type: (frm) => {
        set_party_type(frm);
        // if(frm.doc.docstatus == 1){
        // 	frappe.meta.get_docfield("Stock Entry", "select_cheque_lot", cur_frm.doc.name).read_only = 1;
        // }
    },
    refresh: (frm) => {
        open_ledger(frm);
    },
    amount: (frm) => {
        console.log("hello world")
        calculate_balance(frm);
    },
    select_cheque_lot: (frm) => {
        fetch_cheque_lot(frm)
    },
});

var set_party_type = (frm) => {
    cur_frm.set_query('party_type', (frm) => {
        return {
            'filters': {
                'name': 'Supplier'
            }
        };
    });
}


var fetch_cheque_lot = (frm) => {
    if (frm.doc.select_cheque_lot) {
        frappe.call({
            method: "erpnext.accounts.doctype.cheque_lot.cheque_lot.get_cheque_no_and_date",
            args: {
                'name': frm.doc.select_cheque_lot
            },
            callback: function (r) {
                console.log(r.message)
                if (r.message) {
                    cur_frm.set_value("cheque_no", r.message[0].reference_no);
                    cur_frm.set_value("cheque_date", r.message[1].reference_date);
                    cur_frm.refresh_field('cheque_no')
                    cur_frm.refresh_field('cheque_date')
                }
            }
        });
    }
}
var calculate_balance = (frm) => {
    console.log("yyyyyyyyyyyyyyyy")
    if (frm.doc.amount > 0) {
        console.log("under the condition rn")
        cur_frm.set_value("balance_amount", frm.doc.amount)
        cur_frm.set_value("adjusted_amount", 0)
    }
}
var open_ledger = (frm) => {
    if (frm.doc.docstatus === 1) {
        frm.add_custom_button(
            __("Accounting Ledger"),
            function () {
                frappe.route_options = {
                    voucher_no: frm.doc.name,
                    from_date: frm.doc.entry_date,
                    to_date: frm.doc.entry_date,
                    company: frm.doc.company,
                    group_by_voucher: false,
                };
                frappe.set_route("query-report", "General Ledger");
            },
            __("View")
        );
    }
}