# -*- coding: utf-8 -*-

{
    "name": "Madeco - Transports",
    "sequence": '0',
    "version": "14.0.0.0.1",
    "author": "APIK CONSEILS - Michel GUIHENEUF",
    "website": "http://www.apik-conseils.com",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Madeco - Transports",
    "summary": "Madeco - Transports",
    "depends": [
        'base',
        'sale',
        'stock',
        'madeco_vente',
        'apik_edi',             
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/report_paperformat_ptt.xml",
        "views/stock_picking.xml",
        "views/intrastat_transport.xml",
        "views/transporteur.xml",
        "report/report.xml",
        "report/etiquette_laposte.xml",        
        "views/stock_picking_type.xml",
        "data/transporteur_madeco.xml",  
        "views/partner.xml", 
        "views/sale_order.xml",  
        "views/account_move.xml", 
        "security/rule_transport.xml",   
    ],
    "demo": [
	    
    ],
    'qweb': [
        	    
    ],
    'installable': True,
	'application':True,
    'auto_install':False,
}
