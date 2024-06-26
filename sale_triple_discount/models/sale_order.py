# -*- coding: utf-8 -*-

from odoo import api, models

import logging
logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends("order_line.price_total")
    def _amount_all(self):
        prev_values = dict()
        for order in self:
            prev_values.update(order.order_line.triple_discount_preprocess())
        super()._amount_all()
        self.env["sale.order.line"].triple_discount_postprocess(prev_values)
        

    def _get_tax_amount_by_group(self):
        # Copy/paste from standard method in sale
        self.ensure_one()
        res = {}
        for line in self.order_line:
            price_reduce = line.price_reduce  # changed
            taxes = line.tax_id.compute_all(
                price_reduce,
                quantity=line.product_uom_qty,
                product=line.product_id,
                partner=self.partner_shipping_id,
            )["taxes"]
            for tax in line.tax_id:
                group = tax.tax_group_id
                res.setdefault(group, 0.0)
                for t in taxes:
                    if t["id"] == tax.id or t["id"] in tax.children_tax_ids.ids:
                        res[group] += t["amount"]
        res = sorted(list(res.items()), key=lambda l: l[0].sequence)
        res = [(l[0].name, l[1]) for l in res]
        return res
