# -*- coding: utf-8 -*-

{
    "name": "Apik - WEB PrestaShop",
    "sequence": '0',
    "version": "14.0.0.0.1",
    "author": "APIK CONSEILS - Michel GUIHENEUF",
    "website": "http://www.apik-conseils.com",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Apik - WEB PrestaShop",
    "summary": "Apik - WEB PrestaShop",
    "depends": [
        'base',
        'sale', 
        'stock',       
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/param_presta.xml",
        "data/erreur_presta.xml",
        "data/groups.xml",
		"views/partner.xml",  
        "views/erreur_presta.xml",   
        "views/param_presta.xml",
        "views/suivi_presta.xml",
        "views/res_company.xml", 
        "views/sale_order.xml",        
        "wizard/import_cde_presta.xml",
        "wizard/export_arc_cde_presta.xml",        
        "views/menu_prestashop.xml",
        "views/actions_prestashop.xml",
        "views/stock_picking_type.xml",
    ],
    "demo": [
	    
    ],
    'qweb': [
        	    
    ],
    'installable': True,
	'application':True,
    'auto_install':False,
}
