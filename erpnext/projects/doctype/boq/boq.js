// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("project", "branch", "branch");
cur_frm.add_fetch("project", "cost_center", "cost_center");
cur_frm.add_fetch("project", "party_type", "party_type");
cur_frm.add_fetch("project", "party", "party");

frappe.ui.form.on('BOQ', {
	setup: function (frm) {
		frm.get_docfield("boq_item").allow_bulk_edit = 1;

		frm.get_field('boq_item').grid.editable_fields = [
			{ fieldname: 'boq_code', columns: 1 },
			{ fieldname: 'item', columns: 3 },
			{ fieldname: 'is_group', columns: 1 },
			{ fieldname: 'uom', columns: 1 },
			{ fieldname: 'quantity', columns: 1 },
			{ fieldname: 'rate', columns: 1 },
			{ fieldname: 'amount', columns: 2 }
		];

		frm.get_field('boq_history_item').grid.editable_fields = [
			{ fieldname: 'transaction_type', columns: 2 },
			{ fieldname: 'transaction_date', columns: 2 },
			{ fieldname: 'initial_amount', columns: 2 },
			{ fieldname: 'adjustment_amount', columns: 2 },
			{ fieldname: 'final_amount', columns: 2 },
		];
		
		frm.get_field('boq_substitution_item').grid.editable_fields = [
                        { fieldname: 'transaction_type', columns: 2 },
                        { fieldname: 'transaction_date', columns: 2 },
                        { fieldname: 'initial_amount', columns: 2 },
                        { fieldname: 'substitution_amount', columns: 2 },
                        { fieldname: 'final_amount', columns: 2 },
                ];

		frm.get_field('boq_addition_item').grid.editable_fields = [
                        { fieldname: 'transaction_type', columns: 2 },
                        { fieldname: 'transaction_date', columns: 2 },
                        { fieldname: 'initial_amount', columns: 2 },
                        { fieldname: 'additional_amount', columns: 2 },
                        { fieldname: 'final_amount', columns: 2 },
                ];
		
		frm.get_field('initial_boq_item').grid.editable_fields = [
                        { fieldname: 'boq_code', columns: 1 },
                        { fieldname: 'item', columns: 3 },
                        { fieldname: 'is_group', columns: 1 },
                        { fieldname: 'uom', columns: 1 },
                        { fieldname: 'quantity', columns: 1 },
                        { fieldname: 'rate', columns: 1 },
                        { fieldname: 'amount', columns: 2 }
                ];

	},

	refresh: function (frm) {
		cur_frm.set_df_property("boq_item", "read_only",  frm.doc.docstatus == 1);

		boq_item_html(frm);
		if (!frm.doc.__islocal && frm.doc.docstatus == 1) {
			if (frappe.model.can_read("BOQ Adjustment")) {
				frm.add_custom_button(__("Adjustments"), function () {
					frappe.route_options = { "boq": frm.doc.name }
					frappe.set_route("List", "BOQ Adjustment");
				}, __("View"), true);
			}
			if (frappe.model.can_read("BOQ Substitution")) {
				frm.add_custom_button(__("Substitutions"), function () {
						frappe.route_options = { "boq": frm.doc.name }
						frappe.set_route("List", "BOQ Substitution");
				}, __("View"), true);
            }

			if (frappe.model.can_read("BOQ Addition")) {
				frm.add_custom_button(__("Additions"), function () {
						frappe.route_options = { "boq": frm.doc.name }
						frappe.set_route("List", "BOQ Addition");
				}, __("View"), true);
            }

			/*
			if(frappe.model.can_read("Project")) {
				frm.add_custom_button(__("Project"), function() {
					frappe.route_options = {"name": frm.doc.project}
					frappe.set_route("Form", "Project", frm.doc.project);
				}, __("View"), true);
			}
			*/

			if (frappe.model.can_read("MB Entry")) {
				frm.add_custom_button(__("MB Entries"), function () {
					frappe.route_options = { "boq": frm.doc.name }
					frappe.set_route("List", "MB Entry");
				}, __("View"), true);
			}

			if (frappe.model.can_read("Project Invoice")) {
				frm.add_custom_button(__("Invoices"), function () {
					frappe.route_options = { "boq": frm.doc.name }
					frappe.set_route("List", "Project Invoice");
				}, __("View"), true);
			}
		}

		frm.trigger("get_defaults");

		if (frm.doc.docstatus == 1) {
			//frm.add_custom_button(__("Advance"), function(){frm.trigger("make_boq_advance")},__("Make"), "icon-file-alt");
			frm.add_custom_button(__("BOQ Adjustment"), function () { frm.trigger("make_boq_adjustment") },
				__("Make"), "icon-file-alt"
			);
			//Logic for Substition and Extra Items Begins ---TASHI DORJI----
			
			frm.add_custom_button(__("BOQ Substitution"), function () { frm.trigger("make_boq_substitution") },
                __("Make"), "icon-file-alt"
            );
			frm.add_custom_button(__("BOQ Addition"), function () { frm.trigger("make_additional_boq") },
                __("Make"), "icon-file-alt"
            );
			//end the logic

			if (frm.doc.party_type !== "Supplier") {
				frm.add_custom_button(__("Subcontract"), function () { frm.trigger("make_boq_subcontract") }, __("Make"), "icon-file-alt");
			}
		}

		if (frm.doc.docstatus == 1 && parseFloat(frm.doc.claimed_amount) < (parseFloat(frm.doc.total_amount) + parseFloat(frm.doc.price_adjustment))) {
			/*
			frm.add_custom_button(__("Claim Advance"),function(){frm.trigger("claim_advance")},
				__("Make"), "icon-file-alt"
			);
			*/
			frm.add_custom_button(__("Measurement Book Entry"), function () { frm.trigger("make_book_entry") },
				__("Make"), "icon-file-alt"
			);
			/*
			frm.add_custom_button(__("Direct Invoice"),function(){frm.trigger("make_direct_invoice")},
				__("Make"), "icon-file-alt"
			);
			*/
			frm.add_custom_button(__("Invoice"), function () { frm.trigger("make_mb_invoice") },
				__("Make"), "icon-file-alt"
			);
		}

		/*
		$.each(cur_frm.doc['boq_item'], function(i, item){
			console.log($("div[data-fieldname=boq_item]").find(format('div.grid-row[data-idx="{0}"]', [item.idx])));
			$("div[data-fieldname=boq_item]").find(format('div.grid-row[data-idx="{0}"]', [item.idx])).css({'background-color': '#FF0000'});
			$("div[data-fieldname=boq_item]").find(format('div.grid-row[data-idx="{0}"]', [item.idx])).find('.grid-static-col').css({'background-color': '#FF0000'});
		})
		*/

		// Not working
		/*
		$.each(cur_frm.doc['boq_item'], function(i, item){
			//console.log(item.balance_amount); this line works
			//console.log($("div[data-fieldname=boq_item]").find(format('div.grid-row[data-idx="{0}"]', [item.idx])));
			if(parseFloat(item.balance_amount || 0.0) > 0.0){
				//console.log($("div[data-fieldname=boq_item]").find(format('div.grid-row[data-idx="{0}"]', [item.idx])));
				console.log($("div[data-fieldname=boq_item]").find(format('div.grid-row[data-name="{0}"]', [item.name])));
				//$("div[data-fieldname=boq_item]").find(format('div.grid-row[data-idx="{0}"]', [item.idx])).css({'background-color': '#FF0000'});
				$("div[data-fieldname=boq_item]").find(format('div.grid-row[data-name="{0}"]', [item.name])).css({'background-color': 'red'});
				$("div[data-fieldname=boq_item]").find(format('div.grid-row[data-idx="{0}"]', [item.idx])).find('.grid-static-col').css({'background-color': '#FF0000 !important'});
			}
		});
		*/
	},
	make_boq_adjustment: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.boq.boq.make_boq_adjustment",
			frm: frm
		});
	},


	//Substition and Extra Item logig Begins ----TASHI DORJI---
	make_boq_substitution: function (frm) {
                frappe.model.open_mapped_doc({
                        method: "erpnext.projects.doctype.boq.boq.make_boq_substitution",
                        frm: frm
                });
        },

	make_additional_boq: function (frm) {
                frappe.model.open_mapped_doc({
                        method: "erpnext.projects.doctype.boq.boq.make_additional_boq",
                        frm: frm
                });
        },
	//Logic Ends
	make_direct_invoice: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.boq.boq.make_direct_invoice",
			frm: frm
		});
	},

	make_boq_subcontract: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.boq.boq.make_boq_subcontract",
			frm: frm
		});
	},

	make_mb_invoice: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.boq.boq.make_mb_invoice",
			frm: frm
		});
	},

	make_book_entry: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.boq.boq.make_book_entry",
			frm: frm
		});
	},

	project: function (frm) {
		frm.trigger("get_defaults");
	},

	get_defaults: function (frm) {
		frm.add_fetch("project", "branch", "branch");
		frm.add_fetch("project", "cost_center", "cost_center");
	},

	make_boq_advance: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.boq.boq.make_boq_advance",
			frm: frm
		});
	},
});

