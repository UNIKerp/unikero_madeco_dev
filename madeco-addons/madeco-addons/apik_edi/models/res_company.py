# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class res_company(models.Model):
    _inherit = 'res.company'
    
    param_edi_id = fields.Many2one('parametre.edi', string='Partenaire EDI', readonly=False)
    gestion_user_id = fields.Many2one('res.users', string='Gestionnaire EDI', readonly=False)
    group_user_id = fields.Many2one('res.groups',string='Groupe gestion EDI', readonly=False)
    type_societe = fields.Char(string='Type de société EDI',readonly=False)
    capital_social = fields.Char(string='capital social EDI',readonly=False)
    gestion_archivage = fields.Boolean(string="Gestion de l'artchivage des échanges EDI", default=False,readonly=False)
    par_by_id = fields.Many2one('type.intervenant',string='Type intervenant acheteur (NAD+BY)', readonly=False)
    par_uc_id = fields.Many2one('type.intervenant',string='Type intervenant client final (NAD+UC)', readonly=False)
    email_ordchg = fields.Char(string='Email destinataire des flux ORDCHG', readonly=False)
    par_dp_id = fields.Many2one('type.intervenant',string='Type intervenant Livré à (NAD+DP)', readonly=False)
    par_ud_id = fields.Many2one('type.intervenant',string='Type intervenant client final (NAD+UD)', readonly=False)
    cond_escompte_text = fields.Text(string="Conditions d’escomptes", readonly=False)
    penal_retard_text = fields.Text(string="Pénalités de retard", readonly=False)
    resa_proprio_text = fields.Text(string="Réserve de propriété", readonly=False)
    client_factor_text = fields.Text(string="Client factor", readonly=False)

    