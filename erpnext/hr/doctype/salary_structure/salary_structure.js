// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
/*
---------------------------------------------------------------------------------------------------------------------------
Version          Author            CreatedOn          ModifiedOn          Remarks
------------ ---------------  ------------------ -------------------  -----------------------------------------------------
2.0		          SHIV		      27/02/2018         					Dynamic get_query added for Salary_Components under
																			tables `earnings` and `deductions`
2.0#CDCL#886	  SHIV 		      06/09/2018 		   					Moved retirement_age, health_contribution, employee_pf, 
																			employer_pf from "HR Settings" to "Employee Group"
---------------------------------------------------------------------------------------------------------------------------
*/

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('company', 'default_letter_head', 'letter_head');

frappe.ui.form.on('Salary Structure', {
	onload: function(frm, cdt, cdn){
		e_tbl = frm.doc.earnings || [];
		d_tbl = frm.doc.deductions || [];
		
		if (e_tbl.length == 0 && d_tbl.length == 0){
			cur_frm.call({
				method: "make_earn_ded_table",
				doc: frm.doc
			});
		}
	},
	refresh: function(frm, cdt, cdn) {
		frm.trigger("toggle_fields")
		frm.fields_dict['earnings'].grid.set_column_disp("default_amount", false);
		frm.fields_dict['deductions'].grid.set_column_disp("default_amount", false);
		frm.fields_dict['earnings'].grid.set_column_disp("sb_additional_info", false);
		/*
		if((!frm.doc.__islocal) && (frm.doc.is_active == 'Yes') && cint(frm.doc.salary_slip_based_on_timesheet == 0)){
			cur_frm.add_custom_button(__('Salary Slip'),
				cur_frm.cscript['Make Salary Slip'], __("Make"));
			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
		}
		*/
	},
	employee: function(frm, cdt, cdn){
		if (frm.doc.employee) {
			cur_frm.call({
				method: "get_employee_details",
				doc: frm.doc
			});
		}
		calculate_others(frm.doc);
	},
	salary_slip_based_on_timesheet: function(frm) {
		frm.trigger("toggle_fields")
	},
	toggle_fields: function(frm) {
		frm.toggle_display(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
		frm.toggle_reqd(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
	},
	eligible_for_corporate_allowance: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_contract_allowance: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_communication_allowance: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_fuel_allowances: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_underground: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_shift: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_difficulty: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_high_altitude: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_psa: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_pda: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_deputation: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_officiating_allowance: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_temporary_transfer_allowance: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_scarcity: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_cash_handling: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_mpi: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_sws: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_gis: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_pf: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_health_contribution: function(frm){
		calculate_others(frm.doc);
	},
	ca: function(frm){
		calculate_others(frm.doc);
	},
	contract_allowance: function(frm){
		calculate_others(frm.doc);
	},
	communication_allowance: function(frm){
		calculate_others(frm.doc);
	},
	psa: function(frm){
		calculate_others(frm.doc);
	},
	mpi: function(frm){
		calculate_others(frm.doc);
	},
	officiating_allowance: function(frm){
		calculate_others(frm.doc);
	},
	temporary_transfer_allowance: function(frm){
		calculate_others(frm.doc);
	},
	/*
	lumpsum_temp_transfer_amount: function(frm) {
		calculate_others(frm.doc);
		calculate_totals(frm.doc);
	},
	*/
	fuel_allowances: function(frm){
		calculate_others(frm.doc);
	},
	pda: function(frm){
		calculate_others(frm.doc);
	},
	shift: function(frm){
		calculate_others(frm.doc);
	},
	deputation: function(frm){
		calculate_others(frm.doc);
	},
	underground: function(frm){
		calculate_others(frm.doc);
	},
	difficulty: function(frm){
		calculate_others(frm.doc);
	},
	high_altitude: function(frm){
		calculate_others(frm.doc);
	},
	scarcity: function(frm){
		calculate_others(frm.doc);
	},
	cash_handling: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_hra: function(frm){
                calculate_others(frm.doc);
        },
	// Payment Methods
	ca_method: function(frm){
		calculate_others(frm.doc);
	},
	contract_allowance_method: function(frm){
		calculate_others(frm.doc);
	},
	communication_allowance_method: function(frm){
		calculate_others(frm.doc);
	},
	psa_method: function(frm){
		calculate_others(frm.doc);
	},
	mpi_method: function(frm){
		calculate_others(frm.doc);
	},
	officiating_allowance_method: function(frm){
		calculate_others(frm.doc);
	},
	temporary_transfer_allowance_method: function(frm){
		calculate_others(frm.doc);
	},
	fuel_allowances_method: function(frm){
		calculate_others(frm.doc);
	},
	pda_method: function(frm){
		calculate_others(frm.doc);
	},
	shift_method: function(frm){
		calculate_others(frm.doc);
	},
	deputation_method: function(frm){
		calculate_others(frm.doc);
	},
	underground_method: function(frm){
		calculate_others(frm.doc);
	},
	difficulty_method: function(frm){
		calculate_others(frm.doc);
	},
	high_altitude_method: function(frm){
		calculate_others(frm.doc);
	},
	scarcity_method: function(frm){
		calculate_others(frm.doc);
	},
	cash_handling_method: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_banking_allowance: function(frm) {
                calculate_others(frm.doc);
        },
        banking_allowance_methods: function(frm){
                calculate_others(frm.doc);
        },
        banking_allowance: function(frm){
                calculate_others(frm.doc)
        },
        eligible_for_project_allowance: function(frm) {
                calculate_others(frm.doc);
        },
        project_allowance_method: function(frm){
                calculate_others(frm.doc);
        },
        project_allowance: function(frm){
                calculate_others(frm.doc)
        },
	eligible_for_vha_allowance: function(frm){
		calculate_others(frm.doc);
	},
	vha_method: function(frm){
		calculate_others(frm.doc);
	},
	vha: function(frm){
		calculate_others(frm.doc);
	},
	eligible_for_medical_allowance: function(frm){
                calculate_others(frm.doc);
        },
	medical_allowance_method: function(frm){
                calculate_others(frm.doc);
        },
	medical_allowance: function(frm){
                calculate_others(frm.doc);
        },
	eligible_for_royal_audit_allowance: function(frm){
                calculate_others(frm.doc);
        },
	royal_audit_allowance_method: function(frm){
                calculate_others(frm.doc);
        },
	royal_audit_allowance: function(frm){
                calculate_others(frm.doc);
        },


})

frappe.ui.form.on('Salary Detail', {
	amount: function(frm, cdt, cdn) {
		calculate_others(frm.doc);
	},
	
	earnings_remove: function(frm) {
		calculate_others(frm.doc);
	}, 
	
	deductions_remove: function(frm) {
		calculate_others(frm.doc);
	},
	
	total_deductible_amount: function(frm, cdt, cdn){
		d = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "total_outstanding_amount", parseFloat(d.total_deductible_amount || 0.0)-parseFloat(d.total_deducted_amount || 0.0));
	},
})

var calculate_others = function(doc){
	cur_frm.call({
		method: "update_salary_structure",
		doc: doc
	
	});
}

cur_frm.fields_dict.employee.get_query = function(doc,cdt,cdn) {
			return{ query: "erpnext.controllers.queries.employee_query" }
}

cur_frm.cscript['Make Salary Slip'] = function() {
	frappe.model.open_mapped_doc({
		method: "erpnext.hr.hr_custom_functions.make_salary_slip",
		frm: cur_frm
	});
}

// ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++
// Following code added by SHIV on 2018/02/27
frappe.ui.form.on("Salary Structure", "refresh", function(frm) {
    frm.fields_dict['earnings'].grid.get_field('salary_component').get_query = function(doc, cdt, cdn) {
        doc = locals[cdt][cdn]
        return {
            "query": "erpnext.hr.doctype.salary_structure.salary_structure.salary_component_query",
            filters: {'parentfield': 'earnings'}
        }
    };
});

frappe.ui.form.on("Salary Structure", "refresh", function(frm) {
    frm.fields_dict['deductions'].grid.get_field('salary_component').get_query = function(doc, cdt, cdn) {
        doc = locals[cdt][cdn]
        return {
            "query": "erpnext.hr.doctype.salary_structure.salary_structure.salary_component_query",
            filters: {'parentfield': 'deductions'}
        }
    };
});
// +++++++++++++++++++++ Ver 2.0 ENDS +++++++++++++++++++++
