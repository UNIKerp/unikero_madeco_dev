# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    print_delivery_type = fields.Selection(string="Delivery print", selection=[('local', "Local"), ('chain', "Chain")], default="local")
