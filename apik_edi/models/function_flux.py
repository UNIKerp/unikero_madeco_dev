# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class FunctionFluxEdi(models.Model):
    _name = 'function.flux'
    _description = 'Fonction Flux EDI'
    
    
    name = fields.Char(string="Nom de fonction du flux", required=True, translate=True)
    code_gencod_id = fields.Many2one('flux.edi', string="Code gencod du flux", required=True)
    libelle_function_flux = fields.Char(string="Libellé de la fonction du flux")
    active = fields.Boolean('Active', default=True)

