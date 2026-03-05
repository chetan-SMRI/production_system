# Copyright (c) 2025, CHETAN NAHAR and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document
import pandas as pd
from production_system.api import clean


class ProductionTemplate(Document):
	def before_save(self):
		file_doc = frappe.get_doc("File", {"file_url": self.template_file})
		file_path = file_doc.get_full_path()
		df = pd.read_excel(file_path)

		# fetch unique task type and milestones
		types = set()
		milestones = set()
		for _, row in df.iterrows():
			t_type = clean(row.get("Type"))
			milestone = clean(row.get("Milestone"))
			if t_type:
				types.add(t_type)
			if milestone:
				milestones.add(milestone)

		# create Production Task Type and Production Milestone records if they don't exist
		for t_type in types:
			if not frappe.db.exists("Production Type", t_type):
				frappe.get_doc({"doctype": "Production Type", "type": t_type}).insert()
		for milestone in milestones:
			if not frappe.db.exists("Production Milestone", milestone):
				frappe.get_doc({"doctype": "Production Milestone", "milestone_name": milestone}).insert()