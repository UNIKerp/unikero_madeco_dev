# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime, timedelta
from datetime import date
from odoo.exceptions import AccessError, UserError, ValidationError
import json
import datetime

from odoo.addons.apik_calendar.models import apik_calendar

import logging
logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = 'sale.order.line'
    
    assembly_time = fields.Integer(string="Assembly time",compute='_compute_assembly_time', default=0,
        help="If the indicator is red, the system failed to calculate a mount delay. Consult the warehouses.")
    assembly_time_ok = fields.Boolean(string="Calcul délai montage ok", default=True)    
    display_assembly_time = fields.Boolean(compute='_compute_display_assembly_time') 
    display_montage_error = fields.Char(string="", help="If the indicator is red, the system failed to calculate a mount delay. Consult the warehouses.")
    display_montage_ok = fields.Char(string="", help="If the indicator is red, the system failed to calculate a mount delay. Consult the warehouses.")
    component_replenishment_time = fields.Integer(string="Component replenishment time",default=0)
    component_available = fields.Selection([('yes', 'Yes'),('no', 'No'),(' ','sans')], string='Component available', default=' ') 
    display_component_error = fields.Char(string="")
    display_component_ok = fields.Char(string="")
    detail_component = fields.Char(string="Component detail")
    overall_lead_time = fields.Integer(string="Overall lead time in days",compute='_compute_overall_lead_time', default=0)
    availability_date = fields.Datetime(string="Date of availability", compute='_compute_availability_date')
    display_alert_message = fields.Boolean(string="", default=False) 
    display_alert_message_montage = fields.Boolean(string="", default=False) 
    display_alert_message_compo = fields.Boolean(string="", default=False) 
    date_livraison_prevue = fields.Datetime(string="Date de livraison prèvue", related='order_id.commitment_date', store=True)
    product_uom_qty = fields.Float(default=0.0)    

    @api.depends('product_id', 'product_uom_qty','assembly_time')
    def _compute_display_assembly_time(self):
        for line in self:
            if line.assembly_time == 0 or not line.assembly_time:
                line.display_assembly_time = False
            else:
                line.display_assembly_time = True

    @api.depends('assembly_time', 'component_replenishment_time')
    def _compute_overall_lead_time(self):
        company_id =  self.env.company 
        for line in self:              
            if line.component_available == 'yes':
                if line.assembly_time_ok: 
                    line.overall_lead_time = line.assembly_time + line.component_replenishment_time + company_id.delai_debut_disponibilite            
                else:
                    line.overall_lead_time = False
            else:
                if line.product_id.bom_count > 0:
                    if line.component_replenishment_time > 0:
                        if line.assembly_time_ok: 
                            line.overall_lead_time = line.assembly_time + line.component_replenishment_time + company_id.delai_debut_disponibilite            
                        else:
                            line.overall_lead_time = False
                    else:    
                        line.overall_lead_time = False
                else:
                    if line.assembly_time_ok:
                        line.overall_lead_time = line.component_replenishment_time + company_id.delai_debut_disponibilite    
                    else:    
                        line.overall_lead_time = False

    @api.depends('overall_lead_time')
    def _compute_availability_date(self):
        typedate = 'datetime'
        company_id =  self.env.company 
        today = fields.Datetime.now()
        for line in self:
            if line.overall_lead_time:
                line.availability_date = apik_calendar.calcul_date_ouvree(today, line.overall_lead_time, company_id.nb_weekend_days, company_id.zone_geo, typedate)  
                date_calc = line.availability_date.date()
                date_jour = date.today()
                nb_jour = (date_calc - date_jour)
                nb_entier = nb_jour.days
                line.customer_lead = nb_entier or 0
            else:
                line.availability_date = False  
                line.customer_lead = False  

    @api.depends('product_id', 'product_uom_qty')
    def _compute_assembly_time(self):
        delai_obj = self.env["stock.warehouse.product"]
        for line in self:
            line.display_alert_message = False
            if line.order_id.warehouse_id:
                if line.product_id:
                    delais = delai_obj.search([('warehouse_id','=',line.order_id.warehouse_id.id),('product_tmpl_id','=',line.product_id.product_tmpl_id.id)]) 
                    if delais:
                        delai_trouve = False
                        delai_jour = 0
                        for delai in delais:
                            if line.product_uom_qty < delai.quantity_max:
                                delai_jour = delai.time_limit
                                delai_trouve = True 
                                break
                        if delai_trouve == True:
                            line.assembly_time = delai_jour  
                            line.display_alert_message_montage = False 
                            line.assembly_time_ok = True 
                        else:
                            line.assembly_time = 0  
                            line.display_alert_message_montage = True 
                            line.assembly_time_ok = False       
                    else:
                        line.assembly_time = 0 
                        line.display_alert_message_montage = True 
                        line.assembly_time_ok = False             
                else:
                    line.assembly_time = 0  
                    line.display_alert_message_montage = False
                    line.assembly_time_ok = True               
            else:
                line.assembly_time = 0 
                line.display_alert_message_montage = False
                line.assembly_time_ok = True   

            article_sous_traite = self.recherche_article_sous_traite(line)
            if article_sous_traite:
                line.assembly_time = 0  
                line.display_alert_message_montage = False 
                line.assembly_time_ok = True    
            else:    
                if line.product_id.bom_count == 0 or line.product_id.bom_count == False:
                    line.assembly_time = 0  
                    line.display_alert_message_montage = False 
                    line.assembly_time_ok = True  
            if line.display_alert_message_compo or line.display_alert_message_montage:
                line.display_alert_message = True 
            else:
                line.display_alert_message = False          

    ########################################################################
    # Calcul des délais composants de chaque ligne 
    ########################################################################
    #@api.depends('product_id', 'product_uom_qty')
    @api.onchange('product_id', 'product_template_id', 'product_uom_qty')
    def _compute_display_component_time(self):
        typedate = 'datetime'
        delai_sst_obj = self.env["partner.subcontracting.deadlines"]
        partner_obj = self.env["res.partner"]
        today = date.today()
        company_id =  self.env.company 
        today_ferie = fields.Datetime.now()
        for line in self:            
            qte_origine = line._origin.product_uom_qty

            delai_calc = 0
            rows_delai = []
            line.component_available = ' ' 
            line.display_alert_message = False

            #
            # On traite les articles sous-traités sans stock 
            #
            if line.product_id.art_sst_no_stock:
                delai_min = 0
                delai_trouve = False
                alerte = False
                if line.product_id.seller_ids:
                    for seller in line.product_id.seller_ids:
                        if seller.name:
                            delais_sst = delai_sst_obj.search([('partner_id','=',seller.name.id)]) 
                            if delais_sst:
                                delai_trouve = False
                                delai_jour = 0
                                for delai in delais_sst:
                                    if line.product_uom_qty < delai.quantity_below:
                                        delai_jour = delai.production_time
                                        delai_trouve = True 
                                        break
                                if delai_trouve == True:
                                    if delai_min == 0:
                                        delai_min = delai_jour 
                                    else:
                                        if delai_jour < delai_min:
                                            delai_min = delai_jour 
                                          
                    if delai_trouve:
                        delai = delai_min
                        date_aff_calc = apik_calendar.calcul_date_ouvree(today_ferie, delai, company_id.nb_weekend_days, company_id.zone_geo, typedate)  
                        date_a_aff = str(date_aff_calc.date())
                        date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                        affich = "Délai de sous-traitance"
                        delai_ok = True
                        delai_reappro = True
                        alerte = False
                    else:
                        delai = 0
                        date_affiche = ' '
                        affich = "Pas de délai de sous-traitance existant" 
                        delai_ok = False  
                        delai_reappro = False
                        alerte = True   
                else:
                    delai = 0
                    date_affiche = ' '
                    affich = "Consulter les appros"
                    delai_ok = False  
                    delai_reappro = False
                    alerte = True    

                detail_delai = {'article': line.product_id.name,
                                    'qty': line.product_uom_qty,
                                    'delai': delai,
                                    'affich': affich,
                                    'date_affiche': date_affiche,
                                    'delai_ok': delai_ok,
                                    'delai_reappro': delai_reappro,
                                    'alerte': alerte}
                rows_delai.append(detail_delai)  
                if delai_ok:
                    line.component_replenishment_time = delai
                    line.component_available = 'yes'
                    line.detail_component = json.dumps(rows_delai)
                    if alerte == True:
                        line.display_alert_message_compo = True  
                    else:
                        line.display_alert_message_compo = False  
                else:
                    if delai_reappro:
                        line.component_replenishment_time = delai 
                    else:
                        line.component_replenishment_time = 0 
                    line.component_available = 'no'
                    line.assembly_time_ok = False
                    line.detail_component = json.dumps(rows_delai)
                    if alerte == True:
                        line.display_alert_message_compo = True 
                    else:
                        line.display_alert_message_compo = False   
            else:    
                article_sous_traite = self.recherche_article_sous_traite(line)
                if article_sous_traite:                    
                    # 
                    # Articles sous-traités avec nomenclature 
                    #
                    delai_min = 0
                    delai_trouve = False
                    alerte = False
                    if line.product_id.seller_ids:
                        for seller in line.product_id.seller_ids:
                            if seller.is_subcontractor:
                                if seller.name:
                                    delais_sst = delai_sst_obj.search([('partner_id','=',seller.name.id)]) 
                                    if delais_sst:
                                        delai_trouve = False
                                        delai_jour = 0
                                        for delai in delais_sst:
                                            if line.product_uom_qty < delai.quantity_below:
                                                delai_jour = delai.production_time
                                                delai_trouve = True 
                                                break
                                        if delai_trouve == True:
                                            if delai_min == 0:
                                                delai_min = delai_jour 
                                            else:
                                                if delai_jour < delai_min:
                                                    delai_min = delai_jour 
                                        #else:
                                        #    delai_min = 0           
                                    #else:
                                    #    delai_min = 0 
                    if delai_trouve:
                        delai = delai_min
                        date_aff_calc = apik_calendar.calcul_date_ouvree(today_ferie, delai, company_id.nb_weekend_days, company_id.zone_geo, typedate)  
                        date_a_aff = str(date_aff_calc.date())
                        date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                        affich = "Délai de sous-traitance"
                        delai_ok = True
                        delai_reappro = True
                        alerte = False
                    else:
                        affich = "Consulter les appros"
                        delai = 0
                        date_affiche = ' '
                        delai_ok = False
                        delai_reappro = False
                        alerte = True



                    detail_delai = {'article': line.product_id.name,
                                        'qty': line.product_uom_qty,
                                        'delai': delai,
                                        'affich': affich,
                                        'date_affiche': date_affiche,
                                        'delai_ok': delai_ok,
                                        'delai_reappro': delai_reappro,
                                        'alerte': alerte}
                    rows_delai.append(detail_delai)  
                    if delai_ok:
                        line.component_replenishment_time = delai
                        line.component_available = 'yes'
                        line.detail_component = json.dumps(rows_delai)
                        if alerte == True:
                            line.display_alert_message_compo = True  
                        else:
                            line.display_alert_message_compo = False  
                    else:
                        if delai_reappro:
                            line.component_replenishment_time = delai 
                        else:
                            line.component_replenishment_time = 0 
                        line.component_available = 'no'
                        line.detail_component = json.dumps(rows_delai)
                        if alerte == True:
                            line.display_alert_message_compo = True 
                        else:
                            line.display_alert_message_compo = False     
                else:
                    # 
                    # Articles avec nomenclature 
                    #
                    if line.product_id.bom_count > 0:
                        # 
                        # On recherche la disponibité des composants
                        #
                        for bom in line.product_id.bom_ids:
                            if bom.type != 'normal':
                                continue
                            else:
                                for bom_line in bom.bom_line_ids:
                                    delai = 0
                                    affich = ''
                                    date_affiche = ' '
                                    alerte = False  
                                    delai_ok = True
                                    delai_reappro = False
                                    article_present = self.recherche_presence_variante_dans_nomenclature(line, bom_line)
                                    if article_present:
                                        #
                                        # On regarde si article de sous_traitance dans les tarifs fournisseur du composant.
                                        # 

                                        #
                                        # On traite les articles sous-traités sans stock 
                                        #
                                        if bom_line.product_id.art_sst_no_stock:
                                            delai_min = 0
                                            delai_trouve = False
                                            alerte = False
                                            besoin_qty = line.product_uom_qty * bom_line.product_qty  
                                            if bom_line.product_id.seller_ids:                                        
                                                for seller in bom_line.product_id.seller_ids:
                                                    if seller.name:
                                                        delais_sst = delai_sst_obj.search([('partner_id','=',seller.name.id)]) 
                                                        if delais_sst:
                                                            delai_trouve = False
                                                            delai_jour = 0
                                                            for delai in delais_sst:
                                                                if besoin_qty < delai.quantity_below:
                                                                    delai_jour = delai.production_time
                                                                    delai_trouve = True 
                                                                    break
                                                            if delai_trouve == True:
                                                                if delai_min == 0:
                                                                    delai_min = delai_jour 
                                                                else:
                                                                    if delai_jour < delai_min:
                                                                        delai_min = delai_jour 
                                                if delai_trouve:
                                                    delai = delai_min
                                                    date_aff_calc = apik_calendar.calcul_date_ouvree(today_ferie, delai, company_id.nb_weekend_days, company_id.zone_geo, typedate)  
                                                    date_a_aff = str(date_aff_calc.date())
                                                    date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                                    affich = "Délai de sous-traitance"
                                                    delai_ok = True
                                                    delai_reappro = True
                                                    alerte = False
                                                else:
                                                    delai = 0
                                                    date_affiche = ' '
                                                    affich = "Pas de délai de sous-traitance existant" 
                                                    delai_ok = False  
                                                    delai_reappro = False
                                                    alerte = True       
                                            else:
                                                delai = 0
                                                date_affiche = ' '
                                                affich = "Consulter les appros"
                                                delai_ok = False  
                                                delai_reappro = False
                                                alerte = True  
                                            detail_delai = {'article': bom_line.product_id.name,
                                                            'qty': besoin_qty,
                                                            'delai': delai,
                                                            'affich': affich,
                                                            'date_affiche': date_affiche,
                                                            'delai_ok': delai_ok,
                                                            'delai_reappro': delai_reappro,
                                                            'alerte': alerte}
                                            rows_delai.append(detail_delai) 
                                        else:
                                            sous_traitance = False 
                                            if bom_line.product_id.seller_ids:
                                                for seller in bom_line.product_id.seller_ids:
                                                    if seller.is_subcontractor:
                                                        sous_traitance = True 
                                                        break     
                                            if sous_traitance:
                                                #
                                                # On traite le cas 2.4.1.2
                                                # 
                                                delai_min = 0
                                                delai_trouve = False
                                                besoin_qty = line.product_uom_qty  
                                                if bom_line.product_id.seller_ids:
                                                    for seller in bom_line.product_id.seller_ids:
                                                        if seller.is_subcontractor:
                                                            if seller.name:
                                                                delais_sst = delai_sst_obj.search([('partner_id','=',seller.name.id)]) 
                                                                if delais_sst:
                                                                    delai_trouve = False
                                                                    delai_jour = 0
                                                                    for delai in delais_sst:
                                                                        if line.product_uom_qty < delai.quantity_below:
                                                                            delai_jour = delai.production_time
                                                                            delai_trouve = True 
                                                                            break
                                                                    if delai_trouve == True:
                                                                        if delai_min == 0:
                                                                            delai_min = delai_jour                                                                         
                                                                        else:
                                                                            if delai_jour < delai_min:
                                                                                delai_min = delai_jour 
                                                if delai_trouve:
                                                    delai = delai_min
                                                    date_aff_calc = apik_calendar.calcul_date_ouvree(today_ferie, delai, company_id.nb_weekend_days, company_id.zone_geo, typedate)  
                                                    date_a_aff = str(date_aff_calc.date())
                                                    date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                                    affich = "Délai de sous-traitance"
                                                    delai_ok = True
                                                    delai_reappro = True
                                                    alerte = False
                                                else:
                                                    delai = 0
                                                    date_affiche = ' '
                                                    affich = "Pas de délai de sous-traitance existant" 
                                                    delai_ok = False  
                                                    delai_reappro = False
                                                    alerte = True    
                                                detail_delai = {'article': bom_line.product_id.name,
                                                            'qty': besoin_qty,
                                                            'delai': delai,
                                                            'affich': affich,
                                                            'date_affiche': date_affiche,
                                                            'delai_ok': delai_ok,
                                                            'delai_reappro': delai_reappro,
                                                            'alerte': alerte}
                                                rows_delai.append(detail_delai)                                              
                                            else:  
                                                if bom_line.product_id.type == 'product':  
                                                    besoin_qty = line.product_uom_qty * bom_line.product_qty  
                                                    qty_en_stock = self.recherche_quantite_en_stock(bom_line.product_id,line.order_id.warehouse_id.lot_stock_id)
                                                    if qty_en_stock >= besoin_qty:
                                                        delai = 0
                                                        date_a_aff = str(today)
                                                        date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                                        affich = "Disponible le"
                                                        delai_ok = True
                                                        delai_reappro = True
                                                        alerte = False    
                                                    else:  
                                                        qty_virtual = self.recherche_quantite_virtual(bom_line.product_id, line.order_id.warehouse_id)
                                                        if bom_line.product_id.id == 498:
                                                            logger.info("Quantité virtuelle : " + str(qty_virtual))

                                                        if qty_virtual >= besoin_qty:   
                                                            delai = 0
                                                            delai_date = self.recherche_date_dispo_qte(bom_line.product_id, besoin_qty,line.order_id.warehouse_id)    
                                                            if bom_line.product_id.id == 498:
                                                                logger.info("Délai date : " + str(delai_date))

                                                            #logger.info("Cas 1 - Délai date trouve et inférieur à la date de la commande")
                                                            #logger.info(delai_date)
                                                            #logger.info(line.order_id.date_order)                                    

                                                            if delai_date:
                                                                #if delai_date >= line.order_id.date_order:
                                                                if delai_date.date() >= today:    
                                                                    date_a_aff = str(delai_date.date())
                                                                    date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                                                    delta = delai_date.date() - today
                                                                    delai = delta.days 
                                                                    jours_moins = self.calcul_week_end_et_ferie(today,delai_date.date())    
                                                                    if jours_moins >= 1:
                                                                        if delai > jours_moins:
                                                                            delai = delai - jours_moins
                                                                        else:
                                                                            delai = 0
                                                                    affich = "Disponible le"
                                                                    delai_ok = False
                                                                    delai_reappro = True
                                                                    alerte = False
                                                                else:                                                    
                                                                    delai = company_id.delai_dispo_fournisseur
                                                                    date_aff_calc = apik_calendar.calcul_date_ouvree(today_ferie, delai, company_id.nb_weekend_days, company_id.zone_geo, typedate)  
                                                                    date_a_aff = str(date_aff_calc.date())
                                                                    date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                                                    affich = "Dispo chez le fournisseur"
                                                                    delai_ok = False
                                                                    delai_reappro = True
                                                                    alerte = False    
                                                            else:
                                                                affich = "Consulter les appros"
                                                                delai = 0
                                                                date_affiche = ' '
                                                                delai_ok = False
                                                                delai_reappro = False
                                                                alerte = True
                                                        else:                                                        
                                                            #
                                                            # On traite le cas 2.4.1.1
                                                            #  
                                                            besoin_qty = line.product_uom_qty * bom_line.product_qty  
                                                            date_delai_calc = self.recherche_date_dispo_qte(bom_line.product_id, besoin_qty,line.order_id.warehouse_id)    
                                                            
                                                            if bom_line.product_id.id == 498:
                                                                logger.info("__________________ 3 _________")
                                                                logger.info(date_delai_calc)
                                                                logger.info("______________________________") 
                                                            
                                                            #logger.info("Cas 2 - Délai_calc_date trouve et inférieur à la date du jour")
                                                            #logger.info(delai_date)
                                                            #logger.info(today)

                                                            if not date_delai_calc:
                                                                affich = "Consulter les appros"
                                                                delai = 0
                                                                date_affiche = ' '
                                                                delai_ok = False
                                                                delai_reappro = False
                                                                alerte = True
                                                            else:    
                                                                if date_delai_calc.date() < today:
                                                                    affich = "Dispo chez le fournisseur"
                                                                    delai = company_id.delai_dispo_fournisseur
                                                                    date_aff_calc = apik_calendar.calcul_date_ouvree(today_ferie, delai, company_id.nb_weekend_days, company_id.zone_geo, typedate)  
                                                                    date_a_aff = str(date_aff_calc.date())
                                                                    date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                                                    delai_ok = True
                                                                    delai_reappro = True
                                                                    alerte = False
                                                                else:
                                                                    date_a_aff = str(date_delai_calc.date())
                                                                    #date_affiche = date_a_aff[5:7]+"/"+date_a_aff[8:]+'/'+date_a_aff[0:4]
                                                                    date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                                                    affich = "Disponible le" 
                                                                    delta = date_delai_calc.date() - today
                                                                    delai = delta.days 
                                                                    jours_moins = self.calcul_week_end_et_ferie(today,date_delai_calc.date())    
                                                                    if jours_moins >= 1:
                                                                        if delai > jours_moins:
                                                                            delai = delai - jours_moins
                                                                        else:
                                                                            delai = 0
                                                                    delai_ok = False
                                                                    delai_reappro = True
                                                                    alerte = False  
                                                    detail_delai = {'article': bom_line.product_id.name,
                                                            'qty': besoin_qty,
                                                            'delai': delai,
                                                            'affich': affich,
                                                            'date_affiche': date_affiche,
                                                            'delai_ok': delai_ok,
                                                            'delai_reappro': delai_reappro,
                                                            'alerte': alerte}
                                                    rows_delai.append(detail_delai) 
                                            '''                          
                                            detail_delai = {'article': bom_line.product_id.name,
                                                            'qty': besoin_qty,
                                                            'delai': delai,
                                                            'affich': affich,
                                                            'date_affiche': date_affiche,
                                                            'delai_ok': delai_ok,
                                                            'delai_reappro': delai_reappro,
                                                            'alerte': alerte}
                                            rows_delai.append(detail_delai) 
                                            '''
                                break  
                                            
                        delai_ok = True
                        delai_rea = True
                        delai_max = 0
                        alerte_popup = False
                        for row in rows_delai:
                            articleligne = row['article']
                            qtyligne = row['qty']
                            delailigne = row['delai']
                            affichligne = row['affich']
                            delaiokligne = row['delai_ok']
                            delaireaokligne = row['delai_reappro']
                            dateafficheligne = row['date_affiche']
                            alerte = row['alerte']
                            if not delaiokligne :
                                delai_ok = False
                            else:
                                if delailigne > delai_max:
                                    delai_max = delailigne
                            if not delaireaokligne: 
                                delai_rea = False
                            else:
                                if delailigne > delai_max:
                                    delai_max = delailigne       
                            if alerte == True:
                                alerte_popup = True
                        if delai_ok:
                            line.component_replenishment_time = delai_max                    
                            line.component_available = 'yes'
                            line.detail_component = json.dumps(rows_delai)
                            if alerte_popup == True:
                                line.display_alert_message_compo = True
                            else:
                                line.display_alert_message_compo = False    
                        else:
                            if delai_rea:
                                line.component_replenishment_time = delai_max 
                            else:
                                line.component_replenishment_time = 0    
                            line.component_available = 'no'
                            line.assembly_time_ok = False
                            line.detail_component = json.dumps(rows_delai)
                            if alerte_popup == True:
                                line.display_alert_message_compo = True 
                            else:
                                line.display_alert_message_compo = False                           
                    else:
                        if line.product_id.type == 'service' or line.product_id.type == 'consu' :
                            delai = 0 #(-1) * company_id.delai_debut_disponibilite
                            date_a_aff = str(today)
                            date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                            affich = "Disponible le"
                            delai_ok = True
                            delai_reappro = False
                            alerte = False     
                        else:    
                            # 
                            # Pas une nomenclature, on recherche les éléments sur l'article 
                            #
                            alerte = False 
                            besoin_qty = line.product_uom_qty 
                            qty_en_stock = self.recherche_quantite_en_stock(line.product_id,line.order_id.warehouse_id.lot_stock_id)
                            #if line.qty_available_today >= besoin_qty:
                            if qty_en_stock >= besoin_qty:    
                                delai = 0
                                date_a_aff = str(today)
                                date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                affich = "Disponible le"
                                delai_ok = True
                                delai_reappro = False
                                alerte = False    
                            else: 
                                if line.virtual_available_at_date >= besoin_qty:    
                                    delai_date = self.recherche_date_dispo_qte(line.product_id, besoin_qty, line.order_id.warehouse_id)    
                                    
                                    #logger.info("Cas 3 - Délai date trouve et inférieur à la date de la commande")
                                    #logger.info(delai_date)
                                    #logger.info(line.order_id.date_order)
                                    
                                    if delai_date:
                                        #if delai_date >= line.order_id.date_order:
                                        if delai_date.date() >= today:     
                                            date_a_aff = str(delai_date.date())
                                            date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                            delta = delai_date.date() - today
                                            delai = delta.days 
                                            jours_moins = self.calcul_week_end_et_ferie(today,delai_date.date())    
                                            if jours_moins >= 1:
                                                if delai > jours_moins:
                                                    delai = delai - jours_moins
                                                else:
                                                    delai = 0
                                            affich = "Disponible le"
                                            delai_ok = False
                                            delai_reappro = True
                                            alerte = False
                                        else:
                                            delai = company_id.delai_dispo_fournisseur
                                            date_aff_calc = apik_calendar.calcul_date_ouvree(today_ferie, delai, company_id.nb_weekend_days, company_id.zone_geo, typedate)  
                                            date_a_aff = str(date_aff_calc.date())
                                            date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                            affich = "Dispo chez le fournisseur"
                                            delai_ok = False
                                            delai_reappro = True
                                            alerte = False              
                                    else:
                                        affich = "Consulter les appros"
                                        delai = 0 
                                        date_affiche = ' '
                                        delai_ok = False
                                        delai_reappro = False
                                        alerte = True
                                else:
                                    date_delai_calc = self.recherche_date_dispo_qte(line.product_id, besoin_qty, line.order_id.warehouse_id)    
                                    
                                    #logger.info("Cas 4 - Délai_calc_date trouve et inférieur à la date du jour")
                                    #logger.info(date_delai_calc)
                                    #logger.info(today)
                                    
                                    if not date_delai_calc:
                                        affich = "Consulter les appros"
                                        date_affiche = ' '
                                        delai = 0
                                        delai_ok = False
                                        delai_reappro = False
                                        alerte = True
                                    else:    
                                        if date_delai_calc.date() < today:
                                            affich = "Dispo chez le fournisseur"
                                            delai = company_id.delai_dispo_fournisseur
                                            date_aff_calc = apik_calendar.calcul_date_ouvree(today_ferie, delai, company_id.nb_weekend_days, company_id.zone_geo, typedate)  
                                            date_a_aff = str(date_aff_calc.date())
                                            date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                            delai_ok = True
                                            delai_reappro = True
                                            alerte = False
                                        else:
                                            date_a_aff = str(date_delai_calc.date())
                                            date_affiche = date_a_aff[8:]+"/"+date_a_aff[5:7]+'/'+date_a_aff[0:4]
                                            affich = "Disponible le" 
                                            delta = date_delai_calc.date() - today
                                            delai = delta.days 
                                            jours_moins = self.calcul_week_end_et_ferie(today,date_delai_calc.date())    
                                            if jours_moins >= 1:
                                                if delai > jours_moins:
                                                    delai = delai - jours_moins
                                                else:
                                                    delai = 0
                                            delai_ok = True 
                                            delai_reappro = True
                                            alerte = False   

                        detail_delai = {'article': line.product_id.name,
                                        'qty': line.product_uom_qty,
                                        'delai': delai,
                                        'affich': affich,
                                        'date_affiche': date_affiche,
                                        'delai_ok': delai_ok,
                                        'delai_reappro': delai_reappro,
                                        'alerte': alerte}
                        rows_delai.append(detail_delai)  
                        
                        if delai_ok:
                            line.component_replenishment_time = delai
                            line.component_available = 'yes'
                            line.detail_component = json.dumps(rows_delai)                         
                        else:
                            if delai_reappro:
                                line.component_replenishment_time = delai 
                            else:
                                line.component_replenishment_time = 0 
                            line.component_available = 'no'
                            line.detail_component = json.dumps(rows_delai)
                        if alerte == True:
                            line.display_alert_message_compo = True  
                        else:
                            line.display_alert_message_compo = False  

            #       
            # Jusqu'ici
            #                        
            if line.display_alert_message_compo or line.display_alert_message_montage:
                line.display_alert_message = True 
            else:
                line.display_alert_message = False    

    ###########################################################
    #   On recherche la date de disponibilté la plus courte   #
    ###########################################################
    def recherche_date_dispo_qte(self, product_id, qty, warehouse_id):  
        stock_move_obj = self.env['stock.move']
        stock_quant_obj = self.env['stock.quant']
        stock_qty = 0
        # 
        # On recherche la quantité en stock 
        # 
        quants = stock_quant_obj.search([('product_id','=', product_id.id),('on_hand','=',True),('location_id','=',warehouse_id.lot_stock_id.id)]) 
        if quants:
            for quant in quants:
                stock_qty += quant.quantity    
                #stock_qty += quant.available_quantity   

                if product_id.id == 498:
                    logger.info("===================== 3 ============")
                    logger.info(quant.available_quantity)
                    logger.info(quant.inventory_quantity)
                    logger.info(quant.quantity)
                    logger.info(quant.reserved_quantity)
                    logger.info(quant.location_id.name)
                    logger.info(quant.lot_id.name)
                    logger.info(stock_qty)
                    logger.info("====================================")
        else:
            stock_qty = 0 

        stock_moves = stock_move_obj.search([('product_id','=', product_id.id),('state','not in',['done','cancel'])], order='date asc' ) 
        date_dispo = False        
        if stock_moves:
            #
            # On recherche la somme des sorties (besoin en cours)
            # 
            qte_out_besoin = 0
            for move in stock_moves:
                if move.warehouse_id.id == warehouse_id.id or not move.warehouse_id.id:                     
                    if move.location_id.id == warehouse_id.lot_stock_id.id:
                        #  
                        # Mouvement de sortie 
                        #      
                        qte_out_besoin += move.product_uom_qty

            #
            # On recherche la première date de dispo qui couvre les besoins en cours et ma demande
            # 
            date_retour = False 
            for move in stock_moves:
                if product_id.id == 498 and move.warehouse_id.id == warehouse_id.id: 
                    logger.info("===================== 4 ============")
                    logger.info("No Mouvement Id : " + str(move.id))
                    logger.info("Product_id  : " + str(move.product_id.id))
                    logger.info("Nom : " + move.name)
                    logger.info("Etat : " + str(move.state))
                    logger.info("Origine : " + str(move.origin))
                    logger.info("Warehouse : " + str(move.warehouse_id.name))
                    logger.info("Location : " + str(move.location_id.name))
                    logger.info("Location dest : " + str(move.location_dest_id.name))
                    logger.info("Ligne vente : " + str(move.sale_line_id.id))
                    logger.info("Ligne achat : " + str(move.purchase_line_id.id))
                    logger.info("Qte move : " + str(move.product_uom_qty))
                    logger.info("Qte done : " + str(move.quantity_done))
                    logger.info("Qte resa : " + str(move.reserved_availability))
                    logger.info("Qte dispo : " + str(move.should_consume_qty))
                    logger.info("Qte réelle : " + str(move.product_qty))  
                    logger.info("qté prévue : " + str(move.availability))        
                    logger.info("Qté prévision : " + str(move.forecast_availability)) 
                    logger.info("Qté besoin : " + str(qte_out_besoin))             
                    logger.info("Date : " + str(move.date))
                    logger.info("====================================")
                if move.warehouse_id.id == warehouse_id.id or not move.warehouse_id.id: 
                    if move.location_dest_id.id == warehouse_id.lot_stock_id.id:
                        #  
                        # Mouvement d'entrée 
                        #
                        stock_qty += move.product_uom_qty

                        qte_restante = stock_qty - qte_out_besoin
                        if product_id.id == 498 and move.warehouse_id.id == warehouse_id.id: 
                            logger.info("Qté restante : " + str(qte_restante))
                        if qte_restante >= qty: 
                            date_retour = move.date 
                            if product_id.id == 498 and move.warehouse_id.id == warehouse_id.id: 
                                logger.info("Date retour : " + str(move.date ))
                            return date_retour
            return date_retour
        else:
            date_retour = False    
        return date_retour   

    ####################################################################################################
    #   On regarde si la variante de la ligne est prévue dans la variante de la ligne de nomenclature  #
    ####################################################################################################
    def recherche_presence_variante_dans_nomenclature_old(self, sale_line, bom_line):
        art_present = False
        if sale_line.product_id.product_template_attribute_value_ids:
            for var_ligne in sale_line.product_id.product_template_attribute_value_ids:
                if bom_line.bom_product_template_attribute_value_ids:
                    for var_bom in bom_line.bom_product_template_attribute_value_ids:  
                        if var_ligne.id == var_bom.id:
                            art_present = True   
                else:
                    art_present = True        
        else:
            art_present = True                    
        return art_present    

    #############################################################################
    #   On recherche le nb de jours de week-end et jours fériés entre 2 dates   #
    #############################################################################
    def calcul_week_end_et_ferie(self, date_debut, date_fin):  
        nb_jr_moins = 0        
        if date_debut >= date_fin:
           nb_jr_moins = 0
        else:
            date_a_controler = date_debut
            while date_a_controler < date_fin:
                jour_semaine = date_a_controler.weekday()
                if jour_semaine in [5, 6]:
                    nb_jr_moins += 1
                else:
                    date_ferie = apik_calendar.controle_jour_ferie(date_a_controler, 'metropole', 'date') 
                    if date_ferie:
                        nb_jr_moins += 1  
                date_a_controler = date_a_controler + datetime.timedelta(days=1) 
        return nb_jr_moins   

    ####################################################################################################
    #   On regarde si la variante de la ligne est prévue dans la variante de la ligne de nomenclature  #
    ####################################################################################################
    def recherche_presence_variante_dans_nomenclature(self, sale_line, bom_line):
        art_present = False
        if sale_line.product_id.product_template_attribute_value_ids:
            for var_ligne in sale_line.product_id.product_template_attribute_value_ids:
                if bom_line.bom_product_template_attribute_value_ids:  
                    #                   
                    # On recherche le nombre de caractéristiques de la ligne de nomeclature  
                    # 
                    # Si multiple    
                    #   
                    if len(bom_line.bom_product_template_attribute_value_ids)>1:
                        #
                        # On recherche si toutes les caractéristiques de la ligne de nomenclature sont sur la ligne de commande
                        #
                        '''
                        if bom_line.product_id.id == 498:    
                            logger.info("variantes bom ligne")
                            logger.info(len(bom_line.bom_product_template_attribute_value_ids))
                            logger.info(bom_line.bom_product_template_attribute_value_ids) 
                            logger.info(len(sale_line.product_id.product_template_attribute_value_ids))
                            logger.info(sale_line.product_id.product_template_attribute_value_ids)  
                        '''
                        caract_multi = False
                        nb_caract_recherche = len(bom_line.bom_product_template_attribute_value_ids) 
                        nb_caract_trouve = 0
                        for bom_multi in bom_line.bom_product_template_attribute_value_ids:  
                            caract_trouve = False
                            for ligne_multi in sale_line.product_id.product_template_attribute_value_ids:
                                if bom_multi.id == ligne_multi.id:
                                    caract_trouve = True 
                                    break
                            if caract_trouve:
                                nb_caract_trouve += 1  
                                
                        if nb_caract_recherche == nb_caract_trouve:
                            art_present = True
                        else:
                            art_present = False    
                    # 
                    # sans caractéristique ou simple 
                    # 
                    else:    
                        for var_bom in bom_line.bom_product_template_attribute_value_ids:  
                            if var_ligne.id == var_bom.id:
                                art_present = True   
                else:
                    art_present = True        
        else:
            art_present = True                    
        return art_present    

    ################################################
    #   On regarde si l'article est sous-traités   #
    ################################################
    def recherche_article_sous_traite(self, sale_line):
        art_sst = False
        if sale_line.product_id.seller_ids:
            for seller in sale_line.product_id.seller_ids:
                if seller.is_subcontractor:
                    art_sst = True 
                    break  
        else:
            art_sst = False    
        return art_sst                   

    ################################################
    #   Calcul de la quantité en stock par dépot   #
    ################################################
    def recherche_quantite_en_stock(self,product_id,lot_stock_id):
        stock_quant_obj = self.env['stock.quant']
        qty = 0
        quants = stock_quant_obj.search([('product_id','=', product_id.id),('on_hand','=',True),('location_id','=',lot_stock_id.id)]) 
        if quants:
            for quant in quants:                
                qty += quant.available_quantity    
        else:
            qty = 0 
        return qty   

    ################################################
    #   Calcul de la quantité virtual par dépot    #
    ################################################
    def recherche_quantite_virtual(self, product_id, warehouse_id):
        stock_move_obj = self.env['stock.move']
        stock_qte = 0        
        stock_moves = stock_move_obj.search([('product_id','=', product_id.id),('state','not in',['done','cancel'])], order='date asc' ) 
        if stock_moves:
            for move in stock_moves:  
                if move.warehouse_id.id == warehouse_id.id or not move.warehouse_id.id: 
                    if move.location_dest_id.id == warehouse_id.lot_stock_id.id:
                        #  
                        # Mouvement d'entrée 
                        #
                        stock_qte += move.product_uom_qty
                        #stock_qte -= move.reserved_availability
                    if move.location_id.id == warehouse_id.lot_stock_id.id:
                        #  
                        # Mouvement de sortie 
                        #      
                        stock_qte -= move.product_uom_qty
        else:
            stock_qte = 0   
        return stock_qte         
