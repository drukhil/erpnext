// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

//cur_frm.add_fetch("cost_center", "branch", "branch");
cur_frm.add_fetch("branch", "cost_center", "cost_center");
cur_frm.add_fetch("cost_center", "name", "project_name"); 
cur_frm.add_fetch("project_name", "parent_cost_center", "parent_cost_center");
cur_frm.add_fetch("project_name", "branch", "branch");
cur_frm.add_fetch("parent_project", "mandays", "overall_mandays" );
cur_frm.add_fetch("parent_project", "holiday_list", "holiday_list");
cur_frm.add_fetch("reference_budget", "actual_total", "estimated_budget" );

frappe.ui.form.on("Project", {
	setup: function(frm) {
		frm.get_docfield("activity_tasks").allow_bulk_edit = 1;		
		frm.get_docfield("additional_tasks").allow_bulk_edit = 1;		
		
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
		if(!frm.doc.__islocal){
			if(!frm.doc.is_group){
			frm.add_custom_button(__("Project Progress Report"), function(){
					frappe.route_options = {
						activity: frm.doc.name,
						from_date: frm.doc.expected_start_date,
						to_date: frm.doc.expected_end_date
					};
					frappe.set_route("query-report", "Project Progress Report");
				},__("<b style='color: blue; font-size: 110%;'> Progress Reports </b>"), "icon-file-alt"
			);
			frm.add_custom_button(__("Project Progress Graph"), function(){
					frappe.route_options = {
						activity: frm.doc.name,
						from_date: frm.doc.expected_start_date,
						to_date: frm.doc.expected_end_date
					};
					frappe.set_route("query-report", "Project Progress Graphs");
				},__("<b style='color: blue; font-size: 110%;'> Progress Graphs </b>"), "icon-file-alt"
			);
			}
			else {
			frm.add_custom_button(__("Project Progress Report"), function(){
                                        frappe.route_options = {
                                                project: frm.doc.name,
                                                from_date: frm.doc.expected_start_date,
                                                to_date: frm.doc.expected_end_date
                                        };
                                        frappe.set_route("query-report", "Project Progress Report");
                                },__("<b style='color: blue; font-size: 110%;'> Progress Reports </b>"), "icon-file-alt"
                        );
                        frm.add_custom_button(__("Project Progress Graph"), function(){
                                        frappe.route_options = {
                                                project: frm.doc.name,
                                                from_date: frm.doc.expected_start_date,
                                                to_date: frm.doc.expected_end_date
                                        };
                                        frappe.set_route("query-report", "Project Progress Graphs");
                                },__("<b style='color: blue; font-size: 110%;'> Progress Graphs </b>"), "icon-file-alt"
                        );
			}
		}
		
		if(frm.doc.__islocal) {
			frm.web_link && frm.web_link.remove();
		} /*else {
			frm.add_web_link("/projects?project=" + encodeURIComponent(frm.doc.name));

			if(frappe.model.can_read("Task")) {
				frm.add_custom_button(__("Gantt Chart"), function() {
					frappe.route_options = {"project": frm.doc.name,
						"start": frm.doc.expected_start_date, "end": frm.doc.expected_end_date};
					frappe.set_route("Gantt", "Task");
				});
			}

			frm.trigger('show_dashboard');
		}
		*/

	if (!frm.doc.__islocal) {
                        frm.trigger('show_progress');
                }

	},

	show_progress: function(frm) {
                var bars = [];
                var message = '';
                var added_min = false;

       
                var title = __('<b style="color: green; font-size: 110%;">  {0} Percent Completed </b>', [parseFloat(frm.doc.percent_completed, 2)]);
                bars.push({
                        'title': title,
                        'width': parseFloat(frm.doc.percent_completed) + '%',
                        'progress_class': 'progress-bar-success'
                });
                if (bars[0].width == '0%') {
                        bars[0].width = '0.5%';
                        added_min = 0.5;
                }
                message = title;
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
                                message = message + '. ' + title;
                        }
                }
                frm.dashboard.add_progress(__('Status'), bars, message);
        },
			
		
	branch: function(frm){
		// Update Cost Center
		if(frm.doc.branch){
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Cost Center',
					filters: {
						'branch': frm.doc.branch
					},
					fieldname: ['name']
				},
				callback: function(r){
					if(r.message){
						cur_frm.set_value("cost_center", r.message.name);
						refresh_field('cost_center');
					}
				}
			});
		}
	},
	
	project_category: function(){
		cur_frm.set_value('project_sub_category','');
		cur_frm.fields_dict['project_sub_category'].get_query = function(doc, dt, dn) {
		   return {
				filters:{"project_category": doc.project_category}
		   }
		}
	}
	,

	expected_start_date: function(cur_frm) {
		if(cur_frm.doc.expected_end_date) {
			calculate_duration(cur_frm, cur_frm.doc.expected_start_date, cur_frm.doc.expected_end_date);
	//cur_frm.set_value('total_duration', frappe.datetime.get_day_diff(cur_frm.doc.expected_end_date, cur_frm.doc.expected_start_date) + 1)
		}
	},
	
	
	expected_end_date: function() {
		if(cur_frm.doc.expected_start_date) {
			calculate_duration(cur_frm, cur_frm.doc.expected_start_date, cur_frm.doc.expected_end_date);
	//cur_frm.set_value('total_duration', frappe.datetime.get_day_diff(cur_frm.doc.expected_end_date, cur_frm.doc.expected_start_date) + 1)
		}
	},
	mandays: function() {
		cur_frm.set_value("physical_progress_weightage", (parseFloat(cur_frm.doc.mandays)/parseFloat(cur_frm.doc.overall_mandays)*100).toFixed(3))
		cur_frm.set_value("man_power_required", Math.round(parseFloat(cur_frm.doc.mandays)/parseFloat(cur_frm.doc.total_duration)))
	},
	overall_mandays: function() {
		cur_frm.set_value("physical_progress_weightage", (parseFloat(cur_frm.doc.mandays)/parseFloat(cur_frm.doc.overall_mandays)*100).toFixed(3))
	},
	total_duration: function() {
		cur_frm.set_value("man_power_required", Math.round(parseFloat(cur_frm.doc.mandays)/parseFloat(cur_frm.doc.total_duration)))
	},
	physical_progress_weightage: function() {
		//cur_frm.set_value("percent_completed", (parseFloat(cur_frm.doc.physical_progress)/parseFloat(cur_frm.doc.physical_progress_weightage) *100).toFixed(4))
		//cur_frm.set_value("physical_progress", (parseFloat(cur_frm.doc.percent_completed)/100 * parseFloat(cur_frm.doc.physical_progress_weightage)).toFixed(4))
	},
	//percent_completed: function() {
		//cur_frm.set_value("physical_progress", (parseFloat(cur_frm.doc.percent_completed)/100 * parseFloat(cur_frm.doc.physical_progress_weightage)).toFixed(4))
	//}
});



