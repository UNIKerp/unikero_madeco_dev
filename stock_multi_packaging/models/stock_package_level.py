# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class StockPackageLevel(models.Model):
    _inherit = "stock.package_level"


    def name_get(self):
        return [(record.id, record.package_id.display_name) for record in self]

