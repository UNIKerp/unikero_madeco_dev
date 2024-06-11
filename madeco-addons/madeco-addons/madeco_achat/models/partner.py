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
    
    delai_fournisseur = fields.Integer(string="Délai de livraison fournisseur")
    incoterm_id = fields.Many2one('account.incoterms', string='Code incoterm')


    @api.model_create_multi
    def create(self, vals_list):
        ir_default_obj = self.env['ir.default']
        company_id =  self.env.user.company_id 
        parent_obj = self.env['res.partner']
        for vals in vals_list:            
            if vals.get('parent_id',False):
                parent_id = vals['parent_id']
                parent = parent_obj.search([('id', '=', parent_id)],limit=1)
                vals['delai_fournisseur'] = parent.delai_fournisseur   
                vals['incoterm_id'] = parent.incoterm_id.id
                #vals[''] = parent. 
                
        res = super(Partner, self).create(vals_list)  
        return res 


