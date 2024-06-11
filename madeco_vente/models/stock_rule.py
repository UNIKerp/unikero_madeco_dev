
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import logging

from odoo import models

logger = logging.getLogger(__name__)

class StockRule(models.Model):
    _inherit = "stock.rule"


    def _make_po_get_domain(self, company_id, values, partner):        
        domain = super()._make_po_get_domain(company_id, values, partner)
        if values.get("supplier"):
            suppinfo = values["supplier"]
            product = suppinfo.product_id or suppinfo.product_tmpl_id

            if product.typologie_article == 'A3':
                if values.get("move_dest_ids"):
                    domain += (("order_line.name", "=", values["move_dest_ids"][:1].description_ligne_vente),)

        return domain

    '''
    def _run_buy(self, procurements):
        for procurement, _rule in procurements:
            grouping = procurement.product_id.categ_id.procured_purchase_grouping
            if not grouping:
                grouping = self.env.company.procured_purchase_grouping
            procurement.values["grouping"] = grouping
        return super()._run_buy(procurements)    
    '''    