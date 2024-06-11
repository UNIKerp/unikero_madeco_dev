# -*- coding: utf-8 -*-
"""
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
    Default Docstring
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    groupe_id = fields.Many2one('res.partner',string='Groupe', related='move_id.groupe_id', store=True, copy=False)
    centrale_id = fields.Many2one('res.partner',string='Centrale', related='move_id.centrale_id', store=True, copy=False)
    enseigne_id = fields.Many2one('res.partner',string='Enseigne', related='move_id.enseigne_id', store=True, copy=False)
    destinataire_relance = fields.Selection([('client', 'Client'),('centrale', 'Centrale'),], string='Destinataire des relances', 
        related='partner_id.destinataire_relance', store=True, copy=False)
    prix_promo = fields.Boolean(string='Promotion')
    line_global_discount = fields.Boolean(string="Global discount line", default=False, store=True, copy=False)


    @api.model  
    def calcul_px_net_ligne(self,lines=False):
        punet = 0
        for line in lines:
            if line.quantity != 0:
                punet = line.price_subtotal / line.quantity
            else:
                punet = 0    
        return punet