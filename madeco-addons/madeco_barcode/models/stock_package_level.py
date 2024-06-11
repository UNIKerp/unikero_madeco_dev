# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPackageLevel(models.Model):
    _inherit = "stock.package_level"

    state = fields.Selection(selection_add=[('palletized', 'Palletized')])

    @api.depends('move_ids', 'move_ids.state', 'move_line_ids', 'move_line_ids.state')
    def _compute_state(self):
        super(StockPackageLevel, self)._compute_state()

        for package_level in self:
            # when the picking is validated
            if package_level.picking_id.picking_type_id.step == 'pallet' and package_level.picking_id.state == 'done':
                origin_packages = package_level.picking_id.move_line_ids.mapped('package_id')
                result_packages = package_level.picking_id.move_line_ids.mapped('result_package_id')

                # change state of package level
                if package_level.package_id.id in origin_packages.ids:
                    package_level.write({'state': 'palletized'})

                if package_level.package_id.id in result_packages.ids:
                    package_level.write({'state': 'done'})
