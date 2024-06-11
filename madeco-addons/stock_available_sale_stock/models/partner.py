# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import logging
logger = logging.getLogger(__name__)


class Partner(models.Model):
    _name = "res.partner"
    _inherit = 'res.partner'
    
    subcontracting_deadlines_ids = fields.One2many('partner.subcontracting.deadlines', 'partner_id', 'Subcontracting deadlines', copy=True)
