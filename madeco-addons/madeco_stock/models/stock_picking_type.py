# -*- coding: utf-8 -*-

import logging

from odoo import models, fields

logger = logging.getLogger(__name__)


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    is_packaging_hidden = fields.Boolean("Masquer la mise en colis")
