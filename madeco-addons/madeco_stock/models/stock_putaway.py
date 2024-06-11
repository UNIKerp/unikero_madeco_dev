# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict, namedtuple

from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, _, api, fields, models, registry
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero, html_escape
from odoo.tools.misc import split_every

logger = logging.getLogger(__name__)


class StockPutawayRule(models.Model):
    _name = 'stock.putaway.rule'
    _inherit = 'stock.putaway.rule'
    
    @api.onchange('location_out_id')
    def _onchange_location_out_custom(self):
        for spr in self:
            swos = self.env['stock.warehouse.orderpoint'].search([('company_id','=',spr.company_id.id),('location_id','=',spr.location_in_id.id),('product_id','=',spr.product_id.id)])
            if swos:
                for swo in swos:
                    if spr.location_in_id.id == swo.location_id.id: 
                        if spr.location_out_id:
                            swo.strategie_location_id = spr.location_out_id.id
                        else:    
                            swo.strategie_location_id = spr.location_in_id.id               

    @api.model
    def create(self, vals):
        res = super(StockPutawayRule, self).create(vals)
        if res:
            for spr in res:
                swos = self.env['stock.warehouse.orderpoint'].search([('company_id','=',spr.company_id.id),('location_id','=',spr.location_in_id.id),('product_id','=',spr.product_id.id)])
                if swos:
                    for swo in swos:
                        if spr.location_in_id.id == swo.location_id.id: 
                            if spr.location_out_id:
                                swo.strategie_location_id = spr.location_out_id.id
                            else:    
                                swo.strategie_location_id = spr.location_in_id.id               
        return res

    def unlink(self):
        for spr in self:
            swos = self.env['stock.warehouse.orderpoint'].search([('company_id','=',spr.company_id.id),('location_id','=',spr.location_in_id.id),('product_id','=',spr.product_id.id)])
            if swos:
                for swo in swos:
                    swo.strategie_location_id = spr.location_in_id.id               
        return super(StockPutawayRule, self).unlink()    
  
