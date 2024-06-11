# -*- coding: utf-8 -*-

{
    "name": "Madeco - Product",
    "sequence": '0',
    "version": "14.0.0.0.1",
    "author": "APIK CONSEILS - Michel GUIHENEUF",
    "website": "http://www.apik-conseils.com",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Madeco - Product",
    "summary": "Madeco - Product",
    "depends": [
        'base',
        'product',
        'delivery',
    ],
    "data": [
        #"security/ir.model.access.csv",
        "views/packaging.xml",
        "views/product.xml",
        
    ],
    "demo": [],  
    'qweb': [],
    'test': [],
    'installable': True,
	'application': True,
    'auto_install': False,
}