// ++++++++++++++++++++ Ver 1.0 BEGINS ++++++++++++++++++++
// Following block of code added by SHIV on 11/08/2017
frappe.ui.form.on("Activity Tasks", {
	
	task_category: function(frm, doctype, name) {
		var child = locals[doctype][name]
		frm.set_query('task_sub_category', 'activity_tasks', function() {
			return {
				'filters': {
					'task_category': child.task_category
				}
			};
		});
	},
	
	start_date: function(frm, doctype, name) {
		var item = locals[doctype][name]
		var at = frm.doc.activity_tasks || [];
        	var task_duration = 0.0
        	if(item.end_date) {
			calculate_duration1(frm, doctype, name, item.start_date, item.end_date);
		}
		for(var i=0; i<at.length; i++){
                        task_duration += parseFloat(at[i].task_duration || 0.0);
                }
		cur_frm.set_value('duration_sum', task_duration)
		//frappe.model.set_value(doctype, name, "task_weightage", (parseFloat(item.task_duration)/parseFloat(task_duration) * parseFloat(cur_frm.doc.physical_progress_weightage)).toFixed(7));
		frappe.model.set_value(doctype, name, "task_weightage", (parseFloat(item.task_duration)/parseFloat(task_duration)*100).toFixed(7));
		frappe.model.set_value(doctype, name, "one_day_weightage", (parseFloat(item.task_weightage)/parseFloat(item.task_duration)).toFixed(7))
	},
	end_date: function(frm, doctype, name) {
		var item = locals[doctype][name]
		var at = frm.doc.activity_tasks || [];
                var task_duration = 0.0
		if(item.start_date) {
			calculate_duration1(frm, doctype, name, item.start_date, item.end_date);
		}
                for(var i=0; i<at.length; i++){
                        task_duration += parseFloat(at[i].task_duration || 0.0);
                }
		cur_frm.set_value('duration_sum', task_duration);
                //frappe.model.set_value(doctype, name, "task_weightage", (parseFloat(item.task_duration)/parseFloat(task_duration)* parseFloat(cur_frm.doc.physical_progress_weightage)).toFixed(7));
                frappe.model.set_value(doctype, name, "task_weightage", (parseFloat(item.task_duration)/parseFloat(task_duration)*100).toFixed(7));
		frappe.model.set_value(doctype, name, "one_day_weightage", (parseFloat(item.task_weightage)/parseFloat(item.task_duration)).toFixed(7))

},
	task_completion_percent: function(frm, doctype, name) {
		var item = locals[doctype][name]
		frappe.model.set_value(doctype, name, "task_achievement_percent", (parseFloat(item.task_completion_percent/100)*parseFloat(item.task_weightage)).toFixed(7));
		frappe.model.set_value(doctype, name, "one_day_achievement", (parseFloat(item.task_achievement_percent)/parseFloat(item.task_duration).toFixed(7)))
	
	},
	task_duration: function(frm, doctype, name) {
	},
	task_achievement_percent: function(frm, doctype, name) {
	var at = frm.doc.activity_tasks || [];
        var task_achievement_percent1 = 0.0
        for(var i=0; i<at.length; i++){
                        task_achievement_percent1 += parseFloat(at[i].task_achievement_percent || 0.0);
                }
        cur_frm.set_value("percent_completed", (parseFloat(task_achievement_percent1)).toFixed(4))
	cur_frm.set_value("physical_progress", (parseFloat(cur_frm.doc.percent_completed)/100 * parseFloat(cur_frm.doc.physical_progress_weightage)).toFixed(4))
	}
});


