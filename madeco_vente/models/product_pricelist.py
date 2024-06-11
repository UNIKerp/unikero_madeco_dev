# -*- coding: utf-8 -*-
"""
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
    Default Docstring
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    prix_promo = fields.Boolean(string='Promotion', default=False, store=True, copy=False)


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    prix_promo_item = fields.Boolean(string='Promotion', default=False, store=True, copy=False)    

    '''
    @api.onchange('product_tmpl_id','pricelist_id')
    def onchange_purchase_order(self):
        list_prix_obj = self.env['product.pricelist']    
        logger.info(self.env.context.get('active_id'))
        logger.info(self.env.context)
        id_prix = self.env.context.get('active_id', False)  
        for record in self:
            if id_prix:
                listprix = list_prix_obj.search([('id','=',id_prix)])  
                if listprix:
                    record.prix_promo_item = listprix.prix_promo 
                else:
                    record.prix_promo_item = False            
            else:
                record.prix_promo_item = False   
            logger.info("===============")
            logger.info(record.prix_promo_item)
            logger.info("===============")
    '''        