# -*- coding: utf-8 -*-
"""
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
    Default Docstring
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = "stock.move.line"

    description_ligne_vente = fields.Text(string='Description vente', compute='_compute_description_ligne_vente')

    def _compute_description_ligne_vente(self):
        for rec in self:
            rec.description_ligne_vente = rec.move_id.description_ligne_vente
