# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime
from odoo.exceptions import AccessError, UserError, ValidationError

import logging
logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = 'sale.order'
        
    warehouse_id = fields.Many2one(string="Assembly center", domain="[('blocage_vente', '=', False)]")
    planning_validated = fields.Boolean(string="Planning validated", default=False) 

    def action_recalcul_delai(self):
        for sale in self:
            for line in sale.order_line:
                line._compute_display_component_time()           

    
            
          