# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api

from functools import lru_cache


class AccountInvoiceReport(models.Model):
    _name = "account.invoice.report"
    _inherit = "account.invoice.report"
    
    categorie_commande_id = fields.Many2one('categorie.commande',string='Order category', readonly=True)
    typologie_commande_id = fields.Many2one('typologie.commande',string='Order typology', readonly=True)
    groupe_id = fields.Many2one('res.partner',string='Groupe', readonly=True)
    centrale_id = fields.Many2one('res.partner',string='Centrale', readonly=True)
    enseigne_id = fields.Many2one('res.partner',string='Enseigne', readonly=True)

    @api.model
    def _select(self):
        return '''
            SELECT
                line.id,
                line.move_id,
                line.product_id,
                line.account_id,
                line.analytic_account_id,
                line.journal_id,
                line.company_id,
                line.company_currency_id,
                line.partner_id AS commercial_partner_id,
                move.state,
                move.move_type,
                move.partner_id,
                move.invoice_user_id,
                move.fiscal_position_id,
                move.payment_state,
                move.invoice_date,
                move.invoice_date_due,
                uom_template.id                                             AS product_uom_id,
                template.categ_id                                           AS product_categ_id,
                move.categorie_commande_id                                  AS categorie_commande_id,
                move.typologie_commande_id                                  AS typologie_commande_id,
                move.groupe_id                                              AS groupe_id,
                move.centrale_id                                            AS centrale_id,
                move.enseigne_id                                            AS enseigne_id,
                line.quantity / NULLIF(COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1), 0.0) * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                                                                            AS quantity,
                -line.balance * currency_table.rate                         AS price_subtotal,
                -line.balance / NULLIF(COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1), 0.0) * currency_table.rate
                                                                            AS price_average,
                COALESCE(partner.country_id, commercial_partner.country_id) AS country_id
        '''

    """
    @api.model  
    def _group_by(self):
        return '''
            GROUP BY
                line.id,
                line.move_id,
                line.product_id,
                line.account_id,
                line.analytic_account_id,
                line.journal_id,
                line.company_id,
                line.currency_id,
                line.partner_id,
                move.name,
                move.state,
                move.type,
                move.amount_residual_signed,
                move.amount_total_signed,
                move.partner_id,
                move.invoice_user_id,
                move.fiscal_position_id,
                move.invoice_payment_state,
                move.invoice_date,
                move.invoice_date_due,
                move.invoice_payment_term_id,
                move.invoice_partner_bank_id,
                move.categorie_commande_id,
                move.typologie_commande_id,
                uom_template.id,
                uom_line.factor,
                template.categ_id,                
                COALESCE(partner.country_id, commercial_partner.country_id)
        ''' 
        """       