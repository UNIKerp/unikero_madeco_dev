# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)

def _get_weight(move_line):
    return move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id) * move_line.product_id.weight


class StockMove(models.Model):
    _inherit = "stock.move"
    
    product_name_supplier = fields.Char(string="Nom de l'article chez le fournisseur", compute="_compute_supplier_product_name", store=True)

    def _merge_moves(self, merge_into=False):
        # don't merge lines if the function is called on a sale order confirmation TODO: and the product is recut ?
        self = self.filtered(lambda rec: not rec.picking_id.sale_id)
        return super(StockMove, self)._merge_moves(merge_into)

    def recherche_qte_commande_stock_move(self,lines=False):   
        qte_cde = 0
        for line in lines:
            qte_cde = line.sale_line_id.product_uom_qty
        return qte_cde   

    @api.depends('product_id','picking_partner_id')
    def _compute_supplier_product_name(self):
        for move in self:
            if move.product_id and move.picking_partner_id:
                move.product_name_supplier = ''
                if move.product_id.seller_ids:
                    for seller in move.product_id.seller_ids:
                        if seller.name.name == move.picking_partner_id.name:
                            move.product_name_supplier = seller.product_name
                            break
                else:
                    move.product_name_supplier = ''

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def recherche_qte_commande_stock_move_line(self,lines=False):    
        qte_cde = 0
        for line in lines:
            qte_cde = line.move_id.sale_line_id.product_uom_qty
        return qte_cde               

    def _get_aggregated_product_quantities(self, **kwargs):
        """ Returns a dictionary of products (key = id+name+description+uom) and corresponding values of interest.

        Allows aggregation of data across separate move lines for the same product. This is expected to be useful
        in things such as delivery reports. Dict key is made as a combination of values we expect to want to group
        the products by (i.e. so data is not lost). This function purposely ignores lots/SNs because these are
        expected to already be properly grouped by line.

        returns: dictionary {product_id+name+description+uom: {product, name, description, qty_done, product_uom}, ...}
        """
        aggregated_move_lines = {}
        for move_line in self:
            name = move_line.product_id.display_name
            description = move_line.move_id.description_picking
            if description == name or description == move_line.product_id.name:
                description = False
            uom = move_line.product_uom_id
            line_key = str(move_line.product_id.id) + "_" + name + (description or "") + "uom " + str(uom.id)

            if line_key not in aggregated_move_lines:
                aggregated_move_lines[line_key] = {'name': name,
                                                   'description': description,
                                                   'qty_done': move_line.qty_done,
                                                   'product_uom': uom.name,
                                                   'product_uom_rec': uom,
                                                   'product': move_line.product_id,
                                                   'qty_cde': move_line.move_id.product_uom_qty}
            else:
                aggregated_move_lines[line_key]['qty_done'] += move_line.qty_done
                aggregated_move_lines[line_key]['qty_cde'] += move_line.move_id.product_uom_qty                
        return aggregated_move_lines   

    def _get_estimated_weight(self):
        # return round(sum([record.product_uom_id._compute_quantity(record.qty_done, record.product_id.uom_id) * record.product_id.weight for record in self]), 2)    
        return round(sum(map(_get_weight, self)), 2)    
