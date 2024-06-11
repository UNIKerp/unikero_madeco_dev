# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)

class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'


    active = fields.Boolean('Active', default=True,
        help="If unchecked, it will allow you to hide the price without removing it.")

    @api.onchange('name')
    def onchange_name_delai_fournisseur_custom(self):        
        if self.name:
            if self.name.delai_fournisseur:        
                self.delay = self.name.delai_fournisseur
        return {}

    @api.model_create_multi
    def create(self, vals_list):
        fourn_obj = self.env['res.partner']  

        for vals in vals_list:

            fourn_id = vals.get('name',False)
            delay = vals.get('delay',False)

            if not delay:
                if fourn_id:
                    fourn = fourn_obj.search([('id', '=', fourn_id)])
                    if fourn:
                        delai = fourn.delai_fournisseur
                        vals['delay'] = delai

        products = super(ProductSupplierinfo, self.with_context(create_product_product=True)).create(vals_list)
        
        if not products.delay:
            products.delay = products.name.delai_fournisseur
        return products