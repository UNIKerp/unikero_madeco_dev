# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime
from odoo.exceptions import AccessError, UserError, ValidationError

import logging
logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = 'sale.order'
    
    partner_id = fields.Many2one(domain="['|', ('company_id', '=', False), ('company_id', '=', company_id),('client_web','=',False)]",)
    partner_invoice_id = fields.Many2one(domain="['|', ('company_id', '=', False), ('company_id', '=', company_id),('client_web','=',False)]",)
    partner_shipping_id = fields.Many2one(domain="['|', ('company_id', '=', False), ('company_id', '=', company_id),('client_web','=',False)]",)