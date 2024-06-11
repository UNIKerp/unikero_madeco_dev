# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)

class CategorieCommande(models.Model):

    _name = "categorie.commande"
    _description = "Order category"
    _rec_name = 'name'
    _order = "name, id"    
    
    name = fields.Char('Order category', required=True, translate=True)
    code = fields.Char('Order category code', required=True, translate=True)
    active = fields.Boolean(string='Active', default=True) 
    


