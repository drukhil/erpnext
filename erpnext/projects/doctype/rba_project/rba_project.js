// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('RBA Project', {
	setup: function(frm) {
		frm.get_docfield("activity_tasks").allow_bulk_edit = 1;			
		frm.get_field('activity_tasks').grid.editable_fields = [
			{fieldname: 'task', columns: 3},
			{fieldname: 'start_date', columns: 2},
			{fieldname: 'end_date', columns: 2},
			{fieldname: 'task_completion_percent', columns: 2},
		];	
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
frappe.ui.form.on("RBA Project Task", {
	
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
