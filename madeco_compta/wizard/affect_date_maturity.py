# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from odoo.http import request
import odoo.addons.decimal_precision as dp

import logging
logger = logging.getLogger(__name__)

class AffectationDateMaturity(models.TransientModel):
    _name = 'aff_date_maturity'
    _description = 'Affectation date Echéance ligne'
    
    start_date = fields.Date(required=True, default=fields.Date.today)    
    
    def affecter_date_maturity(self):
        #
        # on fait une boucle pour modifier tous les factures sélectionnées
        #
        today = fields.Date.context_today(self)        
        move_line_ids = self.env['account.move.line'].search([('id', 'in', self._context.get('active_ids', True))])
        for move_line in move_line_ids:    
            if move_line:  
                #
                # On ne modifie que les lignes clients ou fournisseurs
                #
                if move_line.account_id.user_type_id.type in ('receivable', 'payable'):
                    #
                    # On ne modifie que les factures dont la date d'échéance n'est pas calculée
                    #
                    if not move_line.date_maturity:

                        others_lines = move_line.move_id.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                        company_currency_id = (move_line.company_id or self.env.company).currency_id
                        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
                        total_amount_currency = sum(others_lines.mapped('amount_currency'))

                        if move_line.account_id.user_type_id.type == 'receivable':
                            payment_term_id = move_line.partner_id.property_payment_term_id
                        else:
                            payment_term_id = move_line.partner_id.property_supplier_payment_term_id                           

                        #
                        # On fait le calcul uniquement si payment_term_id est renseigné 
                        #
                        if payment_term_id:
                            computation_date = move_line.date or today
                            to_compute = payment_term_id.compute(total_balance, date_ref=computation_date, currency=move_line.company_id.currency_id)
                            if move_line.currency_id == move_line.company_id.currency_id:
                                # Single-currency.
                                to_compute = [(b[0], b[1], b[1]) for b in to_compute]
                            else:
                                # Multi-currencies.
                                to_compute_currency = payment_term_id.compute(total_amount_currency, date_ref=computation_date, currency=move_line.currency_id)
                                to_compute = [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]                        

                            for date_maturity, balance, amount_currency in to_compute:
                                move_line.date_maturity = date_maturity 

                        
        return {}
    