frappe.ui.form.on("BOQ Item", {
	quantity: function (frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},

	rate: function (frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},

	amount: function (frm) {
		calculate_total_amount(frm);
	},
	no: function (frm, cdt, cdn) {
		child = locals[cdt][cdn];
		var quant = child.no * child.coefficient * child.height * child.length * child.breath
		frappe.model.set_value(cdt, cdn, 'quantity', parseFloat(quant));
	},
	breath: function (frm, cdt, cdn) {
		child = locals[cdt][cdn];
		var quant = child.no * child.coefficient * child.height * child.length * child.breath
		frappe.model.set_value(cdt, cdn, 'quantity', parseFloat(quant));
	},
	height: function (frm, cdt, cdn) {
		child = locals[cdt][cdn];
		var quant = child.no * child.coefficient * child.height * child.length * child.breath
		frappe.model.set_value(cdt, cdn, 'quantity', parseFloat(quant));
	},
	length: function (frm, cdt, cdn) {
		child = locals[cdt][cdn];
		var quant = child.no * child.coefficient * child.height * child.length * child.breath
		frappe.model.set_value(cdt, cdn, 'quantity', parseFloat(quant));
	},
	coefficient: function (frm, cdt, cdn) {
		child = locals[cdt][cdn];
		var quant = child.no * child.coefficient * child.height * child.length * child.breath
		frappe.model.set_value(cdt, cdn, 'quantity', parseFloat(quant));
	}
})

