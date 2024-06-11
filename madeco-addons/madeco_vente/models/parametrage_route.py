# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)

class ParametrageRoute(models.Model):

    _name = "parametrage.route"
    _description = "Paramétrage Route"
    _rec_name = 'name'
    _order = "name, id"    
    
    name = fields.Char('Nom du paramétrage route', required=True, translate=True)
    active = fields.Boolean(string='Active', default=True) 
    xdock = fields.Boolean(string="Livraison XDOCK", default=False)
    recoupe = fields.Boolean(string="Commande de recoupe", default=False)
    implantation = fields.Boolean(string="Commande d'implantation", default=False)
    typologie_article = fields.Selection([
        ('A1', 'Article standard'),
        ('A2', 'Article à recouper'),
        ('A3', 'Article sur mesure'),
        ('A4', 'Dropship'),],
        string="Typologie d'article", default='A1', required=True)   
    route_id = fields.Many2one('stock.location.route',string='Route', required=True)    



