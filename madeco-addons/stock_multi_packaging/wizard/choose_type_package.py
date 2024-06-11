# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class ChooseTypePackage(models.TransientModel):
    _name = 'choose.type.package'
    _description = 'Choose package'


    show_operations_details = fields.Boolean(default=True)
    package_id = fields.Many2one('stock.quant.package', 'Package')
    picking_id = fields.Many2one('stock.picking')
    
    package_level = fields.Boolean(default=False, compute='_compute_package_level')
    package_level_ids = fields.One2many('stock.package_level', compute='_compute_package_level')
    package_ids = fields.Many2many('stock.package_level')

    picking_type_id = fields.Many2one(related='picking_id.picking_type_id')
    move_line_ids = fields.Many2many('stock.move.line')
    allowed_packaging_ids = fields.Many2many(
        comodel_name="product.packaging",
        compute="_compute_allowed_packaging",
        string="Allowed packaging",
    )    
    packaging_id = fields.Many2one('product.packaging', 'Packaging', check_company=True)
    # shipping_weight = fields.Float('Shipping Weight', compute='_compute_move_lines')
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name')
    company_id = fields.Many2one(related='picking_id.company_id')


    @api.depends("picking_id")
    def _compute_package_level(self):
        for record in self:
            record.package_level = record.picking_id.picking_type_id.show_entire_packs
            record.package_level_ids = record.picking_id.package_level_ids_details.filtered(lambda rec: rec.state == 'assigned' and not rec.is_done)


    @api.depends("picking_id")
    def _compute_allowed_packaging(self):
        for record in self:
            record.allowed_packaging_ids = record.picking_type_id.product_packaging_ids or []


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
            return {}

        if self.package_level and self.package_ids:
            # filter on packages
            packages = self.package_ids.mapped('package_id')
            move_line_ids = self.picking_id.move_line_ids
            move_line_ids = move_line_ids.filtered(lambda ml: ml.package_id.id in packages.ids)
            # _logger.warning(move_line_ids)
        else:
            move_line_ids = self.move_line_ids

        package = self.picking_id._put_in_pack(move_line_ids)
        package.packaging_id = self.packaging_id

        auto_print = self.picking_type_id.auto_print_label_enable
        report = self.picking_type_id.report_label_id

        if auto_print and report:
            report_action = report.report_action(package)
            report_action['close_on_report_download'] = True
            return report_action

        return package


