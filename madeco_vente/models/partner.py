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
    
    delai_livraison = fields.Integer(string="Délai de livraison du client", default=0, store=True, copy=True)
    sale_global_discount = fields.Float(string="Invoice footer discount", digits="discount", required=False, default=0.0)
    aff_pourcentage = fields.Char(string='pourcentage',default=" %")
    xdock = fields.Boolean(string="Livraison XDOCK", default=False)
    intrastat_transport_id = fields.Many2one('intrastat.transport_mode', string='Transporteur') 
    delai_demande_sup_a = fields.Integer(string="Délai demandé supérieur à", default=0, store=True, copy=True)
    mtt_superieur = fields.Integer(string="Montant supérieur", default=0, store=True, copy=True)
    delai_transport = fields.Integer(string="Délai de transport", default=0, store=True, copy=True)

    @api.model_create_multi
    def create(self, vals_list):
        parent_obj = self.env['res.partner']
        for vals in vals_list:            
            if vals.get('parent_id',False):
                parent_id = vals['parent_id']
                parent = parent_obj.search([('id', '=', parent_id)],limit=1)
                vals['delai_livraison'] = parent.delai_livraison  
                vals['delai_demande_sup_a'] = parent.delai_demande_sup_a  
                vals['mtt_superieur'] = parent.mtt_superieur  
                vals['delai_transport'] = parent.delai_transport  
                vals['intrastat_transport_id'] = parent.intrastat_transport_id.id 
                vals['property_delivery_carrier_id'] = parent.property_delivery_carrier_id.id 

        res = super(Partner, self).create(vals_list)    
        
        return res        
