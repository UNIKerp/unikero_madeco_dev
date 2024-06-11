# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    default_product_packaging = fields.Many2one(comodel_name='product.packaging', domain=[('product_id', '=', False)])
    product_packaging_ids = fields.Many2many('product.packaging', string="Authorized packagings")
    repackaging_enable = fields.Boolean(string="Repackaging", help="Allow repackaging in batch transfers", default=False)
    choose_package_enable = fields.Boolean(string="Package type", help="Allow to choose package type", default=False)
    step = fields.Selection(string="Step", selection=[
        ('pick', 'Picking'), 
        ('pack', 'Packing'), 
        ('recut', 'Recut'), 
        ('pallet', 'Palletizing'), 
        ('ship', 'Shipping')])
    barcode_view_enable = fields.Boolean(string="Allow to operate in barcode app.", default=True)
    auto_print_enable = fields.Boolean(string="Print report upon validation")
    auto_print_label_enable = fields.Boolean(string="Print label upon packaging")
    report_label_id = fields.Many2one('ir.actions.report', string="Report label")
    report_id = fields.Many2one('ir.actions.report', string="Report")

