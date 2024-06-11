# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class Warehouse(models.Model):
    _inherit = "stock.warehouse"
    
    article_ids = fields.One2many('stock.warehouse.product', 'warehouse_id', 'Product lines', copy=True)
    blocage_vente = fields.Boolean(string="Ne pas afficher sur les ventes", default=False) 









    