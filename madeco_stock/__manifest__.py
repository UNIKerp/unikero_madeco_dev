# -*- coding: utf-8 -*-

{
    "name": "Madeco - Stock",
    "sequence": "0",
    "version": "14.0.0.0.1",
    "author": "APIK CONSEILS - Michel GUIHENEUF",
    "website": "http://www.apik-conseils.com",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Madeco - Stock",
    "summary": "Madeco - Stock",
    "depends": [
        "base",
        "stock",
        "madeco_vente",
        "stock_barcode_picking_batch",
        "stock_barcode",
    ],
    "data": [
        "views/stock_picking.xml",
        "views/stock_picking_batch.xml",
        "views/stock_picking_type.xml",
        "views/sw_orderpoint.xml",
        "views/actions_stock.xml",
        "views/res_company.xml",
        "views/assets.xml",
        "report/delivery.xml",
    ],
    "demo": [],
    "qweb": [
        "static/src/xml/*.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
