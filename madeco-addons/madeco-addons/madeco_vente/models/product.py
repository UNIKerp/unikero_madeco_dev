# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _

import logging
logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"
 
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):

        product_ids = super(ProductProduct,self)._name_search(name=name,args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        #
        # On ajoute une recherche dans les customer_product_code en dernier recours sur les ventes
        #
        if not product_ids and self._context.get('partner_id'):
            if len(args)==0:
                selection = ''
            else:
                selection = args[0][0]
            if selection == 'sale_ok':  
                customer_code_ids = self.env['product.customer.code']._search([
                    ('partner_id', '=', self._context.get('partner_id')),
                    '|',
                    ('product_code', operator, name),
                    ('product_name', operator, name)], access_rights_uid=name_get_uid)
                if customer_code_ids:
                    product_ids = self._search([('product_tmpl_id.product_customer_code_ids', 'in', customer_code_ids)], limit=limit, access_rights_uid=name_get_uid)

        return product_ids


class ProductTemplate(models.Model):
    _inherit = "product.template"

    art_frais_transport = fields.Boolean(string='Article Frais de transport', default=False, store=True, copy=False)


    

