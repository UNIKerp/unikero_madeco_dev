# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class FunctionFluxEdi(models.Model):
    _name = 'payment.method'
    _description = 'Méthode de paiement EDI'    
    
    name = fields.Char(string="Nom de la méthode de paiement", required=True, translate=True)
    code_gencod_id = fields.Many2one('flux.edi', string="Code gencod du flux", required=True)
    libelle_payment_method = fields.Char(string="Libellé de la méthode de paiement")
    active = fields.Boolean('Active', default=True)

