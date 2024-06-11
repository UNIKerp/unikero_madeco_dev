# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class res_company(models.Model):
    _inherit = 'res.company'
    
    delai_debut_disponibilite = fields.Integer(string='Availability start time (days)',default=0)  
    delai_dispo_fournisseur = fields.Integer(string='Deadline for availability of components from supplier (days)',default=0)  