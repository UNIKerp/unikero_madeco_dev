# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import logging
logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = 'product.template'
    
    art_sst_no_stock = fields.Boolean(string="Article sous-traité sans stock chez le sous-traitant", default=False) 
