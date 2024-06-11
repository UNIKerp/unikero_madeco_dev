# -*- coding: utf-8 -*-

{
    "name": "Apik PDP",
    "sequence": '0',
    "version": "14.0.0.0.1",
    "author": "APIK - François Le Gal",
    "website": "http://www.apik.cloud",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Apik PDP",
    "depends": [
        'base',
        'mrp_mps'
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/assets.xml',
		'views/mrp_mps_views.xml',
        'views/pdp_search.xml',
        
        'wizard/wz_export.xml',
        'wizard/wz_import.xml',
        
    ],
    "demo": [
	    
    ],
    'qweb': [
	    'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
