# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.addons import decimal_precision as dp
from odoo.tools import float_compare, pycompat
import logging
logger = logging.getLogger(__name__)

'''
class ProductProduct(models.Model):
    _inherit = "product.product"
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):

        res = super(ProductProduct,self)._name_search(name=name,args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
    
        if len(args)==0:
            selection = ''
        else:
            selection = args[0][0]
        
        args = [('impression','ilike',name)]
        
        if selection == 'sale_ok':
            args = [('impression','ilike',name),('sale_ok','=',True)]

        if selection == 'purchase_ok':
            args = [('impression','ilike',name),('purchase_ok','=',True)]

        res2 = super(ProductProduct,self)._name_search(name="",args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

        return list(set(res + res2))

'''