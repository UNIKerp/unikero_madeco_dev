# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)
from mako.exceptions import RichTraceback
import petl as etl

class apik_etl(models.Model):
	_name = 'apik.etl'
	
	name = fields.Char('Nom')
	code = fields.Char('Code')
	extracts = fields.One2many('apik.etl.extract','etl_id',string="Extracts")
	transformations = fields.One2many('apik.etl.transformation','etl_id',string="Transformations")
	loads = fields.One2many('apik.etl.load','etl_id',string='Loads')
	code_etl = fields.Text('Code ETL')
	
	def compile(self):
		logger.info("compile")
		code_etl = ""
		for e in self.extracts:
			e.compile()
			code_etl += e.code_etl
			
		for t in self.transformations:
			t.compile()
			code_etl += t.code_etl
			
		for l in self.loads:
			l.compile()
			code_etl += l.code_etl
			
		self.code_etl = code_etl
	
	
	def execute(self):
		logger.info("execute")
		self.compile()
		logger.info(self.code_etl)
		try:
			exec(self.code_etl)
			
		except Exception as e:
			traceback = RichTraceback()
			for (filename, lineno, function, line) in traceback.traceback:
				logger.info("File %s, line %s, in %s" % (filename, lineno, function))
				logger.info(line, "\n")
			logger.info("%s: %s" % (str(traceback.error.__class__.__name__), traceback.error)) 
		return False