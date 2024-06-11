# -*- coding: utf-8 -*-
"""
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
    Default Docstring
"""
import logging
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare

from werkzeug.urls import url_encode

logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    groupe_id = fields.Many2one('res.partner',string='Groupe', related='order_id.groupe_id', store=True, copy=False)
    centrale_id = fields.Many2one('res.partner',string='Centrale', related='order_id.centrale_id', store=True, copy=False)
    enseigne_id = fields.Many2one('res.partner',string='Enseigne', related='order_id.enseigne_id', store=True, copy=False)
    prix_promo = fields.Boolean(string='Promotion', default=False, store=True, copy=False)
    date_livraison_demandee = fields.Date(related='order_id.date_livraison_demandee')
    date_livraison_calculee = fields.Date(related='order_id.date_livraison_calculee')
    line_global_discount = fields.Boolean(string="Global discount line", default=False, store=True, copy=False)
    typologie_article = fields.Selection([
        ('A1', 'Article standard'),
        ('A2', 'Article à recouper'),
        ('A3', 'Article sur mesure'),
        ('A4', 'Dropship'),],
        string="Typologie d'article", related='product_id.product_tmpl_id.typologie_article')

    @api.onchange('product_id')
    def product_id_change(self):

        if not self.route_id:
            #
            # On recherche la 1ère route active dans la fiche article 
            # 
            if self.product_id:
                if self.product_id.route_ids:
                    for route in self.product_id.route_ids:
                        if route.product_selectable and route.sale_selectable:
                            self.route_id = route.id
                            break

            if self.order_id.route_id:
                self.route_id = self.order_id.route_id.id

        # 
        # On regarde si article de recoupe
        #         
        if self.product_id.typologie_article == 'A2':
            self.order_id.recoupe = True

        list_prix_obj = self.env['product.pricelist.item'] 
        if not self.product_id:
            return
        valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
        # remove the is_custom values that don't belong to this template
        for pacv in self.product_custom_attribute_value_ids:
            if pacv.custom_product_template_attribute_value_id not in valid_values:
                self.product_custom_attribute_value_ids -= pacv

        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav

        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.order_id.partner_id.lang).code,
            partner=self.order_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        vals.update(name=self.get_sale_order_line_multiline_description_sale(product))

        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
        
            #
            # on recherche si promo
            #
            list_prix = list_prix_obj.search([('product_tmpl_id','=',self.product_id.product_tmpl_id.id),('pricelist_id','=',self.order_id.pricelist_id.id)], limit=1) 
            if list_prix:
                vals['prix_promo'] = list_prix.prix_promo_item

            else:
                list_prix2 = list_prix_obj.search([('categ_id','=',self.product_id.product_tmpl_id.categ_id.id),('pricelist_id','=',self.order_id.pricelist_id.id)], limit=1) 
                if list_prix2:
                    vals['prix_promo'] = list_prix.prix_promo_item   

        self.update(vals)

        title = False
        message = False
        result = {}
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s", product.name)
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False
        return result                
    
    def _get_final_prix_promo(self):
        self.ensure_one()
        prix_promo = [getattr(self, x) or 0.0 for x in self._discount_fields()]        
        return prix_promo

    def _discount_fields(self):
        return ["prix_promo"]

    
    @api.depends("prix_promo")
    def _compute_amount(self):
        prev_values = self.prix_promo_preprocess()
        super()._compute_amount()
       
        self.prix_promo_postprocess(prev_values)
   

    def prix_promo_preprocess(self):
        prev_values = dict()
        self.invalidate_cache(
            fnames=["prix_promo"], ids=self.ids
        )
        for line in self:
            prev_values[line] = dict(
                prix_promo=line.prix_promo,
            )
            line._cache.update(
                {
                    "prix_promo": line._get_final_prix_promo(),
                }
            )
        return prev_values
        

    @api.model
    def prix_promo_postprocess(self, prev_values):
        self.invalidate_cache(
            fnames=["prix_promo"],
            ids=[l.id for l in list(prev_values.keys())],
        )
        for line, prev_vals_dict in list(prev_values.items()):
            line._cache.update(prev_vals_dict)
            

    def _prepare_invoice_line(self, **optional_values): 
        invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
        res = super()._prepare_invoice_line(sequence=invoice_item_sequence)

        res.update({"prix_promo": self.prix_promo,
                    "line_global_discount": self.line_global_discount,
                    })

        return res      
