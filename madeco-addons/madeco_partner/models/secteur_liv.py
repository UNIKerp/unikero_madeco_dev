# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)

class SecteurLivraison(models.Model):

    _name = "secteur.livraison"
    _description = "Secteur de livraison"
    _rec_name = 'name'
    _order = "name, id"    
    
    name = fields.Char('Nom du secteur', required=True, translate=True)
    active = fields.Boolean(string='Active', default=True) 
    


