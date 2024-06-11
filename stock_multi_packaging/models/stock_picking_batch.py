# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)

class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    # TODO: ???
    # def action_done(self):
    #     res = super(StockPickingBatch, self).action_done()

    #     pickings = self.mapped('picking_ids').filtered(lambda picking: picking.state == 'done')
    #     auto_print_enable = any(pickings.mapped('picking_type_id.auto_print_enable'))

    #     # Print delivery slip
    #     if res and auto_print_enable:
    #         # return pickings.do_print_picking()
    #         return self.env.ref('stock.action_report_delivery').report_action(pickings)
        
    #     return res


    def action_put_in_pack(self):
        """ Action to put move lines with both package source and destination 
        and 'Done' quantities into a new pack (if repackaging is enable...)
        """
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            repackaging = self.picking_ids[0].picking_type_id.repackaging_enable or False
            
            if not repackaging:
                return super(StockPickingBatch, self).action_put_in_pack()

            picking_move_lines = self.move_line_ids

            # Qty done > 0 and source package == dest package (or not dest package)
            move_line_ids = picking_move_lines.filtered(lambda ml:
                float_compare(ml.qty_done, 0.0, precision_rounding=ml.product_uom_id.rounding) > 0
                and ((ml.package_id == ml.result_package_id) or not ml.result_package_id)
            )

            if move_line_ids:
                res = self._choose_package_type(move_line_ids)

                if not res:
                    res = self.picking_ids[0]._pre_put_in_pack_hook(move_line_ids)
                    if not res:
                        res = self.picking_ids[0]._put_in_pack(move_line_ids, True)
                return res
            else:
                raise UserError(_("Please add 'Done' quantities to the batch picking to create a new pack."))


    def _choose_package_type(self, move_line_ids):
        view_id = self.env.ref('stock_multi_packaging.choose_batch_package_view_form').id
        wiz = self.env['choose.batch.package'].create({
            'batch_id': self.id,
            'move_line_ids': [(6, 0, move_line_ids.ids)]
        })

        return {
            'name': _('Choose a package type'),
            'view_mode': 'form',
            'res_model': 'choose.batch.package',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'type': 'ir.actions.act_window',
            'res_id': wiz.id,
            'target': 'new'
        }
           