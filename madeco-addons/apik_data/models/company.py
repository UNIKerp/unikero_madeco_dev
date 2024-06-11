# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)


class res_company(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'
    
    apik_data_user = fields.Char('User')
    apik_data_password = fields.Char('Mot de passe')
  