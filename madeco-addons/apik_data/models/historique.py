# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)

class apik_historique(models.Model):
    _name = "apik.historique"
    
    name = fields.Text('Requete SQL')
    requete = fields.Many2one('apik.data',string="Requete")
    
    def remplacer(self):
        for h in self:
            h.requete.requete = h.name
            h.requete.executer()