# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)

class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"


    def action_print_sscc_labels(self, close=True):
        report = self.env.ref('madeco_stock_sscc.action_report_sscc_batch_label').report_action(self)
        report['close_on_report_download'] = close

        return report        


    def _get_report_sscc_filename(self):
        name = (self.picking_type_id.step == 'pack' and 'SSCC-COLIS-LOCAL-{}') or 'SSCC-PALETTE-CHAINE-{}'
        packages = self.move_line_ids.mapped('result_package_id')
        name = name.format(packages._get_short_name() if packages else 'XXXX')

        return name


    def _get_sscc_packages(self):
        packages = self.move_line_ids.mapped('result_package_id')
        ctx = {
            'batch': self.ids,
            'move_lines': self.move_line_ids.ids,
        }
        return packages.with_context(**self.env.context, **ctx)._get_sscc_packages()        
     