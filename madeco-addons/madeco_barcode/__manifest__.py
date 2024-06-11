# -*- coding: utf-8 -*-
{
    "name": "Madeco - Barcode",
    "description": "Madeco - Barcode",
    "sequence": '0',
    "version": "14.0.1.0.0",
    "author": "APIK",
    "maintainers": ["Claire Caparros", "Aurelien ROY"],
    "website": "https://www.apik.cloud/",
    "category": "Stock",
    "depends": [
        'base',
        'stock',
        'stock_barcode',
        'delivery',
        'product',
        'web',
        'stock_picking_batch',
        'intrastat_product',
        'madeco_vente',
        'madeco_stock_sscc',
        'madeco_product', 
        'stock_multi_packaging',     
        'madeco_transport',   
    ],
    "data": [
        'data/product_packaging.xml',
        'data/report_paperformat.xml',
        'data/stock_picking_type.xml',
        'data/ir_actions_report.xml',
        'report/stock_picking_recut.xml',
        'report/stock_picking_preparation.xml',
        'views/sale_order.xml',
        'views/stock_picking_batch.xml',
        'views/stock_picking.xml',
        'views/stock_quant_package.xml',
        'views/stock_rule.xml',
        'security/ir.model.access.csv'
    ],
    'qweb': [
        'static/src/xml/barcode_templates.xml'
    ],
    'assets': {
    },
    'installable': True,
	'application': True,
    'auto_install': False,
}
