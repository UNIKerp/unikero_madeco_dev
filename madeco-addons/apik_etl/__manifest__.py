# -*- coding: utf-8 -*-

{
    "name": "Apik ETL",
    "version": "14.0",
    "author": "APIK - François Le Gal",
    "website": "http://www.apik.cloud",
    "license": "AGPL-3",
    "category": "Vertical",
    "description": "Apik ETL",
    "depends": [
        'base',
        
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/etl_source.xml',
        'data/etl_destination.xml',
        'views/apik_etl.xml',
        'views/apik_etl_extract.xml',
        'views/apik_etl_load.xml',
        'views/apik_etl_source.xml',
        'views/apik_etl_source_ss_type.xml',
        'views/apik_etl_destination.xml',
        'views/apik_etl_destination_ss_type.xml',        
    ],
    "demo": [
	    
    ],
    'qweb': [
	    
    ],
    'installable': True,
	'application':True,
}
