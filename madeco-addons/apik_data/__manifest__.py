# -*- coding: utf-8 -*-

{
    "name": "Apik DATA",
    "version": "1.0",
    "author": "APIK CONSEILS - François Le Gal",
    "website": "http://www.apik-conseils.com",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Apik Data",
    "depends": [
        'base',
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/user.xml',
        'data/group.xml',
		'views/data.xml',
		'views/historique.xml',
		'views/assets.xml',
		'views/res_config_settings.xml',
		'views/user.xml',
    ],
    "demo": [
	    
    ],
    'qweb': [
	    'static/src/xml/tabulator.xml',
    ],
    'installable': True,
	'application':True,
}
