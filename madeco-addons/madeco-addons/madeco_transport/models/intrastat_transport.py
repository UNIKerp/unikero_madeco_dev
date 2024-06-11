# -*- coding: utf-8 -*-

import json
from datetime import datetime
from odoo.tools import float_compare, float_round
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import unidecode
import logging
logger = logging.getLogger(__name__)


class IntrastatTransportMode(models.Model):
    _name = 'intrastat.transport_mode'
    _inherit = 'intrastat.transport_mode'

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
    
        
