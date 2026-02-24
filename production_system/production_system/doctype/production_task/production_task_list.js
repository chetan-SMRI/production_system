

frappe.listview_settings["Production Task"] = {
  	onload: function(listview) {
      // Hide frappe's default assigned to
      setTimeout(() => {

        // Hide the entire left sidebar
        $(".layout-side-section").remove();

        // Expand the main content to full width
        $(".layout-main-section").removeClass("col-lg-10").addClass("col-lg-12");

      }, 300);
      setTimeout(() => {

        $(".group-by-field").each(function () {
          let label = $(this).find("span.ellipsis").text().trim();

          if (label === "Assigned To") {
            $(this).hide();
          }
        });

      }, 800);

      // Add custom button

      listview.page.add_action_item(__("Bulk Assign"), function() {
          const selected = listview.get_checked_items();

          if (selected.length === 0) {
              frappe.msgprint("Please select at least one task.");
              return;
          }

          const dialog = new frappe.ui.Dialog({
              title: 'Assign Tasks To',
              fields: [
                  {
                      label: 'Assign To',
                      fieldname: 'assign_to',
                      fieldtype: 'Link',
                      options: 'User',
                      reqd: true
                  }
              ],
              primary_action_label: 'Proceed',
              primary_action: function (values) {
                  dialog.hide();

                  frappe.confirm(
                      `Are you sure you want to assign ${selected.length} tasks to ${values.assign_to}?`,
                      async () => {
                          for (let row of selected) {
                              await frappe.call({
                                  method: "frappe.client.set_value",
                                  args: {
                                      doctype: "Production Task",
                                      name: row.name,
                                      fieldname: {
                                          "assigned_to": values.assign_to
                                      }
                                  },
                                  callback: function (r) {
                                      if (!r.exc) {
                                          frappe.show_alert(`${row.name} updated`);
                                      }
                                  }
                              });
                          }

                          listview.refresh();
                      }
                  );
              }
          });

          dialog.show();

      });
      listview.page.add_action_item(__("Set Due Date"), function() {
          const selected = listview.get_checked_items();

          if (selected.length === 0) {
              frappe.msgprint("Please select at least one task.");
              return;
          }

          const dialog = new frappe.ui.Dialog({
              title: 'Set Due Date',
              fields: [
                  {
                      label: 'Due Date',
                      fieldname: 'due_date',
                      fieldtype: 'Date',
                      reqd: true
                  }
              ],
              primary_action_label: 'Proceed',
              primary_action: function (values) {
                  dialog.hide();

                  frappe.confirm(
                      `Are you sure you want to set the due date for ${selected.length} tasks to ${values.due_date}?`,
                      async () => {
                          for (let row of selected) {
                              await frappe.call({
                                  method: "frappe.client.set_value",
                                  args: {
                                      doctype: "Production Task",
                                      name: row.name,
                                      fieldname: {
                                          "due_date": values.due_date
                                      }
                                  },
                                  callback: function (r) {
                                      if (!r.exc) {
                                          frappe.show_alert(`${row.name} updated`);
                                      }
                                  }
                              });
                          }

                          listview.refresh();
                      }
                  );
              }
          });

          dialog.show();

      });
	},

  hide_name_column: true,
    button: {
      show: function(doc) {
        return (doc.status !== "Completed" && doc.status !== "Cancelled") && !doc.is_parent;
      },
      get_label: function() {
        return __("Mark Completed");
      },
      get_description: function(doc) {
        return "Complete Task";
      },
      action: function(doc) {
        frappe.call({
        method: "frappe.client.set_value",
        args: {
          doctype: "Production Task",
          name: doc.name,
          fieldname: "status",
          value: "Completed",
        },
        callback: function (r) {
          if (!r.exc) {
            frappe.show_alert({
              message: __("Task {0} marked as Completed", [doc.name]),
              indicator: "green",
            });
            // refresh the list view row so button disappears
            cur_list.refresh();
            //update once more after 100ms
            setTimeout(() => {
              cur_list.refresh();
            }, 100);
            setTimeout(() => {
              cur_list.refresh();
            }, 500);
          }
        },
      });
      }
  },

  add_fields: ["due_date","task_type","item","milestone", "is_parent"],

  formatters: {
    due_date: function (value, df, row, data) {
      if (!value) return "";

	  if (["Completed", "Cancelled"].includes(row.status)) {
      return `<div style="font-size:0.95rem; color:#6b7280; font-weight:600;">
                ${row.status}
              </div>`;
	    }


      const diff = daysDiffFromTodaySafe(value);

      if (diff === null) {
        return `<div class="text-destructive font-semibold">Invalid date</div>`;
      }

      let text = "";
      let color = "";

      if (diff > 1) {
        text = `${diff} days left`;
        color = "#16a34a"; // green
      } else if (diff === 1) {
        text = `1 day left`;
        color = "#16a34a"; // green
      } else if (diff === 0) {
        text = `Today`;
        color = "#f59e0b"; // yellow
      } else {
        const delayed = Math.abs(diff);
        text = `${delayed} day${delayed === 1 ? " delay" : "s delay"}`;
        color = "#ef4444"; // red
      }

      return `
        <div style="display:flex;align-items:center;gap:8px;">
          <div style="font-size:0.95rem; color: ${color}; font-weight:600;">
            ${text}
          </div>
        </div>
      `;
    },
	task_subject: function (value, df, row, rowdata) {
		if(row.task_type == "Item"){
			return `${row.item} - ${row.task_subject} (${row.milestone})`;
		}
		return `${row.task_subject} (${row.milestone})`;
	}
  },
};

// === Helpers ===

// Parse "YYYY-MM-DD" safely into local Date
function parseYMDToDate(ymd) {
  if (!ymd || typeof ymd !== "string") return null;
  const parts = ymd.split("-");
  if (parts.length !== 3) return null;
  const y = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  const d = parseInt(parts[2], 10);
  if (Number.isNaN(y) || Number.isNaN(m) || Number.isNaN(d)) return null;
  return new Date(y, m - 1, d, 0, 0, 0, 0);
}

// Get difference in whole days: due - today
function daysDiffFromTodaySafe(dueDateStr) {
  const due = parseYMDToDate(dueDateStr);
  if (!due) return null;
  const today = parseYMDToDate(frappe.datetime.get_today());
  const msPerDay = 24 * 60 * 60 * 1000;
  return Math.floor((due - today) / msPerDay);
}
