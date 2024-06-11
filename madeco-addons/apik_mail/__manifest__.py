# -*- coding: utf-8 -*-

{
    "name": "Apik - Mail",
    "sequence": '0',
    "version": "14.0.0.0.1",
    "author": "APIK CONSEILS - Michel",
    "website": "http://www.apik.cloud",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Apik - Mail : pas de cadrage ",
    "summary": "Apik - Mail",
    "depends": [
        'base',
        'mail',
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_layout.xml",
    ],
    "demo": [
	    
    ],
    'qweb': [
            
    ],
    'installable': True,
	'application':True,
    'auto_install':False,
}
