

frappe.listview_settings["Production Task"] = {
  hide_name_column: true,
    button: {
      show: function(doc) {
        return doc.status !== "Completed" && doc.status !== "Cancelled";
      },
      get_label: function() {
        return __("Task Completed");
      },
      get_description: function(doc) {
        return "Description";
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
          }
        },
      });
      }
  },

  add_fields: ["due_date","task_type","item","milestone"],

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
