# -*- coding: utf-8 -*-

import json
from datetime import datetime
from datetime import timedelta
from odoo.tools import float_compare, float_round
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'  

    lig_commande_edi = fields.Boolean(string="Commande EDI",default=False)
    code_art_vendeur = fields.Char(string="Code article vendeur", copy=True)
    code_art_acheteur = fields.Char(string="Code article acheteur", copy=True)
    qte_pcb = fields.Float(string="Quantité PCB", copy=True)
    unite_pcb = fields.Many2one('uom.uom',string="Unité PCB", copy=True)
    qte_gratuit = fields.Float(string="Quantité gratuite", copy=True)
    unite_gratuit = fields.Many2one('uom.uom',string="Unité gratuite", copy=True)
    pub_edi = fields.Float(string="PUB EDI", copy=True)
    pun_edi = fields.Float(string="PUN EDI", copy=True)
    pvc_edi = fields.Float(string="PVC EDI", copy=True)
    mt_net_ligne_edi = fields.Float(string="Montant net ligne EDI", copy=True)
    nb_ul_edi = fields.Float(string="Nombre d'UL", copy=True)
    type_emballage = fields.Char(string="No de commande magasin", copy=True)
    ean_ul_edi = fields.Many2one('product.product',string="EAN ul", copy=True)
    date_liv_edi = fields.Datetime(string="Date de livraison demandée", copy=True)
    no_cde_magasin = fields.Char(string="No de commande magasin (RFF+CR)", copy=True)
    gln_magasin = fields.Many2one('res.partner',string="GLN magasin (LOG+7)", copy=True)
    comment_edi = fields.Text(string="Commentaire ligne EDI", copy=True)
    ref_cde_cli_final = fields.Char(string="Référence commande client final (RFF+ON/RFF+UC)", copy=True)
    no_cde_remplace = fields.Char(string="No de commande remplacée (RFF+PW)", copy=True)
    no_ope_promo = fields.Char(string="No d'opération promotionnelle (RFF+PD)", copy=True)
    no_lig_erp_cli = fields.Char(string="No ligne ERP client (RFF+LI)", copy=True)
    pourc_remise_edi = fields.Float(string="Pourcentage de remise", copy=True)
    no_ligne_edi = fields.Char(string="No ligne EDI", copy=True)
    commande_edi = fields.Boolean(related="order_id.commande_edi",string="Commande EDI",default=False)
    pu_different = fields.Boolean(string="PU différent", compute='_compute_prix_unitaire_different', default=False)



    @api.depends('price_unit','pun_edi')
    def _compute_prix_unitaire_different(self):

        for ligne in self:
            if ligne.price_unit:
                if ligne.pun_edi:
                    if ligne.price_unit == ligne.pun_edi:
                        ligne.pu_different = False
                    else:   
                        if ligne.order_id.commande_edi: 
                            ligne.pu_different = True
                        else:
                            ligne.pu_different = False        
                else: 
                    ligne.pu_different = False   
            else:
                ligne.pu_different = False


    