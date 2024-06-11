# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class SuiviPresta(models.Model):
    _name = 'suivi.presta'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Suivi des mouvements PrestaShop'
    _check_company_auto = True 
    _order = "date_mvt_presta desc, company_id"
    
    name = fields.Char(string="Nom du mouvement", required=True, store=True,translate=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, stored=True, index=True)
    date_mvt_presta = fields.Datetime(string="Date du mouvement PrestaShop", required=True, store=True, default=fields.Datetime.now)
    libelle_mvt_presta = fields.Text(string="Libellé du mouvement", default=False,store=True)
    erreur_id = fields.Many2one('erreur.presta', 'Erreur', required=False, store=True)
    active = fields.Boolean('Active', default=True)
    reussite = fields.Boolean('Intégration réussie', related='erreur_id.reussite', default=False)

