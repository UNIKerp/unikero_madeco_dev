# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"


    # def action_print_sscc(self):
    #     batches = self.filtered(lambda x: x.picking_type_id.step == 'ship')
    #     return batches.action_print_sscc_labels()


    # def action_print_recut(self):
    #     return self.picking_ids.action_print_recut()


    # def action_print_delivery(self):
    #     return self.picking_ids.action_print_delivery()
