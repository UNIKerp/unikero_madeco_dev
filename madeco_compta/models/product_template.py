# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime
from odoo.exceptions import AccessError, UserError, ValidationError

import logging
logger = logging.getLogger(__name__)


class PorductTemplate(models.Model):
    _name = "product.template"
    _inherit = 'product.template'
    
    surface = fields.Float(string='Surface en m2')
      

