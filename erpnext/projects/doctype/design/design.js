cur_frm.add_fetch("parent_project", "branch", "branch");


frappe.ui.form.on('Design', {
	setup: function(frm) {
		frm.get_docfield("activity_tasks").allow_bulk_edit = 1;			
		frm.get_field('activity_tasks').grid.editable_fields = [
			{fieldname: 'task', columns: 3},
			{fieldname: 'start_date', columns: 2},
			{fieldname: 'end_date', columns: 2},
			{fieldname: 'task_completion_percent', columns: 2},
		];	
	},

	onload: function(frm) {
				//  enable_disable(frm);
				cur_frm.fields_dict['parent_project'].get_query = function(doc, dt, dn) {
		                   return {
		                                filters:{"is_group": 1}
		                   }
		                }
		
			},
	refresh: function(frm) {
		// enable_disable(frm);
		if(!frm.doc.__islocal){
			if(!frm.doc.is_group){
			frm.add_custom_button(__("Design Progress Report"), function(){
					frappe.route_options = {
						activity: frm.doc.name,
						from_date: frm.doc.expected_start_date,
						to_date: frm.doc.expected_end_date
					};
					frappe.set_route("query-report", "Design Progress Report");
				},__("<b style='color: blue; font-size: 110%;'> Progress Reports </b>"), "icon-file-alt"
			);
			// frm.add_custom_button(__("Project Progress Graph"), function(){
			// 		frappe.route_options = {
			// 			activity: frm.doc.name,
			// 			from_date: frm.doc.expected_start_date,
			// 			to_date: frm.doc.expected_end_date
			// 		};
			// 		frappe.set_route("query-report", "Project Progress Graphs");
			// 	},__("<b style='color: blue; font-size: 110%;'> Progress Graphs </b>"), "icon-file-alt"
			// );
			}
			else {
			frm.add_custom_button(__("Design Progress Report"), function(){
                                        frappe.route_options = {
                                                project: frm.doc.name,
                                                from_date: frm.doc.expected_start_date,
                                                to_date: frm.doc.expected_end_date
                                        };
                                        frappe.set_route("query-report", "Design Progress Report");
                                },__("<b style='color: blue; font-size: 110%;'> Progress Reports </b>"), "icon-file-alt"
                        );
                        // frm.add_custom_button(__("Project Progress Graph"), function(){
                        //                 frappe.route_options = {
                        //                         project: frm.doc.name,
                        //                         from_date: frm.doc.expected_start_date,
                        //                         to_date: frm.doc.expected_end_date
                        //                 };
                        //                 frappe.set_route("query-report", "Project Progress Graphs");
                        //         },__("<b style='color: blue; font-size: 110%;'> Progress Graphs </b>"), "icon-file-alt"
                        // );
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
                        bars[0].width = '0.8%';
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
	project_category: function(){
		cur_frm.set_value('project_sub_category','');
		cur_frm.fields_dict['project_sub_category'].get_query = function(doc, dt, dn) {
		   return {
				filters:{"project_category": doc.project_category}
		   }
		}
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

	
});

frappe.ui.form.on("Design Tasks", {
	
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
				var at = frm.doc.design_tasks || [];
		        	var task_duration = 0.0
		        	if(item.end_date) {
					calculate_duration1(frm, doctype, name, item.start_date, item.end_date);
				}
				
				
			},
	end_date: function(frm, doctype, name) {
				var item = locals[doctype][name]
				var at = frm.doc.design_tasks || [];
		                var task_duration = 0.0
				if(item.start_date) {
					calculate_duration1(frm, doctype, name, item.start_date, item.end_date);
				}
		                for(var i=0; i<at.length; i++){
						
				}
				
		},
	task_weightage: function(frm, doctype, name){
		var item = locals[doctype][name]
		var at = frm.doc.design_tasks || [];
		var one_day_weightage = 0.0
		if(item.task_weightage) {
			frappe.model.set_value(doctype, name, "one_day_weightage", (parseFloat(item.task_weightage)/parseFloat(item.task_duration)).toFixed(4))
		}
	},
	task_completion_percent: function(frm, doctype, name) {
		var item = locals[doctype][name]
		frappe.model.set_value(doctype, name, "task_achievement_percent", (parseFloat(item.task_completion_percent/100)*parseFloat(item.task_weightage)).toFixed(4));
		frappe.model.set_value(doctype, name, "one_day_achievement", (parseFloat(item.task_achievement_percent)/parseFloat(item.task_duration).toFixed(4)))
			
	},

	task_achievement_percent: function(frm, doctype, name) {
		var at = frm.doc.activity_tasks || [];
		var task_achievement_percent1 = 0.0
		task_achievement_percent1 += parseFloat(at[i].task_achievement_percent || 0.0);
		cur_frm.set_value("percent_completed", (parseFloat(task_achievement_percent1) * 100).toFixed(4))
		cur_frm.set_value("physical_progress", (parseFloat(cur_frm.doc.percent_completed) * parseFloat(cur_frm.doc.physical_progress_weightage)).toFixed(4))
	}

});
	

function calculate_duration(cur_frm, from_date, to_date) {
	        frappe.call({
	                method: "erpnext.projects.doctype.design.design.calculate_durations",
	                 args: {
	                       
	                        "from_date": from_date,
	                        "to_date": to_date
	                   },
	                callback: function(r) {
	                        if(r.message) {
	                        	cur_frm.set_value('total_duration', r.message);
				}
			}
	        })
			
	};

function calculate_duration1(cur_frm, doctype, name, from_date, to_date) {
        frappe.call({
                method: "erpnext.projects.doctype.design.design.calculate_durations",
                 args: {
                        
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
        cur_frm.toggle_display("_tasks", !frm.doc.__islocal);
        cur_frm.toggle_display("sb_additional_tasks", !frm.doc.__islocal);
        cur_frm.toggle_display("additional_tasks", !frm.doc.__islocal);
}