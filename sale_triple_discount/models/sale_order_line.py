# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

import logging
logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_final_discount(self):
        #logger.info("_get_final_discount")
        self.ensure_one()
        if self.discounting_type == "additive":
            return self._additive_discount()
        elif self.discounting_type == "multiplicative":
            return self._multiplicative_discount()
        else:
            raise ValidationError(
                _("Sale order line %s has unknown discounting type %s")
                % (self.name, self.discounting_type)
            )

    def _additive_discount(self):
        #logger.info("_additive_discount")

        self.ensure_one()

        discount = 0
        if self.discount != 0 :
            discount += self.discount 
        if self.discount2 != 0 :    
            discount += self.discount2
        if self.discount3 != 0 :    
            discount += self.discount3        

        if discount <= 0:
            return 0
        elif discount >= 100:
            return 100
        return discount

    def _multiplicative_discount(self):
        #logger.info("============================")
        #logger.info("! _multiplicative_discount !")
        #logger.info("============================")

        self.ensure_one()

        final_discount = 1
        
        if self.discount != 0 :
            final_discount = final_discount * (1 - (self.discount / 100))
        if self.discount2 != 0 :    
            final_discount = final_discount * (1 - (self.discount2 / 100))
        if self.discount3 != 0 :    
            final_discount = final_discount * (1 - (self.discount3 / 100))

        resultat = 100 - final_discount * 100

        return resultat

    def _discount_fields(self): 
        #logger.info("_discount_fields")       
        return ["discount", "discount2", "discount3"]

    
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'discount2', 'discount3', 'discounting_type')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        prev_values = self.triple_discount_preprocess()
        for line in self:
            if line.discounting_type == 'additive':
                rem_total = (line.discount or 0.0) + (line.discount2 or 0.0) + (line.discount3 or 0.0)
                price = line.price_unit * (1.0 - rem_total / 100.0)
            else:
                if line.discount > 0:
                    total_int1 = line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)   
                else:
                    total_int1 = line.price_unit
                if line.discount2 > 0:
                    total_int2 = total_int1 * (1.0 - (line.discount2 or 0.0) / 100.0) 
                else:
                    total_int2 = total_int1
                if line.discount3 > 0:
                    total_int3 = total_int2 * (1.0 - (line.discount3 or 0.0) / 100.0) 
                else:
                    total_int3 = total_int2         
                       
                price = total_int3   

            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

        self.triple_discount_postprocess(prev_values)




    discount2 = fields.Float(string="Disc. 2 (%)", digits="Discount", default=0.0,)
    discount3 = fields.Float(string="Disc. 3 (%)", digits="Discount", default=0.0,)
    discounting_type = fields.Selection(
        string="Discounting type",
        selection=[("additive", "Additive"), ("multiplicative", "Multiplicative")],
        default="multiplicative",
        required=True,
        help="Specifies whether discounts should be additive "
        "or multiplicative.\nAdditive discounts are summed first and "
        "then applied.\nMultiplicative discounts are applied sequentially.\n"
        "Multiplicative discounts are default",
    )

    _sql_constraints = [
        (
            "discount2_limit",
            "CHECK (discount2 <= 100.0)",
            "Discount 2 must be lower than 100%.",
        ),
        (
            "discount3_limit",
            "CHECK (discount3 <= 100.0)",
            "Discount 3 must be lower than 100%.",
        ),
    ]

    def _get_triple_discount(self):
        #logger.info("_get_triple_discount")
        """Get the discount that is equivalent to the subsequent application
        of discount, discount2 and discount3"""
        discount_factor = 1.0
        for discount in [self.discount, self.discount2, self.discount3]:
            discount_factor *= (100.0 - discount) / 100.0
        return 100.0 - (discount_factor * 100.0)

    def _prepare_invoice_line(self, **optional_values): 
        #logger.info("_prepare_invoice_line")  
        invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
        res = super()._prepare_invoice_line(sequence=invoice_item_sequence)
        res.update({"discount2": self.discount2, "discount3": self.discount3})

        return res


    @api.depends('price_unit', 'discount','discount2', 'discount3', 'discounting_type')
    def _get_price_reduce(self):
        #logger.info("_get_price_reduce")  
        prev_values = self.triple_discount_preprocess()
        for line in self:
            if line.discounting_type == 'additive':
                rem_total = line.discount + line.discount2 + line.discount3
                line.price_reduce = line.price_unit * (1.0 - rem_total / 100.0)
            else:
                if line.discount > 0:
                    total_int1 = line.price_unit * (1.0 - line.discount / 100.0)   
                else:
                    total_int1 = line.price_unit
                if line.discount2 > 0:
                    total_int2 = total_int1 * (1.0 - line.discount2 / 100.0) 
                else:
                    total_int2 = total_int1
                if line.discount3 > 0:
                    total_int3 = total_int2 * (1.0 - line.discount3 / 100.0) 
                else:
                    total_int3 = total_int2         
                       
                line.price_reduce = total_int3    
        self.triple_discount_postprocess(prev_values)    


    def triple_discount_preprocess(self):
        #logger.info("triple_discount_preprocess")        
        """Save the values of the discounts in a dictionary,
        to be restored in postprocess.
        Resetting discount2 and discount3 to 0.0 avoids issues if
        this method is called multiple times.
        Updating the cache provides consistency through recomputations."""
        prev_values = dict()
        self.invalidate_cache(
            fnames=["discount", "discount2", "discount3"], ids=self.ids
        )
        for line in self:
            
            prev_values[line] = dict(
                discount=line.discount,
                discount2=line.discount2,
                discount3=line.discount3,
            )
            line._cache.update(
                {
                    "discount": line._get_final_discount(),
                    "discount2": 0.0,
                    "discount3": 0.0,
                }
            )
        return prev_values

    @api.model
    def triple_discount_postprocess(self, prev_values):
        #logger.info("triple_discount_postprocess")
        """Restore the discounts of the lines in the dictionary prev_values.
        Updating the cache provides consistency through recomputations."""
        self.invalidate_cache(
            fnames=["discount", "discount2", "discount3"],
            ids=[l.id for l in list(prev_values.keys())],
        )
        for line, prev_vals_dict in list(prev_values.items()):
            line._cache.update(prev_vals_dict)

