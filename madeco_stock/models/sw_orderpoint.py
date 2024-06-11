# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)


from odoo import _, api, fields, models
from odoo.tools.float_utils import float_is_zero


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'
    
    strategie_location_id = fields.Many2one('stock.location',string='Stratégie de rangement', compute="_compute_strategie_location", store=True)
    
    @api.depends('product_id', 'location_id', 'route_id', 'write_date')
    def _compute_strategie_location(self):
        for swo in self:
            logger.info("=============================")
            sprs = self.env['stock.putaway.rule'].search([('company_id','=',swo.company_id.id),('location_in_id','=',swo.location_id.id),('product_id','=',swo.product_id.id)])
            if sprs:
                for spr in sprs:
                    if spr.location_in_id.id == swo.location_id.id: 
                        if spr.location_out_id:
                            swo.strategie_location_id = spr.location_out_id.id
                            break 
                        else:
                            swo.strategie_location_id = spr.location_in_id.id               
            else:
                swo.strategie_location_id = swo.location_id.id

            logger.info(swo.product_id.name)
            logger.info(swo.strategie_location_id.name)
            logger.info("=============================") 

    def maj_strategie_de_rangement_dans_reappro(self):
        self._context["active_model"] == "stock.warehouse.orderpoint"
        swos = self.env["stock.warehouse.orderpoint"].browse(self._context["active_ids"])
        for swo in swos:
            logger.info("============ MAJ ============")
            sprs = self.env['stock.putaway.rule'].search([('company_id','=',swo.company_id.id),('location_in_id','=',swo.location_id.id),('product_id','=',swo.product_id.id)])
            if sprs:
                for spr in sprs:
                    if spr.location_in_id.id == swo.location_id.id: 
                        if spr.location_out_id:
                            swo.strategie_location_id = spr.location_out_id.id
                            break 
                        else:
                            swo.strategie_location_id = spr.location_in_id.id               
            else:
                swo.strategie_location_id = swo.location_id.id

            logger.info(swo.product_id.name)
            logger.info(swo.strategie_location_id.name)
            logger.info("=============================")         