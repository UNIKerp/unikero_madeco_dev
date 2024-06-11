# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class res_company(models.Model):
    _inherit = 'res.company'
    
    product_rem_global_id = fields.Many2one('product.product', string='Global discount item code',  ondelete='restrict')  
    html_client_pied = fields.Html(string="Texte paiement client", translate=True)
    html_client_dzb_pied = fields.Html(string="Texte paiement client DZB", translate=True)
    html_cgv = fields.Html(string="CGV pied de facture", translate=True)