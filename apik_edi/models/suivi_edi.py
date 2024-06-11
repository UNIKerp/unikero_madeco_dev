# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class SuiviEdi(models.Model):
    _name = 'suivi.edi'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Suivi des mouvements EDI'
    _check_company_auto = True 
    _order = "date_mvt_edi desc, company_id, flux_id"
    
    name = fields.Char(string="Nom du mouvement", required=True, store=True,translate=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    date_mvt_edi = fields.Datetime(string="Date du mouvement EDI", required=True, store=True, default=fields.Datetime.now)
    libelle_mvt_edi = fields.Text(string="Libellé du mouvement", default=False,store=True)
    flux_id = fields.Many2one('flux.edi', 'Flux', required=True, store=True)
    erreur_id = fields.Many2one('erreur.edi', 'Erreur', required=False, store=True)
    active = fields.Boolean('Active', default=True)
    reussite = fields.Boolean('Intégration réussie', related='erreur_id.reussite', default=False)

