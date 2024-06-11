# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import logging

logger = logging.getLogger(__name__)

class SaleOrderWarning(models.TransientModel):
    _name = 'sale.order.warning'
    _description = "Sales Order Warning"

    order_id = fields.Many2one('sale.order', string='Sale Order', required=True, ondelete='cascade')
    error_warning = fields.Char(string='Warning Erreur', compute='_compute_error_warning')

    @api.depends('order_id')
    def _compute_error_warning(self):
        for wizard in self:
            wizard.error_warning = wizard.order_id.error_warning

    def action_confirm_abandon(self):
        return False
