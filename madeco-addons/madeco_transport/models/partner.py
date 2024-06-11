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
    
    madeco_transport_id = fields.Many2one('madeco.transport', string='Transporteur') 

    @api.model_create_multi
    def create(self, vals_list):
        parent_obj = self.env['res.partner']
        for vals in vals_list:            
            if vals.get('parent_id',False):
                parent_id = vals['parent_id']
                parent = parent_obj.search([('id', '=', parent_id)],limit=1)
                vals['madeco_transport_id'] = parent.madeco_transport_id.id 

        res = super(Partner, self).create(vals_list)    
        
        return res        
