# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)

class apik_etl_extract(models.Model):
	_name = 'apik.etl.extract'
	
	@api.onchange('source','name')
	def onchange_source_name(self):
		code_etl = ""
		if self.source and self.name:
			self.ss_type.compile(self.source)
			if self.ss_type and self.ss_type.code_etl:
				code_etl += self.ss_type.code_etl
			self.code_etl = code_etl + "\n"
			logger.info(code_etl)
	
	
	def compile(self):
		for e in self:
			e.onchange_source_name()
	
	
	name = fields.Char('Nom')
	etl_id = fields.Many2one('apik.etl',string='ETL')
	source = fields.Many2one('apik.etl.source',string="Source",required=True)
	ttype = fields.Selection(related='source.ttype',string='Type')
	ss_type = fields.Many2one('apik.etl.source.ss_type',related='source.ss_type',string='Sous Type')
	code_etl = fields.Text('Code ETL',default="import petl as etl")