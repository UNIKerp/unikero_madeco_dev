# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)

class MadecoTransport(models.Model):

    _name = "madeco.transport"
    _description = "Mode of transport"
    _rec_name = 'name'
    _order = "name, id"    
    
    name = fields.Char('Order typology', required=True, translate=True)
    active = fields.Boolean(string='Active', default=True) 
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, 
        default=lambda self: self.env.company)
    mode_transport_edi = fields.Selection([
        ('10', 'Transport maritime'),
        ('20', 'Transport ferroviaire'),
        ('30', 'Transport routier'),
        ('40', 'Transport aérien'),
        ('50', 'Courrier'),
        ('80', 'Transport fluvial'),
        ], required=True, default='30',string="Mode de transport EDI", copy=False)
    type_transport_edi = fields.Selection([
        ('23', 'Wagon de vrac'),
        ('25', 'Express rail'),
        ('31', 'Camion'),
        ('32', 'Camion citerne'),
        ('34', 'Colis express par route'),
        ('16E', 'Camion plat articulé 10T'),
        ('21E', 'Camion plat 15T'),
        ('34E', 'Remorque pour vrac'),
        ('36E', 'Camionnette'),
        ], required=True, default='31',string="Type de transport EDI", copy=False)    
    type_envoi_edi = fields.Selection(
        string="Type Envoi EDI",
        selection=[("aucun", "Aucun"), ("heppner", "Transport HEPPNER"), ("dpd", "Transport DPD"),("laposte", "Etiquette LA POSTE")],
        default="aucun",
        required=True)
    code_expe_heppner = fields.Char(string='Code Expéditeur Heppner')   
    code_transporteur_heppner = fields.Char(string='Code Transporteur Heppner')  
    code_produit_heppner = fields.Char(string='Code Produit Heppner') 
    code_service_heppner = fields.Selection(
        string="Service Heppner",
        selection=[("P18", "Star priority"), 
        ("P13", "Star priority avant 13h"),
        ("D18", "Livraison à date fixe"),
        ("D13", "Livraison à date fixe avant 13h"),
        ("RDV", "Livraison sur RDV"),
        ("PAR", "Livraison chez un particulier")],
        default="P18",
        required=False)
    no_compte_chargeur_dpd = fields.Char(string='No de compte chargeur DPD')
    dpd_predict = fields.Boolean(string="DPD Predict ", default=False)  
    dpd_retour = fields.Boolean(string="Gestion des retours DPD", default=False)
    dpd_type_envoi = fields.Selection(
        string="Tyoe d'envoi DPD",
        selection=[("classic", "Classic/Export"), 
        ("predict", "Predict"),
        ("relais", "Relais")],
        default="classic",
        required=False) 


