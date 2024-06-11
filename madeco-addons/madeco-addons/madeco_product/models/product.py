# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime
from odoo.exceptions import AccessError, UserError, ValidationError

import logging
logger = logging.getLogger(__name__)


class PorductTemplate(models.Model):
    _name = "product.template"
    _inherit = 'product.template'
    
    master_id = fields.Many2one('product.template',string='Article Master')
    typologie_article = fields.Selection([
        ('A1', 'Article standard'),
        ('A2', 'Article à recouper'),
        ('A3', 'Article sur mesure'),
        ('A4', 'Dropship'),],
        string="Typologie d'article", default='A1')
    statut_article = fields.Selection([
        ('tou', ' '),        
        ('avs', 'AVS'),
        ('nap', 'NAP'),
        ('blo', 'BLO'),
        ],
        string="Statut d'article", default='tou')   

