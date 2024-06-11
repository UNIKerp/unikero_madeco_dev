# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare

import logging

_logger = logging.getLogger(__name__)


class ChooseBatchPackage(models.TransientModel):
    _inherit = 'choose.batch.package'


    def action_put_in_pack(self):
        package = super(ChooseBatchPackage, self).action_put_in_pack()

        # pickings = self.picking_ids.filtered(lambda x: x.picking_type_id.step == 'pallet')        
        pickings = self.picking_ids
        
        if pickings:
            # TODO: Need to check all picking types ?
            # bool(filter(lambda x: x == 'step', pickings.mapped('picking_type_id.step')))
            return package.action_print_sscc_labels()            

        return package


