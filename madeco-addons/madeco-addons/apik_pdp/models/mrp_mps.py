# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)


class mrp_production_schedule_multi(models.Model):
	_name = 'mrp.production.schedule.multi'


	@api.model
	def _default_warehouse_id(self):
		return self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
		

	product_ids = fields.Many2many('product.product', string='Products', required=True)
	warehouse_id = fields.Many2one('stock.warehouse', 'Production Warehouse',
	required=True, default=lambda self: self._default_warehouse_id())
	
	forecast_target_qty = fields.Float('Safety Stock Target')
	min_to_replenish_qty = fields.Float('Minimum to Replenish')
	max_to_replenish_qty = fields.Float('Maximum to Replenish', default=1000)
	
	@api.model
	def create(self,vals):
		res = super().create(vals)
		
		for product in res.product_ids:
			logger.info(product)
			logger.info(res.warehouse_id)
			value = {
				"product_id": product.id,
				"warehouse_id": res.warehouse_id.id,
				"forecast_target_qty": res.forecast_target_qty,
				"min_to_replenish_qty": res.min_to_replenish_qty,
				"max_to_replenish_qty": res.max_to_replenish_qty,
			}
			self.env['mrp.production.schedule'].create(value)
		
		# pour chaque product on crée un mrp.production.schedule
		logger.info("create")
		
		return res
		
	def write(self,vals):
		res = super().write(vals)
		
		logger.info("write")
		
		return res