# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

def _get_weight(move_line):
    return move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id) * move_line.product_id.weight


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"


    def _get_estimated_weight(self):
        # return round(sum([record.product_uom_id._compute_quantity(record.qty_done, record.product_id.uom_id) * record.product_id.weight for record in self]), 2)    
        return round(sum(map(_get_weight, self)), 2)    