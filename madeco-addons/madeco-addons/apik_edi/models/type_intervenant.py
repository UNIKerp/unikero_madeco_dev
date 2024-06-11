# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class TypeIntervenantEdi(models.Model):
    _name = 'type.intervenant'
    _description = 'Type Intervenant EDI'
    
    
    name = fields.Char(string="Nom du type intervenant", required=True, translate=True)
    libelle_type_intervenant = fields.Char(string="Libellé du type intervenant", translate=True)
    active = fields.Boolean('Active', default=True)

