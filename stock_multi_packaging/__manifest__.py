# -*- coding: utf-8 -*-
{
    'name': 'Stock Multi Packaging',
    'version': '14.0.0.1',
    'category': 'Inventory/Inventory',
    'description': "",
    'summary': "Manage multi packaging for batch picking",
    'author': 'Apik',
    "maintainers": ["Aurelien ROY"],
    'website': 'https://apik.cloud',
    'depends': [
        'base',
        'stock_barcode',
        'delivery',
        'stock',
    ],
    'data': [
        'data/packaging_data.xml',
        'data/ir_actions_act_window.xml',
        'views/assets.xml',
        'views/stock_picking_type.xml',
        'views/stock_move_line.xml', 
        'wizard/choose_batch_package.xml',    
        'wizard/choose_type_package.xml', 
        'security/ir.model.access.csv',  
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'pre_init_hook': '',
    'post_init_hook': '',
    'license': 'LGPL-3',
}
