# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)


class apik_etl_load(models.Model):
	_name = 'apik.etl.load'
	
	name = fields.Char('Nom')
	etl_id = fields.Many2one('apik.etl',string='ETL')
	code_etl = fields.Text('Code ETL')
	
	destination = fields.Many2one('apik.etl.destination',string="Destination",required=True)
	ttype = fields.Selection(related='destination.ttype',string='Type')
	ss_type = fields.Many2one('apik.etl.destination.ss_type',related='destination.ss_type',string='Sous Type')
	
	@api.onchange('destination','name')
	def onchange_destination_name(self):
		code_etl = ""
		if self.destination and self.name:
			self.ss_type.compile(self.destination)
			if self.ss_type and self.ss_type.code_etl:
				code_etl += self.ss_type.code_etl
			self.code_etl = code_etl + "\n"
			logger.info(code_etl)
	
	
	def compile(self):
		for e in self:
			e.onchange_destination_name()