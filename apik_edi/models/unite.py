# -*- coding: utf-8 -*-

import json
from datetime import datetime
from odoo.tools import float_compare, float_round
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import unidecode
import logging
logger = logging.getLogger(__name__)


class Unite(models.Model):
    _name = 'uom.uom'
    _inherit = 'uom.uom'    
    
    unite_edi = fields.Char(string="Unité EDI")
    
        


