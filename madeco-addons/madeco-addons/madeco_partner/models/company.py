# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class res_company(models.Model):
    _inherit = 'res.company'
    
    champ_adresse_fac = fields.Many2one('ir.model.fields', string="Champ adresse de facturation de commande")
    champ_adresse_liv = fields.Many2one('ir.model.fields', string="Champ adresse de livraison de commande")
    
