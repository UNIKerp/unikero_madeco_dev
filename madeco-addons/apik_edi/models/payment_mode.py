# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)

class AccountPaymentMode(models.Model):
    _inherit = 'account.payment.mode'

    payment_method_edi = fields.Many2one('payment.method',string="Méthode de paiement EDI")
