# -*- coding: utf-8 -*-
{
    "name": "Madeco - SSCC",
    "description": "Madeco - SSCC",
    "sequence": '0',
    "version": "14.0.0.0.1",
    "author": "APIK",
    "maintainers": ["Claire Caparros", "Aurelien ROY"],
    "website": "https://www.apik.cloud/",
    "category": "Stock",
    "depends": [
        'base',
        'stock',
        'stock_barcode'
    ],
    "data": [
        'data/ir_sequence.xml',
        'data/report_paperformat.xml',
        'views/res_company.xml',
        # 'report/stock_picking_sscc.xml',
        # 'report/stock_picking_batch_sscc.xml',
        # 'report/stock_picking_sscc_multi.xml',
        # 'report/stock_picking_batch_sscc_multi.xml',
        'report/sscc_label.xml',
    ],
    'installable': True,
	'application': True,
    'auto_install': False
}
