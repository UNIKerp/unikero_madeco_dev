# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"


    def action_print_sscc_labels(self, close=True):
        report = self.env.ref('madeco_stock_sscc.action_report_sscc_picking_label').report_action(self)
        report['close_on_report_download'] = close

        return report


    def _get_report_sscc_prefix(self):
        if 'pack' in self.mapped('picking_type_id.step'):
            report_name = 'SSCC-COLIS-LOCAL-{}'
        else:
            report_name = 'SSCC-PALETTE-CHAINE-{}'
        
        return report_name
    

    def _get_report_sscc_filename(self):
        packages = self.move_line_ids.mapped('result_package_id').sorted('create_date', True)
        # packages = packages.filtered(lambda x: not x.is_sscc_report_printed)
        report_name = self._get_report_sscc_prefix()
        
        return report_name.format(packages._get_short_name() if packages else 'XXX')


    def _get_sscc_packages(self):
        packages = self.move_line_ids.mapped('result_package_id')
        ctx = {
            'pickings': self.ids,
            'move_lines': self.move_line_ids.ids,
        }
        return packages.with_context(**self.env.context, **ctx)._get_sscc_packages()
