# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class res_company(models.Model):
    _inherit = 'res.company'
    
    param_presta_id = fields.Many2one('parametre.presta', string='Partenaire PrestaShop', readonly=False)
    gestion_presta_user_id = fields.Many2one('res.users', string='Gestionnaire PrestaShop', readonly=False)
    group_presta_user_id = fields.Many2one('res.groups',string='Groupe gestion PrestaShop', readonly=False)
    gestion_archivage_presta = fields.Boolean(string="Gestion de l'artchivage des échanges PrestaShop", default=False,readonly=False)
    france_fiscal_position_id = fields.Many2one('account.fiscal.position',string='Position fiscale par défaut pour la France', readonly=False)
    france_pays_id = fields.Many2one('res.country',string='Code pays pour la France', readonly=False)


