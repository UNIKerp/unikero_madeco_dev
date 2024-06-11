# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class TypeFluxEdi(models.Model):
    _name = 'type.flux'
    _description = 'Type Flux EDI'
    
    
    name = fields.Char(string="Nom du type flux", required=True, translate=True)
    code_gencod_id = fields.Many2one('flux.edi', string="Code gencod du flux", required=True)
    libelle_type_flux = fields.Char(string="Libellé du type de flux")
    active = fields.Boolean('Active', default=True)

