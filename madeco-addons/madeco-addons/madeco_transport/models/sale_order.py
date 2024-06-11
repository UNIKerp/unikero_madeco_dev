# -*- coding: utf-8 -*-
"""
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
    Default Docstring
"""
import logging
import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta

from functools import partial
from itertools import groupby

from odoo.addons.apik_calendar.models import apik_calendar

logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'  

    madeco_transport_id = fields.Many2one(comodel_name="madeco.transport", string="Mode of transport",
        domain="[('company_id', '=', company_id)]",)

    # 
    # On regarde si adresse de livraison est XDOCK
    # 
    @api.onchange("partner_shipping_id")
    def onchange_partner_shipping_id_xdock_entete_transport(self):
        for sale in self:
            sale.xdock = False
            if sale.partner_shipping_id.xdock:
                sale.xdock = True
            if sale.partner_shipping_id.madeco_transport_id:
                sale.madeco_transport_id = sale.partner_shipping_id.madeco_transport_id.id    

    def _prepare_invoice_transport(self):
        """Copy destination country to invoice"""
        vals = super()._prepare_invoice()
        if self.madeco_transport_id:
            vals["madeco_transport_id"] = self.madeco_transport_id.id        
        return vals
              
