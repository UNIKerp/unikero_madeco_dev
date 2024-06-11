# -*- coding: utf-8 -*-
"""
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
    Default Docstring
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    
    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id_custom(self):
        # Ensures all properties and fiscal positions
        # are taken with the company of the order
        # if not defined, with_company doesn't change anything.
        self = self.with_company(self.company_id)
        if self.partner_id:        
            self.incoterm_id = self.partner_id.incoterm_id.id
        return {}

    @api.model
    def calcul_date_jour(self,docs=False):        
        date_jour = fields.Date.today(self)                                   
        return date_jour  

    @api.model
    def calcul_poids_total(self,docs=False):   
        poids_total = 0
        for doc in docs:
            for line in doc.order_line:
                if line.product_id.weight:
                    poids_total += (line.product_qty * line.product_id.weight)
        return poids_total     

    @api.model
    def calcul_nbr_product(self,docs=False):   
        nb_produits = 0
        for doc in docs:
            for line in doc.order_line:
                nb_produits += line.product_qty 
        return nb_produits 

    @api.model
    def calcul_date_echeance(self,docs=False):
        date_due = fields.Date.today(self)      
        for doc in docs:
            date_due = doc.date_order.date()        
        return date_due   

    @api.model
    def calcul_date_commande(self,docs=False):
        date_cde = fields.Date.today(self)      
        for doc in docs:
            if doc.date_approve:
                date_cde = doc.date_approve.date()   
            else:
                date_cde = doc.date_planned.date()         
        return date_cde  

    @api.model
    def calcul_date_prevue(self,docs=False):
        date_liv = fields.Date.today(self)      
        for doc in docs:
            date_liv = doc.date_planned.date()        
        return date_liv                    



class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def recherche_ref_fourn(self,docs=False, lines=False):   
        ref_fourn = ''
        for doc in docs:
            for line in lines:
                if line.product_id.seller_ids:
                    for seller in line.product_id.seller_ids:

                        logger.info(seller.name)
                        logger.info(seller.name.id)
                        logger.info(doc.partner_id.name)
                        logger.info(doc.partner_id.id)

                        if seller.name.id == doc.partner_id.id:
                            ref_fourn = seller.product_code
                            return ref_fourn
                else:
                    ref_fourn = ''        
        return ref_fourn      