frappe.ui.form.on("Project", "refresh", function(frm) {
    cur_frm.set_query("cost_center", function() {
        return {
            "filters": {
		"is_group": 0,
		"is_disabled": 0
            }
        };
    });
})


function calculate_duration(cur_frm, from_date, to_date) {
        frappe.call({
                method: "erpnext.projects.doctype.project.project.calculate_durations",
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

function calculate_duration1(cur_frm, doctype, name, from_date, to_date) {
        frappe.call({
                method: "erpnext.projects.doctype.project.project.calculate_durations",
                 args: {
                        "hol_list": cur_frm.doc.holiday_list,
                        "from_date": from_date,
                        "to_date": to_date
                   },
                callback: function(r) {
                       if(r.message){
                           frappe.model.set_value(doctype, name, 'task_duration', r.message);
                        }
                }
        })
}


var enable_disable = function(frm){
        //Display tasks only after the project is saved
        cur_frm.toggle_display("activity_and_tasks", !frm.doc.__islocal);
        cur_frm.toggle_display("activity_tasks", !frm.doc.__islocal);
        cur_frm.toggle_display("sb_additional_tasks", !frm.doc.__islocal);
        cur_frm.toggle_display("additional_tasks", !frm.doc.__islocal);
}


cur_frm.fields_dict['activity_tasks'].grid.get_field('task_sub_category').get_query = function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        return {
                filters: [
                ['Task Sub Category', 'task_category', '=', d.task_category]
                ]
                }
        }
frappe.ui.form.on("Project Task", {
        /*edit_task: function(frm, doctype, name) {
                var doc = frappe.get_doc(doctype, name);
                if(doc.task_id) {
                        frappe.set_route("Form", "Task", doc.task_id);
                } else {
                        msgprint(__("Save the document first."));
                }
        },
        status: function(frm, doctype, name) {
                frm.trigger('tasks_refresh');
        },*/
});

// ++++++++++++++++++++ Ver 1.0 BEGINS ++++++++++++++++++++
// Following function created by SHIV on 2017/08/17
var calculate_work_quantity = function(frm){
	var at = frm.doc.activity_tasks || [];
	var adt= frm.doc.additional_tasks || [];
	total_work_quantity = 0.0;
	total_work_quantity_complete = 0.0;
	total_add_work_quantity = 0.0;
	total_add_work_quantity_complete = 0.0;

	for(var i=0; i<at.length; i++){
		//console.log(at[i].is_group);
		if (at[i].work_quantity && !at[i].is_group){
			total_work_quantity += at[i].work_quantity || 0;
			total_work_quantity_complete += at[i].work_quantity_complete || 0;
		}
	}
	
	for(var i=0; i<adt.length; i++){
		//console.log(at[i].is_group);
		if (adt[i].work_quantity && !adt[i].is_group){
			total_add_work_quantity += adt[i].work_quantity || 0;
			total_add_work_quantity_complete += adt[i].work_quantity_complete || 0;
		}
	}
	
	cur_frm.set_value("tot_wq_percent",total_work_quantity);
	cur_frm.set_value("tot_wq_percent_complete",total_work_quantity_complete);
	cur_frm.set_value("tot_add_wq_percent",total_add_work_quantity);
	cur_frm.set_value("tot_add_wq_percent_complete",total_add_work_quantity_complete);
}
// +++++++++++++++++++++ Ver 1.0 ENDS +++++++++++++++++++++



var update_party_info=function(doc){
        cur_frm.call({
                method: "update_party_info",
                doc:doc
        });
}


