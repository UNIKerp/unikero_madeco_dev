# -*- coding: utf-8 -*-

import json
from datetime import datetime
from odoo.tools import float_compare, float_round
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import unidecode
import logging
logger = logging.getLogger(__name__)


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    
    code_dzb = fields.Boolean(string='DZB Bank', default=False)
    num_client_dzb = fields.Char(string="DZB Bank Customer Number", required=False, readonly=False)
    couvert_coface = fields.Boolean(string='COFACE covered', default=False)
    mtt_couvert_coface = fields.Float(string="COFACE covered amount", required=False, readonly=False)
    factor = fields.Boolean(string='Factor', default=False)      
    
    @api.model_create_multi
    def create(self, vals_list):
        parent_obj = self.env['res.partner']
        for vals in vals_list:
            if vals.get('parent_id',False):
                parent_id = vals['parent_id']
                parent = parent_obj.search([('id', '=', parent_id)],limit=1)
                vals['code_dzb'] = parent.code_dzb  
                vals['num_client_dzb'] = parent.num_client_dzb
                vals['couvert_coface'] = parent.couvert_coface 
                vals['mtt_couvert_coface'] = parent.mtt_couvert_coface
                vals['factor'] = parent.factor           
                        
        return super(Partner, self).create(vals_list)     
