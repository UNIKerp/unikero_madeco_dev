# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)


class res_users(models.Model):
	_name = 'res.users'
	_inherit = 'res.users'
	
	apik_data_select = fields.Boolean('Apik Data Select')