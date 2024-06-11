# -*- coding: utf-8 -*-

#import json
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime, timedelta
from tempfile import TemporaryFile
import base64
import io
import logging
logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'  

    commande_presta = fields.Boolean(string="Commande Prestashop",default=False)
    no_cde_presta = fields.Char(string="No de commande client PrestaShop", copy=True)
    code_client_presta = fields.Char(related="partner_id.code_presta")
    cde_presta_genere = fields.Boolean(string="Enregistrement commande PrestaShop généré", copy=False, default=True)
    cde_presta_envoye = fields.Boolean(string="Enregistrement commande PrestaShop envoyé", copy=False, default=False)
    arc_presta_genere = fields.Boolean(string="Arc de commande PrestaShop généré", copy=False, default=False)
    arc_presta_envoye = fields.Boolean(string="Arc de commande PrestaShop envoyé", copy=False, default=False)
    mtt_paye = fields.Float(string="Mtt payé dans PrestaShop",copy=True)
    info_liv_presta = fields.Text(string="Informations de livraison", copy=True)
    date_devis_presta = fields.Datetime(string="Date de devis")
    



    def action_confirm(self):
        #
        # On regarde si le client est en PrestaShop 
        #        
        if self.partner_id.client_presta:
            self.arc_presta_genere = True                            
        else:
            self.arc_presta_genere = False       
            
        return super().action_confirm()

    def _prepare_confirmation_values(self):
        #
        # On regarde si c'est une commande PrestaShop  
        # 
        if self.commande_presta:
            if self.date_devis_presta:
                return {
                    'state':'sale',
                    'date_order': self.date_devis_presta,
                    }
            else:
                return super()._prepare_confirmation_values()
        else:
            return super()._prepare_confirmation_values()                

   

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'  

    lig_commande_presta = fields.Boolean(string="Ligne Commande PrestaShop",default=False)
    pun_presta = fields.Float(string="PUN PrestaShop", copy=True)
    no_ligne_presta = fields.Char(string="No ligne PrestaShop", copy=True)
    commande_prestaShop = fields.Boolean(related="order_id.commande_presta",string="Commande PrestaShop",default=False)

    