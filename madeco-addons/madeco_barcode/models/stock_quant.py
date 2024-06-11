# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = "stock.quant"

    package_origin_ids = fields.Many2many(string="Origin packages", comodel_name="stock.quant.package", readonly=True)
