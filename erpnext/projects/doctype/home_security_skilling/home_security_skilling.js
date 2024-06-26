// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("project_name", "name", "cost_center");
cur_frm.add_fetch("project_name", "branch", "branch");
cur_frm.add_fetch("parent_project", "cost_center", "parent_cost_center");
cur_frm.add_fetch("parent_project", "holiday_list", "holiday_list");
// cur_frm.add_fetch("cost_center", "name", "project_name"); 
cur_frm.add_fetch("parent_project", "mandays", "overall_mandays" );
cur_frm.add_fetch("reference_budget", "actual_total", "estimated_budget" );

frappe.ui.form.on('Home Security Skilling', {
	setup: function(frm) {
		frm.get_docfield("activity_tasks").allow_bulk_edit = 1;			
		
		frm.get_field('activity_tasks').grid.editable_fields = [
			{fieldname: 'task', columns: 3},
			{fieldname: 'is_milestone', columns: 1},
			{fieldname: 'start_date', columns: 2},
			{fieldname: 'end_date', columns: 2},
			{fieldname: 'task_completion_percent', columns: 2},
		];	
	},	
	
	onload: function(frm) {
		enable_disable(frm);
		cur_frm.fields_dict['parent_project'].get_query = function(doc, dt, dn) {
			return {
				filters:{"is_group": 1}
			}
		}

	},
	refresh: function(frm) {
		enable_disable(frm);
		if (!frm.doc.__islocal) {
			frm.trigger('show_progress');
		}
	},
	is_group: function(frm) {
		if (frm.doc.is_group == 1) {
			cur_frm.set_value('parent_project', '');
			cur_frm.set_value('project_category', '');
			cur_frm.set_value('project_sub_category', '');
			cur_frm.set_df_property("overall_mandays", "read_only", 1);
		} else {
			cur_frm.set_df_property("overall_mandays", "read_only", 1);
		}
		
	},
	project_category: function(){
		cur_frm.set_value('project_sub_category', '');
		cur_frm.fields_dict['project_sub_category'].get_query = function(doc, dt, dn) {
		   return {
				filters:{"project_category": doc.project_category}
		   }
		}
	},
	
	show_progress: function(frm) {
		var bars = [];
		var message = '';
		var added_min = false;

		var title = __('{0} Percent Completed ', [parseFloat(frm.doc.percent_completed, 2)]);
		bars.push({
				'title': title,
				'width': parseFloat(frm.doc.percent_completed) + '%',
				'progress_class': 'progress-bar-success'
		});
		if (bars[0].width == '0%') {
				bars[0].width = '0.5%';
				added_min = 0.5;
		}
		message = __('<b style="color: green; font-size: 110%;">  {0} Percent Completed </b>', [parseFloat(frm.doc.percent_completed, 2)]);
		if(frm.doc.percent_completed !== 100){
				var pending_complete = 100 - frm.doc.percent_completed;
				if(pending_complete) {
						var title = __('{0} Remaining to Complete the Activity', [pending_complete]);
						var width = parseFloat(pending_complete) - added_min
						bars.push({
								'title': title,
								'width': (width > 100 ? "99.5" : width)  + '%',
								'progress_class': 'progress-bar-warning'
						})
						message = message + ', ' + __('<b style="color: orange; font-size: 110%;"> {0} Remaining to Complete the Activity </b>', [pending_complete]);
				}
		}
		frm.dashboard.add_progress(__('Status'), bars, message);
	},
	expected_start_date: function(cur_frm) {
		if(cur_frm.doc.expected_end_date) {
			calculate_duration(cur_frm, cur_frm.doc.expected_start_date, cur_frm.doc.expected_end_date);
		}
	},
	expected_end_date: function() {
		if(cur_frm.doc.expected_start_date) {
			calculate_duration(cur_frm, cur_frm.doc.expected_start_date, cur_frm.doc.expected_end_date);
		}
	},
	mandays: function() {
		cur_frm.set_value("overall_mandays", (cur_frm.doc.is_group == 1)?cur_frm.doc.mandays:0);
		cur_frm.set_value("physical_progress_weightage", (parseFloat(cur_frm.doc.mandays)/parseFloat(cur_frm.doc.overall_mandays)*100).toFixed(3))
		cur_frm.set_value("man_power_required", Math.round(parseFloat(cur_frm.doc.mandays)/parseFloat(cur_frm.doc.total_duration)))
	},
	// overall_mandays: function() {
	// 	cur_frm.set_value("physical_progress_weightage", (parseFloat(cur_frm.doc.mandays)/parseFloat(cur_frm.doc.overall_mandays)*100).toFixed(3))
	// },
	total_duration: function() {
		cur_frm.set_value("man_power_required", Math.round(parseFloat(cur_frm.doc.mandays)/parseFloat(cur_frm.doc.total_duration)))
	},
});

var enable_disable = function(frm){
	//Display tasks only after the project is saved
	cur_frm.toggle_display("activity_tasks", !frm.doc.__islocal);
}

function calculate_duration(cur_frm, from_date, to_date) {
	frappe.call({
		method: "erpnext.projects.doctype.home_security_skilling.home_security_skilling.calculate_durations",
			args: {
				"hol_list": cur_frm.doc.holiday_list,
				"from_date": from_date,
				"to_date": to_date
			},
		callback: function(r) {
			if(r.message) {
				cur_frm.set_value('total_duration', r.message);
		}
	}
	})
}