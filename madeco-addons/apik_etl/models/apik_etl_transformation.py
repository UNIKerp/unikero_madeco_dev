# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)


class apik_etl_transformation(models.Model):
	_name = 'apik.etl.transformation'
	
	name = fields.Char('Nom')
	etl_id = fields.Many2one('apik.etl',string='ETL')
	code_etl = fields.Text('Code ETL')
	
	@api.onchange('name')
	def onchange_data(self):
		code_etl = ""
		
		self.code_etl = "" + "\n"
	
	
	def compile(self):
		for t in self:
			t.onchange_data()