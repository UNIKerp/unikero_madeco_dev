# -*- coding: utf-8 -*-

{
    "name": "Madeco - Comptabilité",
    "sequence": '0',
    "version": "14.0.0.0.1",
    "author": "APIK CONSEILS - Michel GUIHENEUF",
    "website": "http://www.apik-conseils.com",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Madeco - Comptabilité",
    "summary": "Madeco - Comptabilité",
    "depends": [
        'base',
        'account',
        'account_move_csv_import',
        'account_partner_reconcile',
        'intrastat_product',
        'l10n_fr_intrastat_product',
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/motif_avoir.xml",
        "views/res_company.xml",
        "views/partner.xml",
        "views/motif_avoir.xml",
        "views/account_move.xml",
        "views/product.xml",
        "wizard/affect_date_maturity.xml",
    ],
    "demo": [
	    
    ],
    'qweb': [
        	    
    ],
    
    'installable': True,
	'application':True,
    'auto_install':False,
}
