# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class res_company(models.Model):
    _inherit = 'res.company'
    
    num_fourn_dzb = fields.Char(string="DZB Bank Supplier Number", required=True, readonly=False)
    taux_escompte = fields.Float(string="Discount rate (in %)", required=True, readonly=False)
    product_escompte_id = fields.Many2one('product.product', string='Discount Item Code',  ondelete='restrict')  
    surface_unit_id = fields.Many2one("intrastat.unit",string="Surface unit")	

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    surface_unit_id = fields.Many2one(related="company_id.surface_unit_id", readonly=False)    