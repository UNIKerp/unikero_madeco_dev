# -*- coding: utf-8 -*-
"""
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
    Default Docstring
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'


    madeco_transport_id = fields.Many2one('madeco.transport', string="Mode of transport")    
