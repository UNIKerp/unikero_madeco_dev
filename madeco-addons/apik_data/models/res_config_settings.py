# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)


class res_config_settings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    company_id = fields.Many2one('res.company','Société')
    apik_data_user = fields.Char('User',related='company_id.apik_data_user', readonly=False)
    apik_data_password = fields.Char('Mot de passe',related='company_id.apik_data_password', readonly=False)
    
  