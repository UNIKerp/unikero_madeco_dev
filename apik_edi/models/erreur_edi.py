# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class FluxEdi(models.Model):
    _name = 'erreur.edi'
    _description = 'Erreur EDI'
    
    
    name = fields.Char(string="Erreur", required=True, store=True,translate=True)
    libelle_erreur = fields.Char(string="Libellé de l'erreur", default=False,store=True)
    active = fields.Boolean('Active', default=True)
    reussite = fields.Boolean('Intégration réussie', default=False)

