# -*- coding: utf-8 -*-
{
    "name": "Account Global Discount",
    "version": "13.0.1.1.0",
    "category": "Accounting",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/server-backend",
    "license": "AGPL-3",
    "depends": ["account", "base_global_discount"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/account_invoice_views.xml",
        "views/global_discount_views.xml",
        "views/report_account_invoice.xml",
    ],
    "application": False,
    "installable": True,
}
