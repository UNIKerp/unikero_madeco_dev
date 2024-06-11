# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)

class MotifAvoir(models.Model):

    _name = "motif.avoir"
    _description = "Motif d'avoir"
    _rec_name = 'name'
    _order = "name, code, id"    
    
    name = fields.Char('Nom du motif', required=True, translate=True)
    code = fields.Char('Code du motif', required=True)
    active = fields.Boolean(string='Active', default=True) 
    


