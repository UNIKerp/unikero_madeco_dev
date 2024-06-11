# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare

import logging

_logger = logging.getLogger(__name__)


class ChooseTypePackage(models.TransientModel):
    _inherit = 'choose.type.package'


    def action_put_in_pack(self):
        package = super(ChooseTypePackage, self).action_put_in_pack()

        return package.action_print_sscc_labels()


