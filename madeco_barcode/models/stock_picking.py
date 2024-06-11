# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_preparation_report_printed = fields.Boolean(
        string="BP printed", default=False, readonly=True)
    intrastat_transport_id = fields.Many2one(
        string="Transporteur", comodel_name="intrastat.transport_mode")
    rule_id = fields.Many2one(
        string="Rule", comodel_name="stock.rule", compute="_compute_rule_id")
    print_delivery_type = fields.Selection(string="Delivery print", selection=[(
        'local', "Local"), ('chain', "Chain")], compute="_compute_print_delivery_type", inverse="_set_print_delivery_type")
    product_rate = fields.Float(string="Product rate", default = 0) # compute="_compute_product_rate")
    product_rate_old = fields.Float(string="Product rate old", compute="_compute_product_rate_old")
    nb_products_order = fields.Float(string="Nb products order", compute="_compute_nb_products_order")
    nb_lines_order = fields.Float(string="Nb lines order", compute="_compute_nb_lines_order")
    availability_rate = fields.Integer(string="Availability rate", default = 0) 

    def _compute_print_delivery_type(self):
        for rec in self:
            rec.print_delivery_type = rec.sale_id.print_delivery_type if rec.sale_id else 'local'

    def _set_print_delivery_type(self):
        for rec in self:
            if rec.sale_id:
                rec.sale_id.print_delivery_type = rec.print_delivery_type

    def _compute_rule_id(self):
        for rec in self:
            # there SHOULD be only one rule
            rules = rec.move_lines.mapped('rule_id')
            rec.rule_id = rules[0].id if rules else False

    def set_preparation_report_printed(self):
        # called from the report
        self.filtered(lambda rec: rec.picking_type_id.step =='pick').write({'is_preparation_report_printed': True})
        return True    

    def _check_products_packaged(self):
        self.ensure_one()
        if self.picking_type_id.step == 'pack':
            for line in self.move_line_ids:
                if not line.result_package_id:
                    return False
        return True

    def get_barcode_view_state(self):
        pickings = super(StockPicking, self).get_barcode_view_state()        
        for picking in pickings:
            # picking['actionReportDeliverySlipId'] = self.env.ref('stock.action_report_delivery').id

            picking['actionReportSsccId'] = self.env.ref('madeco_stock_sscc.action_report_sscc_picking_label').id
        
        # logger.warning(pickings)
        return pickings

    def button_validate(self):
        for rec in self:
            # check that all the products are packaged
            if not rec._check_products_packaged():
                raise UserError(_("Unpacked products"))
        res = super(StockPicking, self).button_validate()
        for rec in self:
            rec.action_update_packages()
            rec.action_update_packages_weight()
        return res

    def action_print_recut(self):
        pickings = self.filtered(lambda x: x.picking_type_id.step == 'recut')
        report = self.env.ref('madeco_barcode.action_report_stock_picking_recut')
        if pickings:
            action = report.report_action(self.ids)
            action['print_report_name'] = 'Recut {}'.format(pickings[0].name) if len(pickings) == 1 else 'Recut',
            logger.error(action)
            return action
            # return {
            #     'type': 'ir.actions.report',
            #     'model': 'stock.picking',
            #     'report_type': 'qweb-pdf',
            #     'paperformat_id': self.env.ref('madeco_barcode.paperformat_stock_picking_recut').id,
            #     'report_name': 'madeco_barcode.report_stock_picking_recut',
            #     'print_report_name': 'Recut {}'.format(pickings[0].name) if len(pickings) == 1 else 'Recut',
            #     'context': {
            #         'active_ids': self.ids
            #     }
            # }
        else:
            return {
                "type": "ir.actions.do_nothing"
            }

    def _get_report_filename(self, default=False):
        self.ensure_one()
        if default:
            return 'Delivery Slip - %s - %s' % (self.partner_id.name or '', self.name)        
        name = self.name.split('/')[-1] or "XXXX*"
        print_type = self.print_delivery_type
        return 'BL-{}-{}'.format(print_type.upper(), name)


    def action_print_sscc(self):
        pickings = self.filtered(lambda x: x.picking_type_id.step == 'ship')
        return pickings.action_print_sscc_labels()

    def action_print_delivery(self):
        report = self.env.ref('stock.action_report_delivery').report_action(self)
        return report
        # if self and ((self[0].print_delivery_type == 'local' and self[0].rule_id.is_print_delivery_local) or (self[0].print_delivery_type == 'chain' and self[0].rule_id.is_print_delivery_chain)) and self[0]._check_products_packaged():
        #     return {
        #         'type': 'ir.actions.report',
        #         'model': 'stock.picking',
        #         'report_type': 'qweb-pdf',
        #         'report_name': 'stock.report_deliveryslip',
        #         # 'print_report_name': 'BL-LOCAL-{}*'.format(self[0].origin if self[0].origin else 'XXXX') if self[0].rule_id and self[0].rule_id.is_print_delivery_local else 'BL-CHAINE-{}*'.format(self[0].origin if self[0].origin else 'XXXX'),
        #         'print_report_name': self[0]._get_report_filename(),
        #         'context': {
        #                 'active_ids': self.ids
        #         }
        #     }
        # else:
        #     return {
        #         "type": "ir.actions.do_nothing"
        #     }


    def action_update_packages(self):
        self.ensure_one()
        if self.picking_type_id.step == 'pallet':
            result_packages = self.move_line_ids.mapped('result_package_id')
            # set origin packages in quants
            for package_level in self.package_level_ids_details:
                # move lines to use to get the origin packages
                move_lines = package_level.move_line_ids
                move_lines_done = []
                for quant in package_level.package_id.quant_ids:
                    # search the matching move line
                    matching_move_lines = move_lines.filtered(lambda x:
                                                              x.id not in move_lines_done and
                                                              x.product_id == quant.product_id and
                                                              x.qty_done == quant.quantity and
                                                              x.lot_id == quant.lot_id and
                                                              x.location_dest_id == quant.location_id
                                                              )
                    if matching_move_lines:
                        # set the origin package in the quant
                        quant.write(
                            {'package_origin_ids': [(4, matching_move_lines[0].package_id.id, False)]})
                        # recompute weight of the origin package
                        matching_move_lines[0].package_id._compute_weight()
                        # avoid the use of a move line twice
                        move_lines_done.append(matching_move_lines[0].id)
                    else:
                        # if no move line found, quantities could have been joined in the quant
                        # for example : one line with 25 in the quant and two move lines with 11 and 14
                        # so we add the two packages as origin
                        # search the matching move lines to get their total quantity
                        matching_move_lines = move_lines.filtered(lambda x:
                                                                  x.id not in move_lines_done and
                                                                  x.product_id == quant.product_id and
                                                                  x.lot_id == quant.lot_id and
                                                                  x.location_dest_id == quant.location_id
                                                                  )
                        if sum([ml.qty_done for ml in matching_move_lines]) == quant.quantity:
                            # set the origin packages in the quant
                            quant.write({'package_origin_ids': [
                                        (4, ml.package_id.id, False) for ml in matching_move_lines]})
                            # recompute weight of the origin packages
                            matching_move_lines.mapped(
                                'package_id')._compute_weight()
                            # avoid the use of move lines twice
                            move_lines_done.extend(matching_move_lines.ids)

    def action_update_packages_weight(self):
        self.ensure_one()
        # compute the weight of the packages, that will be kept even when the palletizing will be done
        if self.picking_type_id.step == 'pack':
            self.move_line_ids.mapped(
                'result_package_id')._update_palletizing_weight()
        # compute the final weight of the pallets
        elif self.picking_type_id.step == 'pallet':
            self.package_level_ids_details.filtered(lambda x: x.state == 'done').mapped(
                'package_id')._update_palletizing_weight()

    @api.model
    def _get_move_line_ids_fields_to_read(self):
        res = super(StockPicking, self)._get_move_line_ids_fields_to_read()
        res.append('description_ligne_vente')
        return res

    def _compute_product_rate(self):
        for picking in self:
            total_qty = 0
            total_res = 0
            for move in picking.move_ids_without_package: 
                total_qty += move.product_uom_qty
                total_res += move.reserved_availability              
            if total_qty > 0:
                picking.product_rate = (total_res / total_qty) * 100
            else:
                picking.product_rate = 0 

    def _compute_availability_rate(self):
        for picking in self:
            total_cde = 0
            total_res = 0
            for move in picking.move_ids_without_package: 
                total_cde += move.product_uom_qty
                total_res += move.reserved_availability              
            if total_cde > 0:
                picking.availability_rate = (total_res / total_cde) * 100
            else:
                picking.availability_rate = 0             

    def action_assign(self):
        resultat = super(StockPicking, self).action_assign()
        if resultat:
            self._compute_product_rate()
            self._compute_availability_rate()
        return True

    def do_unreserve(self):
        resultat = super(StockPicking, self).do_unreserve()
        self._compute_product_rate()
        self._compute_availability_rate()

    def _compute_nb_products_order(self):
        for picking in self:
            total_qty = 0
            for move in picking.move_ids_without_package: 
                total_qty += move.product_uom_qty
            picking.nb_products_order = total_qty         

    def _compute_nb_lines_order(self):
        for picking in self:
            if picking.sale_id: 
                picking.nb_lines_order = len(picking.sale_id.order_line) 
            else:
                picking.nb_lines_order = 0    

    def _compute_product_rate_old(self):
        for picking in self:
            total_qty = 0
            for move in picking.move_line_ids_without_package: 
                if move.preparation_report_line_displaying(): 
                    total_qty += move.product_uom_qty
            if picking.sale_id:
                nb_products_order = 0 
                for line in picking.sale_id.order_line:
                    nb_products_order += line.product_uom_qty
            else:
                nb_products_order = 0
            if nb_products_order > 0:
                picking.product_rate_old = (total_qty / nb_products_order) * 100
            else:
                picking.product_rate_old = 0                

    def do_verif_dispo(self):
        self.action_assign()
        # On les enlèves car déjà lancé dans l'action_assign
        #self._compute_product_rate()
        #self._compute_availability_rate()
