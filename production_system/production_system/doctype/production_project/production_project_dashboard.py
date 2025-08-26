from frappe import _


def get_data():
    return {
        "fieldname": "project",
        # "internal_links": {
        #     "Sales Order": ["items", "sales_order"],
        # },
        "transactions": [
            {"label": _("Tasks"), "items": ["Production Task"]},
        ],
    }
