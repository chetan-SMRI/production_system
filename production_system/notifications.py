import frappe
from frappe.utils import nowdate, get_datetime
from whatsapp_web_automation.whatsapp_web_automation.api.send_message import send_message_in_background

def process_production_task_notifications():
	try:
		# Get settings (singleton)
		settings = frappe.get_single("Production Settings")

		whatsapp_account =  settings.whatsapp_account
		task_to_be_delayed = settings.task_to_be_delayed
		task_delayed_template = settings.task_delayed_template
		
		before_days_raw = settings.start_sending_notification_before_delay_date or ""
		send_after_delay = settings.send_notification_each_day_after_task_delayed

		# Convert "5,3,1" -> [5, 3, 1]
		before_days = []
		if before_days_raw:
			before_days = [int(x.strip()) for x in before_days_raw.split(",") if x.strip().isdigit()]

		today = get_datetime(nowdate()).date()

		# Fetch tasks
		tasks = frappe.get_all(
			"Production Task",
			filters={
				"status": ["in", ["Pending", "In Progress"]],
				"due_date": ["is", "set"],
				"assigned_to": ["is", "set"]
			},
			fields=["name", "due_date", "assigned_to"]
		)

		for task in tasks:
			if task.assigned_to != "pu@email.com":
				continue
			due_date = get_datetime(task.due_date).date()

			# Difference in days
			diff = (due_date - today).days

			task_doc = frappe.get_doc("Production Task", task.name)
			# --- Case 1: Today is due date ---
			if diff == 0:
				# send notification
				# send_notification(task.name, "Due Today")
				pu_mobile = frappe.get_value("User",task_doc.assigned_to,'mobile_no')
				context_data = task_doc.as_dict()
				send_message_in_background(whatsapp_account,pu_mobile,template=task_to_be_delayed,whitelabel=False,context=context_data)
				
				print(f"{task.name} -> due today")


			# --- Case 2: Before due date ---
			elif diff > 0 and diff in before_days:
				# send notification
				# send_notification(task.name, f"{diff} days remaining")
				pu_mobile = frappe.get_value("User",task_doc.assigned_to,'mobile_no')
				context_data = task_doc.as_dict()
				send_message_in_background(whatsapp_account,pu_mobile,template=task_to_be_delayed,whitelabel=False,context=context_data)

				print(f"{task.name} -> {diff} days before due")

			# --- Case 3: After due date ---
			elif diff < 0 and send_after_delay:
				# send notification
				# send_notification(task.name, f"{abs(diff)} days delayed")
				pu_mobile = frappe.get_value("User",task_doc.assigned_to,'mobile_no')
				context_data = task_doc.as_dict()
				send_message_in_background(whatsapp_account,pu_mobile,template=task_delayed_template,whitelabel=False,context=context_data)

				print(f"{task.name} -> {abs(diff)} days delayed")
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Error in processing production task notifications")