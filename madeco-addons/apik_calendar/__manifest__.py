# -*- coding: utf-8 -*-

{
    "name": "Apik - Calendar",
    "sequence": '0',
    "version": "14.0.0.0.1",
    "author": "APIK - Michel GUIHENEUF",
    "website": "http://www.apik-conseils.com",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Apik - Calendar",
    "summary": "Apik - Calendar",
    "depends": [
        'base',
        'sale',        
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company.xml", 
        #"views/sale_order.xml",        
    ],
    "demo": [
	    
    ],
    'qweb': [
        	    
    ],
    'installable': True,
	'application':True,
    'auto_install':False,
}
