# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    source_package_type_id = fields.Many2one(string="Package Type", related='package_id.packaging_id')
    dest_package_type_id = fields.Many2one(string="Package Type", related='result_package_id.packaging_id')
