# -*- coding: utf-8 -*-

{
    "name": "Account Invoice Triple Discount",
    "version": "14.0.1.0.0",
    "category": "Accounting & Finance",
    "author": "QubiQ, Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-invoicing",
    "license": "AGPL-3",
    "summary": "Manage triple discount on invoice lines",
    "depends": ["account"],
    "data": [
        "report/invoice.xml", 
        "views/account_move.xml"
        ],
    "installable": True,
}