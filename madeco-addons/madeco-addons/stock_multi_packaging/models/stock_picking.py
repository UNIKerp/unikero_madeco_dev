# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"


    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        auto_print_enable = any(self.mapped('picking_type_id.auto_print_enable'))
        report = self[0].picking_type_id.report_id

        if (res and isinstance(res, bool)) and (auto_print_enable and report):
            report_action = report.report_action(self)
            report_action['close_on_report_download'] = True

            return report_action
        
        return res


    def _pre_put_in_pack_hook(self, move_line_ids):

        pickings = move_line_ids.mapped('picking_id')
        picking = pickings[0]

        if len(pickings) > 1:
            return super(StockPicking, self)._pre_put_in_pack_hook(move_line_ids)
        
        if not picking.picking_type_id.choose_package_enable:
            return super(StockPicking, self)._pre_put_in_pack_hook(move_line_ids)

        return picking._choose_package_type(move_line_ids)


    def _choose_package_type(self, move_line_ids):
        view_id = self.env.ref('stock_multi_packaging.choose_type_package_view_form').id
        vals = {
            'move_line_ids': [(6, 0, move_line_ids.ids)],
            'picking_id': self.id,
        }

        # if self.package_level_ids_details:
        #     packages = self.package_level_ids_details.filtered(lambda rec: rec.state == 'assigned' and not rec.is_done)
        #     # .mapped('package_id')
        #     vals.update({
        #         'package_level': True,
        #         'package_ids': [(6, 0, packages.ids)],
        #     })
        
        wiz = self.env['choose.type.package'].create(vals)

        return {
            'name': _('Choose a package type'),
            'view_mode': 'form',
            'res_model': 'choose.type.package',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'type': 'ir.actions.act_window',
            'res_id': wiz.id,
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
            }
        }