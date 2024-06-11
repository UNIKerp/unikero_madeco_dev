# -*- coding: utf-8 -*-

#import json
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

    @api.model_create_multi
    def create(self, vals):
        rec = super(UnikOrderLine, self).create(vals)
        for i in rec:
            if i.product_id.typologie_article  == 'A3':
                desc = i.name.split('-')
                taille = len(desc)
                element = str(desc[taille-2])+'-'+str(desc[taille-1])
                i.unik_ref_prestashop = element
        return rec
    

class UnikOrder(models.Model):
    _inherit = 'sale.order'

    
    # --------------------------
    # Business Methods
    # --------------------------
    def _action_confirm(self):
        result = super()._action_confirm()
        # --------------------------
        # Business Methods
        # --------------------------
        order_fabrication_ids = self.env['mrp.production'].sudo().search([('origin', '=', self.name)])
        if order_fabrication_ids:
            for l in self.order_line:
                if l.unik_ref_prestashop:
                    for o in  order_fabrication_ids:
                        if l.product_id==  o.product_id:
                            if not o.unik_ref_prestashop :
                                o.unik_ref_prestashop = l.unik_ref_prestashop
                                l.ordre_fabrication_id = o
                                break
        # --------------------------
        # Business Methods
        # --------------------------
        bon_achat_ids = self.env['purchase.order'].sudo().search([('origin', '=', self.name),('state','!=','cancel')])
        if bon_achat_ids:
            if len(bon_achat_ids)==1:
                for line in self.order_line:
                    bon_achat_ids.unik_ref_prestashop = line.unik_ref_prestashop
                    line.bon_commande_id = bon_achat_ids
            else:
                for l in self.order_line:
                    i =0
                    if not l.bon_commande_id and l.unik_ref_prestashop:
                        for a in  bon_achat_ids:
                            if not a.unik_ref_prestashop:
                                for la in a.order_line:
                                    if la.product_id == l.product_id:
                                        a.unik_ref_prestashop = l.unik_ref_prestashop
                                        l.bon_commande_id  = a
                                        i+=1
                                        break
                            if i != 0:
                                break
        return result
        
