# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    support_expedition = fields.Boolean(string="Shipping support", related="packaging_id.support_expedition")
    origin_quant_ids = fields.Many2many(string="Origin quants", comodel_name="stock.quant", compute="_compute_origin_quant_ids")
    palletizing_weight = fields.Float(string="Palletizing weight", readonly=True)  # pallets will have their real weight, and packages will keep their initial value before the palletizing

    def _compute_origin_quant_ids(self):
        for rec in self:
            # get quants where the package is origin
            rec.origin_quant_ids = self.env['stock.quant'].search([]).filtered(lambda x: rec.id in x.package_origin_ids.ids).ids

    def _update_palletizing_weight(self):
        for rec in self:
            rec.palletizing_weight = sum([quant.quantity * quant.product_id.weight for quant in rec.quant_ids])
