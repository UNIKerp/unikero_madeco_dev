# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import logging
logger = logging.getLogger(__name__)


class StockPickingBatch(models.Model):
    _name =  "stock.picking.batch"
    _inherit =  "stock.picking.batch"
    
    
    categorie_commande_id = fields.Many2one('categorie.commande',string='Order category')
    #
    # On ajoute la catégorie de commande dans la recherche des pickings
    #
    picking_ids = fields.One2many(  
        domain="[('id', 'in', allowed_picking_ids),('categorie_commande_id','=',categorie_commande_id)]")  

        #domain="['&','&','|','&',('id', 'in', allowed_picking_ids),('categorie_commande_id','=',categorie_commande_id),('categorie_commande_id','!=',False),('id', 'in', allowed_picking_ids),('categorie_commande_id','=',False)]")

    is_packaging_hidden = fields.Boolean(
        "Masquer la mise en colis", related="picking_type_id.is_packaging_hidden"
    )

    @api.model
    def _get_fields_to_read(self):
        res = super()._get_fields_to_read()
        res.append("is_packaging_hidden")
        return res
