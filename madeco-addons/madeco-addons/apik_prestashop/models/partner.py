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
    
    client_presta = fields.Boolean(string="Client PrestaShop", default=False)
    code_presta = fields.Char(string="Code client PrestaShop")

    @api.model_create_multi
    def create(self, vals_list):
        parent_obj = self.env['res.partner']
        for vals in vals_list:            
            if vals.get('parent_id',False):
                parent_id = vals['parent_id']
                parent = parent_obj.search([('id', '=', parent_id)],limit=1)                
                vals['client_presta'] = parent.client_presta  
                vals['company_id'] = parent.company_id.id  
                #vals['code_presta'] = parent.code_presta                 

        res = super(Partner, self).create(vals_list)    

        return res        