var calculate_amount = function (frm, cdt, cdn) {
	child = locals[cdt][cdn];
	amount = 0.0;

	//if(child.quantity && child.rate){
	amount = parseFloat(child.quantity) * parseFloat(child.rate)
	//}

	frappe.model.set_value(cdt, cdn, 'amount', parseFloat(amount));
	frappe.model.set_value(cdt, cdn, 'balance_quantity', parseFloat(child.quantity));
	frappe.model.set_value(cdt, cdn, 'balance_amount', parseFloat(amount));
}

var calculate_total_amount = function (frm) {
	var bi = frm.doc.boq_item || [];
	var total_amount = 0.0, balance_amount = 0.0;

	for (var i = 0; i < bi.length; i++) {
		if (bi[i].amount) {
			total_amount += parseFloat(bi[i].amount);
		}
	}
	balance_amount = parseFloat(total_amount) - parseFloat(frm.doc.received_amount)
	cur_frm.set_value("total_amount", total_amount);
	cur_frm.set_value("balance_amount", balance_amount);
}

/*
frappe.ui.form.on("BOQ Item", "is_group", function(frm, cdt, cdn){
    var child = locals[cdt][cdn];
    cur_frm.doc.boq_item.forEach(function(child){
		console.log(child);
        var sel = format('div[data-fieldname="boq_item"] > div.grid-row[data-idx="{0}"]', [child.idx]);
        if (child.is_group > 1000){
            $(sel).css('background-color', "#ff5858");
        } else {
            $(sel).css('background-color', 'transparent');
        }
    });
});
*/


var boq_item_html = function (frm) {
	/*
	cur_frm.doc.boq_item.forEach(function(row){
		console.log("==========================");
		var sel = format('div[data-fieldname="boq_item"] > div.grid-row[data-idx="{0}"]', [row.idx]);
		console.log($(sel).length);

        if (row.is_group){
			console.log('is_group: 1');
            $(sel).css('backgroundColor', "#ff5858");
        } else {
			console.log('is_group: 0');
            $(sel).css('backgroundColor', 'transparent');
        }
    });
	*/
}

// toggle display of items based on boq_type
/*
$(document).find('[data-fieldname="boq_type"]').change(function(){
	console.log('test',$(this).find(":selected").text());
	if($(this).find(":selected").text() !== "Milestone Based"){
		console.log('Non milestone');
	}
	$(document).find('[data-fieldname="quantity"]').toggle($(this).find(":selected").text() !== "Milestone Based");
});
*/
