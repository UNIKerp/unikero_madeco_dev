# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.addons.apik_calendar.models import apik_calendar

import logging
logger = logging.getLogger(__name__)


class Picking(models.Model):
    _name = "stock.picking"
    _inherit = 'stock.picking'


        
    @api.depends('move_lines.state', 'move_lines.date', 'move_type','date_deadline')
    def _compute_scheduled_date(self):
        company_id =  self.env.company 
        for picking in self:
            moves_dates = picking.move_lines.filtered(lambda move: move.state not in ('done', 'cancel')).mapped('date')
            #
            # Sur demande de MADECO du 28 juillet, on enlève le controle sur les livraisons au plus vite (politique de livraison)
            #
            # Début
            #if picking.move_type == 'direct':
            # Fin 
               
            if picking.picking_type_id.code == 'outgoing' or picking.picking_type_id.code == 'internal':
                #
                # Pour les expéditions, on enlève le délai de livraison dans le calcul de la date prévue
                #
                if picking.partner_id.delai_livraison:
                    picking.scheduled_date = min(moves_dates, default=picking.scheduled_date or fields.Datetime.now())
                    nb_jour = picking.partner_id.delai_transport * (-1)
                    date_livraison = apik_calendar.calcul_date_ouvree_negative(picking.scheduled_date, nb_jour, company_id.nb_weekend_days, company_id.zone_geo,'datetime')  

                    #logger.info("_________________________")    
                    #logger.info(picking.name)
                    #logger.info(picking.partner_id.name)
                    #logger.info(nb_jour)
                    #logger.info(picking.scheduled_date)
                    #logger.info(date_livraison)
                    #logger.info("_________________________")     

                    picking.scheduled_date = date_livraison                     
                else:
                    picking.scheduled_date = min(moves_dates, default=picking.scheduled_date or fields.Datetime.now())
            else:  
                picking.scheduled_date = min(moves_dates, default=picking.scheduled_date or fields.Datetime.now())
            
            # Début
            #else:
            #    picking.scheduled_date = max(moves_dates, default=picking.scheduled_date or fields.Datetime.now())
            # Fin    
 
    def write(self, vals):
        if vals.get('date_done'):
            for pick in self:                             
                if pick.sale_id:
                    pick.sale_id._compute_picking_ids_sale_order() 
        
        res = super(Picking, self).write(vals)

        return res
