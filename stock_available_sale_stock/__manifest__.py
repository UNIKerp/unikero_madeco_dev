{
    "name": "Apik - Stock Available Sale Stock",
    "sequence": '0',
    "description": "Availability of components and articles when entering customer quotes",
    "version": "14.0.1.0.0",
     "author": "APIK - Michel GUIHENEUF",
    "website": "https://www.apik.cloud/",
    "license": "AGPL-3",    
    "category": "Vertical",
    "depends":
        [
            "base",
            "sale",
            "stock",
        ],
    "data": [
        "security/ir.model.access.csv",
        "data/groups.xml",
        "views/res_company.xml",
        "views/warehouse_product.xml",
        "views/warehouse.xml",
        "views/sale_order.xml",
        "views/partner_deadline.xml",
        "views/partner.xml",
        "views/product.xml",
    ],
    "demo": [
	    
    ],
    'qweb': [
        'static/src/xml/*.xml',   
    ],
    'installable': True,
	'application':True,
    'auto_install':False,   
}
