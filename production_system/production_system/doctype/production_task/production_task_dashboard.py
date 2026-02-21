from frappe import _


def get_data():
    return {
        "fieldname": "parent_task",
        # "internal_links": {
        #     "Sales Order": ["items", "sales_order"],
        # },
        "transactions": [
            {"label": _("Tasks"), "items": ["Production Task"]},
        ],
    }
