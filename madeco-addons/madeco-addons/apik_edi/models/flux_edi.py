# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class FluxEdi(models.Model):
    _name = 'flux.edi'
    _description = 'Flux EDI'
    
    
    name = fields.Char(string="Nom du flux", required=True, store=True,translate=True)
    code_gencod_id = fields.Char(string="Code gencod du flux", required=True, store=True,translate=True)
    libelle_flux = fields.Char(string="Libellé du flux", default=False,store=True)
    active = fields.Boolean('Active', default=True)
    envoi_auto_mail = fields.Boolean('Envoi automatique des mails', default=False)

