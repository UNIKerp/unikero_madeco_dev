# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import logging
logger = logging.getLogger(__name__)

class ProductPackaging(models.Model):
    _inherit = "product.packaging"
    
    
    longueur = fields.Integer(string="Longueur en cm")
    largeur = fields.Integer(string="Largeur en cm")
    hauteur = fields.Integer(string="Hauteur en cm")
    volume = fields.Float(string="Volume en M3")
    poids = fields.Float(string="Poids en kg")
    support_expedition = fields.Boolean(string="Support d'expédition", default=False)



    @api.onchange('longueur','largeur','hauteur')
    def _onchange_volume(self):
        if self.longueur and self.largeur and self.hauteur:
            self.volume = (self.longueur * self.largeur * self.hauteur) / 1000000 
        else:
            self.volume = 0    
