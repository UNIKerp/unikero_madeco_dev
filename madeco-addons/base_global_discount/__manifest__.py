# -*- coding: utf-8 -*-

{
    "name": "Base Global Discount",
    "version": "13.0.2.0.0",
    "category": "Base",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/server-backend",
    "license": "AGPL-3",
    "depends": ["product"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/global_discount_views.xml",
        "views/res_partner_views.xml",
    ],
    "application": False,
    "installable": True,
}
