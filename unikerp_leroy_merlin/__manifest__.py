# -*- coding: utf-8 -*-

{
    "name": "UNIKerp - Leroy Merlin",
    "sequence": '0',
    "version": "14.0.0.0.1",
    "author": "UNIKerp",
    "website": "http://www.unikerp.com",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "UNIKerp - Leroy Merlin",
    "summary": "UNIKerp - Leroy Merlinp",
    "depends": [
        'apik_prestashop','mrp','purchase','apik_edi',
    ],
    "data": [
        'views/unik_fabrication.xml',
        'views/params_prestashop.xml',
        'views/action_unik.xml',
        'security/ir.model.access.csv',
    ],
    "demo": [  
    ],
    'qweb': [	    
    ],
    'installable': True,
	'application':True,
    'auto_install':False,
} # type: ignore
