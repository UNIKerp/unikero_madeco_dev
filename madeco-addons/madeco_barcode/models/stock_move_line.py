# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import float_compare

import logging
logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def preparation_report_location_displaying(self):
        """
        return a boolean indicating if the location should be displayed on the preparation report
        """
        self.ensure_one()

        #logger.info("début report location displaying ")

        parent_locations = self.env['stock.location'].search([('barcode', 'in', ['WH-PICK'])])
        locations = self.env['stock.location'].search([('location_id', 'child_of', parent_locations.ids)])

        # product not in picking
        if float_compare(sum([self.env['stock.quant']._get_available_quantity(self.product_id, loc) for loc in locations]), 0.0, precision_digits=2) != 1:
            parent_locations = self.env['stock.location'].search([('barcode', 'in', ['ALPHA-STOCK', 'WH-RES'])])
            locations = self.env['stock.location'].search([('location_id', 'child_of', parent_locations.ids)])

            # product in reserve or agfa
            if any([float_compare(self.env['stock.quant']._get_available_quantity(self.product_id, loc), 0.0, precision_digits=2) == 1 for loc in locations]):
                
                #logger.info("avant return False")
                
                return False

        #logger.info("avant return True")

        return True

        
    def preparation_report_line_displaying(self):
        """
        return a boolean indicating if the line should be displayed on the preparation report
        """
        self.ensure_one()

        if float_compare(self.product_id.qty_available, 0.0, precision_digits=2) != 1:
            return False

        return True
