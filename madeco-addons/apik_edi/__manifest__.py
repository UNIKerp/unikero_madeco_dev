# -*- coding: utf-8 -*-

{
    "name": "Apik - EDI",
    "sequence": '0',
    "version": "14.0.0.0.1",
    "author": "APIK CONSEILS - Michel GUIHENEUF",
    "website": "http://www.apik-conseils.com",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Apik - EDI",
    "summary": "Apik - EDI",
    "depends": [
        'base',
        'sale',
        'account_payment_mode',  
        'intrastat_product',
        'stock',
        #'madeco_barcode',
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/param_edi.xml",
        "data/flux_edi.xml",
        "data/erreur_edi.xml",
        "data/type_intervenant.xml",
        "data/groups.xml",
        "data/fonction_flux_edi.xml",
        "data/type_flux_edi.xml",
        "data/payment_method_edi.xml",
		"views/partner.xml",
        #"views/payment_mode.xml",
        "views/flux_edi.xml",
        "views/suivi_edi.xml",
        "views/erreur_edi.xml",
        "views/param_edi.xml",
        "views/res_company.xml",
        "views/type_flux.xml",
        "views/function_flux.xml",
        "views/type_intervenant.xml",
        "views/payment_method_edi.xml",
        "views/unite.xml",
        "views/sale_order.xml",
        "views/picking.xml",
        "views/account_move.xml",
        "wizard/import_cde_edi.xml",
        "wizard/export_arc_cde_edi.xml",
        #"wizard/export_desadv.xml",   
        #"wizard/export_invoic.xml",     
        "views/menu_edi.xml",
        "views/stock_picking_type.xml",
        "views/intrastat_transport.xml",
        "views/account_fiscal.xml",
        "views/actions_edi.xml",
    ],
    "demo": [
	    
    ],
    'qweb': [
        	    
    ],
    'installable': True,
	'application':True,
    'auto_install':False,
}
