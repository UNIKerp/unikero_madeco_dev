import logging
import random

from odoo import models

_logger = logging.getLogger(__name__)

class StockRule(models.Model):
    _inherit = "stock.rule"


    def _prepare_purchase_order(self, company_id, origins, values):
        vals = super(StockRule, self)._prepare_purchase_order(company_id, origins, values)
        _logger.debug("New PO: {}".format(vals))

        return vals
        

    def _make_po_get_domain(self, company_id, values, partner):
        excludes = ['user_id', 'date_order']

        domain = super(StockRule, self)._make_po_get_domain(company_id, values, partner)
        domain = (dom for dom in domain if dom[0] not in excludes)

        message = "".join(["\n{}: {}".format(key,value) for key,value in values.items()])

        _logger.debug("Search PO for {} with {}".format(partner, message))
        _logger.debug("Domain: {}".format(domain))

        return domain
