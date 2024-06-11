# -*- coding: utf-8 -*-

{
    "name": "Madeco - Partner",
    "sequence": '0',
    "version": "14.0.0.0.1",
    "author": "APIK CONSEILS - Michel GUIHENEUF",
    "website": "http://www.apik-conseils.com",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Madeco - Partner",
    "summary": "Madeco - Partner",
    "depends": [
        'base',
        'contacts', 
        'account',
        'sale',
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/partner.xml",
        "views/ir_default.xml",
        "views/secteur_liv.xml",
        "views/company.xml",
    ],
    "demo": [],  
    'qweb': [],
    'test': [],
    'installable': True,
	'application': True,
    'auto_install': False,
}
