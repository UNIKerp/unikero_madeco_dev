# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"


    weight = fields.Float(compute='_compute_weight')

    @api.depends('quant_ids')
    def _compute_weight(self):
        for record in self:
            record.weight = sum([quant.quantity * quant.product_id.weight for quant in record.quant_ids])
