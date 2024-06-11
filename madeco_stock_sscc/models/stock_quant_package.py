# -*- coding: utf-8 -*-
from distutils.file_util import move_file
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError


logger = logging.getLogger(__name__)


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    name = fields.Char(default="")  # is generated in the create TODO: check it's unique
    is_sscc_report_printed = fields.Boolean(string="Is SSCC printed", default=False, readonly=True)  # used to print the correct packages from choose_package_type

    def _check_name_sscc(self, vals):
        # get the package type code
        packaging_type_code = 0

        packaging_id = self.env['product.packaging'].search([('id', '=', vals.get('packaging_id', -1))])
        if packaging_id and packaging_id.shipper_package_code:
            try:
                packaging_type_code = int(packaging_id.shipper_package_code)
            except:
                raise UserError(_("The name (SSCC) can't be generated, the package type code must be an integer between 0 and 9"))

        return packaging_type_code

    @api.model
    def create(self, vals):
        if vals.get('package_use', '') == 'disposable':
            # get the package type code
            packaging_type_code = self._check_name_sscc(vals)

            vals.update({
                # get the name
                'name': self._default_name_sscc(packaging_type_code)
            })

        return super(StockQuantPackage, self).create(vals)

    def write(self, vals):
        res = super(StockQuantPackage, self).write(vals)
        
        if 'packaging_id' in vals or vals.get('package_use', '') == 'disposable':
            # get the package type code
            packaging_type_code = self._check_name_sscc(vals)

            for rec in self.filtered(lambda x: x.package_use == 'disposable'):
                # TODO: not calling write in a write, it should not make a loop ?
                rec.name = self._default_name_sscc(packaging_type_code)

        return res

    def _default_name_sscc(self, package_type_code=0):
        if package_type_code < 0 or package_type_code > 9 or not isinstance(package_type_code, int):
            raise UserError(_("The SSCC can't be generated, the package type code is wrong"))

        sscc_part_2 = str(self.env.company.sscc_extension_character)
        sscc_part_3a = str(self.env.company.sscc_company_prefix)
        # TODO: check sequence length ...?
        sscc_part_3b = self.env['ir.sequence'].next_by_code('sscc')

        # add zeros at the start of 3b to reach 17 characters
        sscc_part_3b = ('0' * (17 - (len(sscc_part_2 + sscc_part_3a + sscc_part_3b) + 1))) + sscc_part_3b  # +1 because of the package type code added after

        # add the package type code
        sscc_part_3b = str(package_type_code) + sscc_part_3b

        # compute check digit
        sscc_part_4 = self._compute_sscc_check_digit(sscc_part_2 + sscc_part_3a + sscc_part_3b)

        # final sscc must have 18 characters
        sscc = sscc_part_2 + sscc_part_3a + sscc_part_3b + str(sscc_part_4)

        if len(sscc) != 18:
            raise UserError(_("The SSCC can't be generated, the length is incorrect"))
        
        return sscc

    def _compute_sscc_check_digit(self, temporary_sscc):
        # calculations must be made on a string of 17 characters
        if len(temporary_sscc) != 17:
            raise UserError(_("The SSCC check digit can't be computed, the length is incorrect"))

        # compute check digit
        # https://www.gs1.org/services/how-calculate-check-digit-manually
        check_digit = 0

        # --multiplications--
        multipliers = [3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3]

        for index, multiplier in enumerate(multipliers):
            check_digit += int(temporary_sscc[index]) * multiplier

        # --find the multiple of ten--
        next_multiple = check_digit
        while next_multiple % 10 != 0:
            next_multiple += 1

        # --subtraction--
        check_digit = next_multiple - check_digit

        # the result must have one character
        if 9 < check_digit < 0:
            raise UserError(_("The SSCC check digit can't be computed, the result is incorrect"))

        return check_digit

    def set_sscc_report_printed(self):
        # called from the report
        self.write({'is_sscc_report_printed': True})
        return True

    def _get_report_sscc_filename(self):
        pickings = self._get_pickings()
        report_name = pickings._get_report_sscc_prefix()

        return report_name.format(self._get_short_name())


    def _get_short_name(self, length=10):
        self = self[0]
        return self.name[-length:]


    def _get_sscc_packages(self):
        packages = []

        for record in self:
            packages.append(record._get_sscc_package_details())

        return packages


    def _get_move_lines(self):
        domain = ['|', ('result_package_id', 'in', self.ids), ('package_id', 'in', self.ids)]
        move_lines = self.env['stock.move.line'].search(domain)

        return move_lines

    
    def _get_pickings(self):
        move_lines = self._get_move_lines()
        return move_lines.mapped('picking_id')


    def action_print_sscc_labels(self, close=True):
        report = self.env.ref('madeco_stock_sscc.action_report_sscc_label').report_action(self)
        report['close_on_report_download'] = close

        return report        


    def _get_sscc_package_details(self):
        self.ensure_one()
        context = self.env.context

        # Shortcuts, load records from context if prodived
        move_line_ids = context.get('move_lines', [])
        picking_ids = context.get('pickings', [])
        batch_ids = context.get('batch', [])

        move_lines = self.env['stock.move.line'].browse(move_line_ids).filtered_domain([('result_package_id', '=', self.id)]) if move_line_ids else self._get_move_lines()
        pickings = self.env['stock.picking'].browse(picking_ids) if picking_ids else move_lines.mapped('picking_id')
        batch = self.env['stock.picking.batch'].browse(batch_ids) if batch_ids else pickings.mapped('batch_id')
        batch = batch[0] if batch else False

        multi_picking = True if len(pickings) > 1 else False
        move_line_ids_without_package = pickings.mapped('move_line_ids_without_package').filtered_domain([('result_package_id', '=', self.id)])

        picking = pickings[0]
        company = self.company_id or picking.company_id
        partners = pickings.mapped('partner_id')
        shipping = partners.mapped('adresse_liv_id')
        orders = pickings.mapped('sale_id')
        order = orders[0] if orders and len(orders) == 1 and not batch else False
        step = batch.picking_type_id.step if batch else picking.picking_type_id.step

        vals = {
            "name": self.name,
            "content": bool(move_lines),
            "to": False,
            "date": False,
            "xdock": True,
            "order_ref": False,
            "client_order_ref": False,
            "ordered_by": False,
            "code_magasin": False,            
            "multi_picking": multi_picking,
            "batch": bool(batch),
            "picking_name": picking.name,
            "company": company,
            "sscc_gs1_identifier": company.sscc_gs1_identifier if company else '00',
            "from": company.partner_id or False,
            "weight": move_lines._get_estimated_weight(),
            "weight_uom_name": self.weight_uom_name,
            "pieces": round(sum(move_line_ids_without_package.mapped('qty_done'))),
            "parcels": len(picking.move_line_ids.filtered(lambda x: x.result_package_id == self).mapped('package_id')),
            "step": step,
        }

        if self.quant_ids:
            vals['parcels'] = len(self.quant_ids.mapped('package_origin_ids'))

        if batch:
            shipping = pickings.mapped('partner_id.adresse_liv_id')
            vals.update({
                "to": shipping[0] if shipping else False, 
                "date": picking.scheduled_date if picking else False, 
                "xdock": True,
            })
        elif order:
            vals.update({
                "to": order.partner_shipping_id,
                "date": order.commitment_date,
                "xdock": order.partner_shipping_id.xdock,
                "order_ref": order.name,
                "client_order_ref": order.client_order_ref,
                "ordered_by": order.partner_id,
                "code_magasin": order.partner_id.code_magasin,
            })      

        logger.warning(vals)
        logger.warning(move_lines)

        self.set_sscc_report_printed()
        
        return vals

