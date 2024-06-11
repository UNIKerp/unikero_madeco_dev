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
    
    client_edi = fields.Boolean(string="Client Edi", default=False)
    code_gln = fields.Char(string="Code GLN")
    edi_order = fields.Boolean(string="EDI : Order – Commande  pour le message ORDRES", default=False)
    edi_ordchg = fields.Boolean(string="EDI : Order Change – Modification de commande pour le message ORDCHG", default=False)
    edi_ordrsp = fields.Boolean(string="EDI : Order response – Réponse à la commande pour le message ORDRSP", default=False)
    edi_desadv = fields.Boolean(string="EDI : Despatch Advice – Avis d’expédition pour le message DESADV", default=False)
    edi_invoic = fields.Boolean(string="EDI : Invoice – Facture pour le message INVOIC", default=False)
    edi_valid_auto = fields.Boolean(string="EDI : Validation automatique des commandes sans erreur", default=False)
    edi_liv_directe = fields.Boolean(string="EDI : Livraison directe client final", default=False)

    @api.model_create_multi
    def create(self, vals_list):
        ir_default_obj = self.env['ir.default']
        company_id =  self.env.company 
        parent_obj = self.env['res.partner']
        for vals in vals_list:            
            if vals.get('parent_id',False):
                parent_id = vals['parent_id']
                parent = parent_obj.search([('id', '=', parent_id)],limit=1)                
                vals['client_edi'] = parent.client_edi  
                #vals['code_gln'] = parent.code_gln  
                vals['edi_order'] = parent.edi_order  
                vals['edi_ordchg'] = parent.edi_ordchg 
                vals['edi_ordrsp'] = parent.edi_ordrsp  
                vals['edi_desadv'] = parent.edi_desadv  
                vals['edi_invoic'] = parent.edi_invoic     
                #vals['edi_valid_auto'] = parent.edi_valid_auto                
                #vals[''] = parent.  

        res = super(Partner, self).create(vals_list)    

        return res        


