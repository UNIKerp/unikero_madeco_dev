# -*- coding: utf-8 -*-

{
    "name": "Import Data",
    "version": "1.0",
    "author": "APIK CONSEILS - François Le Gal",
    "website": "http://www.apik-conseils.com",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Import Data",
    "depends": [
        'base',
        'base_automation',
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/data.xml',
		'views/view.xml',
		'views/ir_actions.xml',
		'wizard/wizard.xml',
		'wizard/action_wizard.xml',
    ],
    "demo": [
	    
    ],
    'qweb': [
	    
    ],
    'installable': True,
	'application':True,
}
