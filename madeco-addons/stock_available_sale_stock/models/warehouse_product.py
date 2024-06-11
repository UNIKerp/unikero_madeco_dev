# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class StockWarehouseProduct(models.Model):

    _name = "stock.warehouse.product"
    _rec_name = 'warehouse_id'
    _description = 'Warehouse Product Time'
    _order = 'warehouse_id, product_tmpl_id, quantity_max ASC, id'

    active = fields.Boolean(default=True)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", ondelete='cascade', required=True, index=True)
    product_tmpl_id = fields.Many2one('product.template', string="Product Template", ondelete='cascade', required=True, index=True)
    quantity_max = fields.Integer(string="Quantity below", required=True)
    time_limit = fields.Integer(string="Time limit", required=True)
    
