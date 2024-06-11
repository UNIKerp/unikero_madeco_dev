# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class ErreurPresta(models.Model):
    _name = 'erreur.presta'
    _description = 'Erreur PrestaShop'
    
    
    name = fields.Char(string="Erreur", required=True, store=True,translate=True)
    libelle_erreur = fields.Char(string="Libellé de l'erreur", default=False,store=True)
    active = fields.Boolean('Active', default=True)
    reussite = fields.Boolean('Intégration réussie', default=False)

