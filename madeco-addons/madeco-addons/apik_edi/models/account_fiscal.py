# -*- coding: utf-8 -*-

import json
from datetime import datetime
from odoo.tools import float_compare, float_round
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import unidecode
import logging
logger = logging.getLogger(__name__)

class AccountFiscalPosition(models.Model):
    _name = 'account.fiscal.position'
    _inherit = 'account.fiscal.position'   
    
    regime_tva_edi = fields.Selection([('1', "VAT (no exoneration) / TVA (pas d'éxonération)"),('2', 'Export'),('3', ' Exoneration / Exonération')], 
        required=True, default='1',string="Régime de TVA EDI", copy=False)

        


