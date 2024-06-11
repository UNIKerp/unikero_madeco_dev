# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockRule(models.Model):
    _inherit = "stock.rule"

    is_print_delivery_local = fields.Boolean(string="Delivery print local", default=False)
    is_print_delivery_chain = fields.Boolean(string="Delivery print chain", default=False)

    # only one print_delivery boolean can be checked at the same time
    @api.onchange('is_print_delivery_local')
    def _onchange_is_print_delivery_local(self):
        if self.is_print_delivery_local:
            self.update({'is_print_delivery_chain': False})

    @api.onchange('is_print_delivery_chain')
    def _onchange_is_print_delivery_chain(self):
        if self.is_print_delivery_chain:
            self.update({'is_print_delivery_local': False})
