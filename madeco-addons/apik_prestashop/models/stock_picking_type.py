# -*- coding: utf-8 -*-

#import json
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime, timedelta
from tempfile import TemporaryFile
import base64
import io
import logging
logger = logging.getLogger(__name__)


class PickingType(models.Model):
    _inherit = 'stock.picking.type' 

    livweb_edi = fields.Boolean(string="Envoi LIVWEB EDI", default=False)

 