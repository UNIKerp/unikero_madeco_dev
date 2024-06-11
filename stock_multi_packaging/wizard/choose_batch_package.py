# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare


class ChooseBatchPackage(models.TransientModel):
    _name = 'choose.batch.package'
    _description = 'Choose package in batch mode'

    
    batch_id = fields.Many2one('stock.picking.batch', 'Batch')
    picking_ids = fields.One2many('stock.picking', compute='_compute_packages')
    move_line_ids = fields.Many2many('stock.move.line')
    package_ids = fields.One2many('stock.quant.package', compute='_compute_packages')
    allowed_packaging_ids = fields.Many2many(
        comodel_name="product.packaging",
        compute="_compute_packages",
        string="Allowed packaging",
    )    
    packaging_id = fields.Many2one('product.packaging', 'Packaging', check_company=True)
    shipping_weight = fields.Float('Shipping Weight', compute='_compute_packages')
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name')
    company_id = fields.Many2one(related='batch_id.company_id')
    

    @api.depends('move_line_ids')
    def _compute_packages(self):
        for record in self:
            if not record.move_line_ids:
                record.package_ids = False
                record.shipping_weight = 0.0
                record.picking_ids = False
                continue

            record.picking_ids = record.move_line_ids.mapped('picking_id')
            record.package_ids = record.move_line_ids.mapped('result_package_id')
            record.shipping_weight = sum(record.package_ids.mapped('weight'))
            record.allowed_packaging_ids = record.picking_ids.mapped('picking_type_id.product_packaging_ids') or []


    @api.depends('packaging_id')
    def _compute_weight_uom_name(self):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        for package in self:
            package.weight_uom_name = weight_uom_id.name


    @api.onchange('packaging_id', 'shipping_weight')
    def _onchange_packaging_weight(self):
        if self.packaging_id.max_weight and self.shipping_weight > self.packaging_id.max_weight:
            warning_mess = {
                'title': _('Package too heavy!'),
                'message': _('The weight of your package is higher than the maximum weight authorized for this package type. Please choose another package type.')
            }
            return {'warning': warning_mess}


    def action_put_in_pack(self):
        if not self.packaging_id:
            return False

        package = self.picking_ids[0]._put_in_pack(self.move_line_ids)
        package.packaging_id = self.packaging_id

        auto_print = self.batch_id.picking_type_id.auto_print_label_enable
        report = self.batch_id.picking_type_id.report_label_id

        if auto_print and report:
            report_action = report.report_action(package)
            report_action['close_on_report_download'] = True
            return report_action

        return package


