# -*- coding: utf-8 -*-

#import json
from email.policy import default
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime, timedelta
from tempfile import TemporaryFile
import base64,pysftp,ftplib
import io
import logging
logger = logging.getLogger(__name__)

class UnikPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    unik_ref_prestashop = fields.Char("Couple REFPRESTA")
    
class UnikMrpProduction(models.Model):
    _inherit = 'mrp.production'

    unik_ref_prestashop = fields.Char("Couple REFPRESTA")


class UnikOrderLine(models.Model):
    _inherit = 'sale.order.line'

    unik_ref_prestashop = fields.Char("Couple REFPRESTA")
    ordre_fabrication_id = fields.Many2one('mrp.production')
    bon_commande_id = fields.Many2one('purchase.order')


    # ------------------------------------------------------------------------------
    # Récupération des couples REFPRESTA lors de la creation d'une ligne de commande
    # ------------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals):
        rec = super(UnikOrderLine, self).create(vals)
        for i in rec:
            if i.product_id.typologie_article  == 'A3':
                print("********************",i.name)
                if '-' in i.name:
                    desc = i.name.split('-')
                    print("********************",desc)
                    taille = len(desc)
                    N = 9
                    length = len(str(desc[taille-2]))
                    str2 = str(desc[taille-2])[length - N:]
                    element = str2+'-'+str(desc[taille-1])
                    element = element.replace(' ','')
                    i.unik_ref_prestashop = element
        return rec
    

class UnikOrder(models.Model):
    _inherit = 'sale.order'

    comfour_envoye = fields.Boolean(default=False)
    portail = fields.Char('PORTAIL')
    # ---------------------------------------------------------------------------------------------------------------
    # Mise à jour des couples REFPRESTA et Liaison des lignes de vente avec un ordre de fabrication et un bon d'achat
    # ---------------------------------------------------------------------------------------------------------------
    def _action_confirm(self):
        result = super()._action_confirm()
        # ---------------------------------------------------------
        # Liaison des lignes de vente avec un ordre de fabrication
        # ---------------------------------------------------------
        order_fabrication_ids = self.env['mrp.production'].sudo().search([('origin', '=', self.name)])
        if order_fabrication_ids:
            for l in self.order_line:
                if l.unik_ref_prestashop:
                    for o in  order_fabrication_ids:
                        if l.product_id==  o.product_id:
                            if not o.unik_ref_prestashop :
                                o.unik_ref_prestashop = l.unik_ref_prestashop
                                l.ordre_fabrication_id = o.id
                                break
        # --------------------------
        # Liaison des lignes de vente avec un bon d'achat
        # --------------------------
        bon_achat_ids = self.env['purchase.order'].sudo().search([('origin', '=', self.name),('state','!=','cancel')],order="id desc")
        if bon_achat_ids:
            for l in self.order_line:
                i =0
                if l.product_id.typologie_article  == 'A3':
                    for a in  bon_achat_ids:
                        if not a.unik_ref_prestashop:
                            for la in a.order_line:
                                if la.product_id == l.product_id and la.product_qty == l.product_uom_qty:
                                    a.unik_ref_prestashop = l.unik_ref_prestashop
                                    l.bon_commande_id  = a.id
                                    i+=1
                                    break
                        if i != 0:
                            break
        return result
        
