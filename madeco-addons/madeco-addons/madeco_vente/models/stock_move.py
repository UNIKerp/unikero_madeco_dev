# -*- coding: utf-8 -*-
"""
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
    Default Docstring
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = "stock.move"

    description_ligne_vente = fields.Text(string='Description vente', compute="_compute_description_ligne_vente")

    def _compute_description_ligne_vente(self):
        for rec in self:
            # get the last move of the process, because the last picking is the one linked to the sale
            last_move = rec

            while last_move.move_dest_ids:
                last_move = last_move.move_dest_ids[0]

            if rec.product_id.typologie_article in ["A2", "A3"] and last_move.sale_line_id:
                rec.description_ligne_vente = last_move.sale_line_id.name
            else:
                rec.description_ligne_vente = rec.product_id.name
