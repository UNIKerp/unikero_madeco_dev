# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)

class TypologieCommande(models.Model):

    _name = "typologie.commande"
    _description = "Order typology"
    _rec_name = 'name'
    _order = "name, id"    
    
    name = fields.Char('Order typology', required=True, translate=True)
    code = fields.Char('Order typology code', required=True, translate=True)
    active = fields.Boolean(string='Active', default=True) 
    


