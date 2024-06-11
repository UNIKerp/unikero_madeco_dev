# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api

from functools import lru_cache


class SaleReport(models.Model):
    _name = "sale.report"
    _inherit = "sale.report"
    
    categorie_commande_id = fields.Many2one('categorie.commande',string='Order category', readonly=True)
    typologie_commande_id = fields.Many2one('typologie.commande',string='Order typology', readonly=True)
    groupe_id = fields.Many2one('res.partner',string='Groupe', readonly=True)
    centrale_id = fields.Many2one('res.partner',string='Centrale', readonly=True)
    enseigne_id = fields.Many2one('res.partner',string='Enseigne', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):       
        fields['categorie_commande_id'] = ', s.categorie_commande_id as categorie_commande_id'
        fields['typologie_commande_id'] = ', s.typologie_commande_id as typologie_commande_id'
        fields['groupe_id'] = ', s.groupe_id as groupe_id'
        fields['centrale_id'] = ', s.centrale_id as centrale_id'
        fields['enseigne_id'] = ', s.enseigne_id as enseigne_id'

        groupby += ', s.categorie_commande_id , s.typologie_commande_id, s.groupe_id, s.centrale_id, s.enseigne_id'
        
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
    
