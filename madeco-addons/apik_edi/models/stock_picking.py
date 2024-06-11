# -*- coding: utf-8 -*-

#import json
import ftplib
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime, timedelta
from tempfile import TemporaryFile
from ftplib import FTP
import base64
import io
import pysftp
import logging
logger = logging.getLogger(__name__)

from odoo.addons.apik_calendar.models import apik_calendar


def maxi(chaine,size):
    """
    Méthode qui retourne une chaine passée en paramètres de la taille demandée
    **Paramètres**
    **chaine**
        Chaine de caractères. Si la chaine n’est pas du type STR, une chaine contenant des espaces de la taille demandée est retournée
    **size**
        Entier, qui donne la taille à retourner
    Retourne une chaine de caractère contenant le nombre de caractères passés en paramètres. 
    Si la chaine est plus grande, une chaine tronquée est retournée. 
    Si la chaine est plus petite, des espaces sont ajoutés. Si la chaine n’est pas du type STR, alors une chaine d’espaces est retournée.
    """
    if type(chaine) == str:
        if len(chaine)>size:
            return chaine[:size]
        else:
            for i in range(size-len(chaine)):
                chaine += " "
            return chaine
    else:
        chaine = ""
        for i in range(size):
            chaine += " "
        return chaine 



class Picking(models.Model):
    _inherit = 'stock.picking' 
    
    commande_edi = fields.Boolean(string="Commande EDI", default=False, compute="_compute_commande_edi")    
    desadv_edi_genere = fields.Boolean(string="DESADV EDI généré", copy=False, default=False)
    desadv_edi_envoye = fields.Boolean(string="DESADV EDI envoyé", copy=False, default=False)
    nb_palette_edi = fields.Integer(string="Nb palette edi", copy=False, default=0, compute="_calcul_nb_palette_edi")
    nb_roll_edi = fields.Integer(string="Nb roll edi", copy=False, default=0)
    nb_packet_edi = fields.Integer(string="Nb colis edi", copy=False, default=0, compute="_calcul_nb_packet_edi")
    no_bl_edi_desadv = fields.Char(string="No du BL pour DESADV Edi", copy=False)

    #########################################################################################
    #                                                                                       #
    #                               _calcul_nb_palette_edi                                  #
    #                                                                                       #
    ######################################################################################### 
    @api.depends('move_line_ids_without_package','move_line_ids')
    def _calcul_nb_palette_edi(self):
        for pick in self:
            if pick.commande_edi:
                nb_pal = 0
                listepal = [] 
                #for line in pick.move_line_ids_without_package: 
                for line in pick.move_line_ids:     
                    if line.result_package_id: 
                        if line.result_package_id.packaging_id.support_expedition:
                            exist = False
                            pal = line.result_package_id.id 
                            for dico in listepal:
                                if pal == dico['pal']:
                                    exist = True                            
                            if not exist:
                                data = {
                                        'pal': line.result_package_id.id,
                                        }
                                listepal.append(data)
                                nb_pal += 1 
                pick.nb_palette_edi = nb_pal
            else:
                pick.nb_palette_edi = 0

    #########################################################################################
    #                                                                                       #
    #                               _calcul_nb_roll_edi                                     #
    #                                                                                       #
    ######################################################################################### 
    @api.depends('move_line_ids_without_package','move_line_ids','package_level_ids_details')
    def _calcul_nb_packet_edi(self):
        for pick in self:
            if pick.commande_edi:
                nb_colis = 0
                #listecolis = [] 
                for colis in pick.package_level_ids_details: 
                    if colis.package_id: 
                        #exist = False
                        #col = line.package_id.id 
                        #for dico in listecolis:
                        #    if col == dico['col']:
                        #        exist = True                            
                        #if not exist:
                        #    data = {
                        #            'col': line.package_id.id,
                        #            }
                        #    listecolis.append(data)
                        if not colis.package_id.packaging_id.support_expedition:
                            nb_colis += 1                 
                pick.nb_packet_edi = nb_colis
            else:
                pick.nb_packet_edi = 0

    #########################################################################################
    #                                                                                       #
    #                                _compute_commande_edi                                  #
    #                                                                                       #
    #########################################################################################     
    @api.depends('origin', 'create_date', 'write_date')
    def _compute_commande_edi(self):
        sale_obj = self.env['sale.order']
        for pick in self:
            if pick.origin:
                sale = sale_obj.search([('name', '=', pick.origin)],limit=1)
                if len(sale)>0:
                    if sale.commande_edi:
                        pick.commande_edi = True
                    else:
                        pick.commande_edi = False
                else:
                    pick.commande_edi = False
            else:
                pick.commande_edi = False
    
    #########################################################################################
    #                                                                                       #
    #                                     Export DESADV                                     #
    #                                                                                       #
    #########################################################################################     
    def button_validate(self): 
        sale_obj = self.env['sale.order']   
        resultat = super().button_validate()

        if resultat == True:
            for pick in self:
                if pick.state == 'done':
                    if pick.picking_type_id.desadv_edi:
                        if pick.origin:
                            #
                            # On regarde si le client est en EDI et si la gestion des DESADV EDI est active
                            #    
                            sale = sale_obj.search([('name', '=', pick.origin)],limit=1)
                            if len(sale)>0:  
                                if sale.partner_acheteur_id.client_edi:
                                    if sale.partner_acheteur_id.edi_desadv:                        
                                        if sale.commande_edi:
                                            #
                                            # On génére l'envoi du DESADV EDI   
                                            #
                                            for rec in pick:
                                                rec.action_update_packages_weight()

                                            pick.desadv_edi_genere = True
                                            pick.export_desadv_edi_picking()
                                        else:
                                            pick.desadv_edi_genere = False     
                                    else:    
                                        pick.desadv_edi_genere = False                                 
                                else:
                                    pick.desadv_edi_genere = False  
                            else:
                                pick.desadv_edi_genere = False               
        return resultat

    def export_desadv(self):
        export_ok = False 

    #########################################################################################
    #                                                                                       #
    #                                     Export DESADV                                     #
    #                                                                                       #
    #########################################################################################      
    def export_desadv_edi_picking(self):           
        self.ensure_one()
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company   

        sale_obj = self.env['sale.order']
        partner_obj = self.env['res.partner']
        picking_obj = self.env['stock.picking']
        
        nb_enreg = 0
        rows_to_write = []
        name_picking = ''

        for picking in self: 
            #
            # On calcule le nombre de palette et le nombre de colis
            # 
            picking._calcul_nb_palette_edi()
            picking._calcul_nb_packet_edi()
            name_picking = picking.name
            #
            # On recherche la commande de vente rattaché à la livraison
            #
            if picking.origin:
                sale = sale_obj.search([('name', '=', picking.origin)],limit=1)                
                if len(sale)>0: 
                    if sale.commande_edi: 
                        if sale.partner_acheteur_id.client_edi:
                            if sale.partner_acheteur_id.edi_desadv:   
                                nb_lig_desadv = 0        
                                #
                                # On génére l'enregistrement Entête
                                #
                                enreg_ent = self.export_desadv_entete(picking,sale)
                                if enreg_ent:
                                    rows_to_write.append(enreg_ent)
                                    nb_enreg = nb_enreg + 1
                                #
                                # On génère l'enregistrement NAD+BY
                                # 
                                if sale.partner_acheteur_id:
                                    enreg_par = self.export_desadv_param('BY',picking,sale) 
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1 
                                #
                                # On génère l'enregistrement NAD+SU
                                # 
                                if sale.partner_vendeur_id:
                                    enreg_par = self.export_desadv_param('SU',picking,sale)
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1  
                                #
                                # On génère l'enregistrement NAD+DP
                                # 
                                if sale.partner_livre_a_id:
                                    enreg_par = self.export_desadv_param('DP',picking,sale)
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1  
                                #
                                # On génère l'enregistrement NAD+UC
                                # 
                                if sale.partner_final_id:
                                    enreg_par = self.export_desadv_param('UC',picking,sale)
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1  
                                #
                                # On génère l'enregistrement NAD+IV
                                # 
                                if sale.partner_facture_a_id:
                                    enreg_par = self.export_desadv_param('IV',picking,sale)
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1  
                                #
                                # On génère l'enregistrement NAD+OB
                                # 
                                if sale.partner_commande_par_id:
                                    enreg_par = self.export_desadv_param('OB',picking,sale)
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1 
                                #
                                # On génère l'enregistrement NAD+PR
                                # 
                                if sale.partner_paye_par_id:
                                    enreg_par = self.export_desadv_param('PR',picking,sale)
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1 
                                #
                                # On génère l'enregistrement NAD+UD
                                # 
                                if sale.partner_final_ud_id:
                                    enreg_par = self.export_desadv_param('UD',picking,sale)
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1              
                              
                                #
                                # On génère les enregistrements palettes
                                # 
                                if picking.nb_palette_edi >= 1: 
                                    listepal = []  
                                    #for line in picking.move_line_ids_without_package:  
                                    for line in picking.move_line_ids: 
                                        if line.result_package_id: 
                                            if line.result_package_id.packaging_id.support_expedition:
                                                exist = False
                                                pal = line.result_package_id.id 
                                                for dico in listepal:
                                                    if pal == dico['pal']:
                                                        exist = True                            
                                                if not exist:
                                                    data = {
                                                            'pal': line.result_package_id.id,
                                                            'name': line.result_package_id.name,
                                                            }
                                                    listepal.append(data) 

                                    if len(listepal)>=1:  
                                        for palette in listepal:
                                            enreg_pal = self.export_desadv_palette(picking, sale, palette) 
                                            if enreg_pal:
                                                rows_to_write.append(enreg_pal)
                                                nb_enreg = nb_enreg + 1 
                                                no_palette = palette.get('pal')
                                                #
                                                # On génère les enregistrements packets (colis) liés à la palette
                                                # 
                                                if picking.nb_packet_edi >= 1:  
                                                    listecolis = []   
                                                    #for line in picking.move_line_ids_without_package: 
                                                    for line in picking.move_line_ids: 
                                                        if line.result_package_id.id == no_palette: 
                                                            if not line.package_id.packaging_id.support_expedition:
                                                                exist = False
                                                                colis = line.package_id.id 
                                                                for dico in listecolis:
                                                                    if colis == dico['colis']:
                                                                        exist = True                            
                                                                if not exist:
                                                                    data = {
                                                                            'colis': line.package_id.id,
                                                                            'name': line.package_id.name,
                                                                            }
                                                                    listecolis.append(data) 
                                                    if len(listecolis)>=1:
                                                        for colis in listecolis: 
                                                            no_colis = colis.get('colis')
                                                            enreg_col = self.export_desadv_colis(picking,sale,colis) 
                                                            if enreg_col:
                                                                rows_to_write.append(enreg_col)
                                                                nb_enreg = nb_enreg + 1 
                                                                #
                                                                # On génère les enregistrements lignes liés au colis
                                                                # 
                                                                #for line in picking.move_line_ids_without_package:
                                                                for line in picking.move_line_ids:
                                                                    if line.package_id.id == no_colis and line.result_package_id.id == no_palette:       
                                                                        nb_lig_desadv += 1
                                                                        enreg_lig = self.export_desadv_ligne(picking,sale,line,nb_lig_desadv) 
                                                                        if enreg_lig:
                                                                            rows_to_write.append(enreg_lig)
                                                                            nb_enreg = nb_enreg + 1 
                                    else:
                                        #
                                        # On génère les enregistrements packets (colis)
                                        # 
                                        if picking.nb_packet_edi >= 1:   
                                            listecolis = []  
                                            #for line in picking.move_line_ids_without_package: 
                                            for line in picking.move_line_ids: 
                                                if line.result_package_id == no_palette: 
                                                    if not line.result_package_id.packaging_id.support_expedition:
                                                        exist = False
                                                        colis = line.package_id.id 
                                                        for dico in listecolis:
                                                            if colis == dico['colis']:
                                                                exist = True                            
                                                        if not exist:
                                                            data = {
                                                                    'colis': line.package_id.id,
                                                                    'name': line.package_id.name,
                                                                    }
                                                            listecolis.append(data)      

                                            if len(listecolis)>=1:
                                                for colis in listecolis: 
                                                    no_colis = colis.get('colis')
                                                    enreg_col = self.export_desadv_colis(picking,sale,colis) 
                                                    if enreg_col:
                                                        rows_to_write.append(enreg_col)
                                                        nb_enreg = nb_enreg + 1 
                                                    #
                                                    # On génère les enregistrements lignes liés au colis
                                                    # 
                                                    #for line in picking.move_line_ids_without_package:
                                                    for line in picking.move_line_ids:
                                                        if line.package_id.id == no_colis:                                                            
                                                            nb_lig_desadv += 1
                                                            enreg_lig = self.export_desadv_ligne(picking,sale,line,nb_lig_desadv) 
                                                            if enreg_lig:
                                                                rows_to_write.append(enreg_lig)
                                                                nb_enreg = nb_enreg + 1 
                                        else:
                                            #
                                            # On génère les enregistrements ligne sans colisage
                                            # 
                                            #for line in picking.move_line_ids_without_package:
                                            for line in picking.move_line_ids:      
                                                nb_lig_desadv += 1
                                                enreg_lig = self.export_desadv_ligne(picking,sale,line,nb_lig_desadv)     
                                                if enreg_lig:
                                                    rows_to_write.append(enreg_lig)
                                                    nb_enreg = nb_enreg + 1 
                                else:
                                    #
                                    # On génère les enregistrements packets (colis) sans palette
                                    # 
                                    if picking.nb_packet_edi >= 1:   
                                        listecolis = []  
                                        #for line in picking.move_line_ids_without_package: 
                                        for line in picking.move_line_ids: 
                                            if not line.result_package_id.packaging_id.support_expedition:
                                                exist = False
                                                colis = line.package_id.id 
                                                for dico in listecolis:
                                                    if colis == dico['colis']:
                                                        exist = True                            
                                                if not exist:
                                                    data = {
                                                            'colis': line.package_id.id,
                                                            'name': line.package_id.name,
                                                            }
                                                    listecolis.append(data)      

                                        if len(listecolis)>=1:
                                            for colis in listecolis: 
                                                no_colis = colis.get('colis')
                                                enreg_col = self.export_desadv_colis(picking,sale,colis) 
                                                if enreg_col:
                                                    rows_to_write.append(enreg_col)
                                                    nb_enreg = nb_enreg + 1 
                                                #
                                                # On génère les enregistrements lignes liés au colis
                                                # 
                                                #for line in picking.move_line_ids_without_package:
                                                for line in picking.move_line_ids:
                                                    if line.package_id.id == no_colis:
                                                        nb_lig_desadv += 1
                                                        enreg_lig = self.export_desadv_ligne(picking,sale,line,nb_lig_desadv)       
                                                        if enreg_lig:
                                                            rows_to_write.append(enreg_lig)
                                                            nb_enreg = nb_enreg + 1 
                                    else:
                                        #
                                        # On génère les enregistrements ligne sans colisage
                                        # 
                                        #for line in picking.move_line_ids_without_package:
                                        for line in picking.move_line_ids:  
                                            nb_lig_desadv += 1
                                            enreg_lig = self.export_desadv_ligne(picking,sale,line,nb_lig_desadv)        
                                            if enreg_lig:
                                                rows_to_write.append(enreg_lig)
                                                nb_enreg = nb_enreg + 1                  
    
                                client = partner_obj.search([('id','=', sale.partner_acheteur_id.id)],limit=1)
                                #
                                # Envoi DESADV : Envoi généré
                                #
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Bons de livraison du ' + str(today) 
                                corps = "Le bon de livraison {} pour le client {} a été envoyé. <br/><br>".format(picking.name, client.name) 
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)
                                code_erreur = self.env['erreur.edi'].search([('name','=', '0700')], limit=1) 
                                flux = self.env['flux.edi'].search([('name','=', 'DESADV')], limit=1)
                                message = "Le bon de livraison {} pour le client {} a été envoyé. ".format(picking.name, client.name) 
                                self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            else:  
                                client = partner_obj.search([('id','=', sale.partner_acheteur_id.id)],limit=1)
                                #
                                # Erreur sur envoi DESADV : Client ne recoit pas les BLs en EDI
                                #
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Bons de livraison du ' + str(today) 
                                corps = "Le client {} ne reçoit pas les bons de livraison en EDI. <br/><br>".format(client.name) 
                                corps+= "Le DESADV n'est pas envoyé. <br/><br>"                         
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)
                                code_erreur = self.env['erreur.edi'].search([('name','=', '0404')], limit=1) 
                                flux = self.env['flux.edi'].search([('name','=', 'DESADV')], limit=1)
                                message = "Le client {} ne reçoit pas les bons de livraison en EDI. Le DESADV n'est pas envoyé. ".format(client.name) 
                                self.edi_generation_erreur(code_erreur, flux, sujet, message)    

                        else:
                            client = partner_obj.search([('id','=', sale.partner_acheteur_id.id)],limit=1)
                            #
                            # Erreur sur envoi DESADV : Client pas en gestion EDI
                            #
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Bons de livraison du  ' + str(today) 
                            corps = "Le client {} n'est pas en gestion EDI. <br/><br>".format(client.name) 
                            corps+= "Le DESADV n'est pas envoyé. <br/><br>"                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.edi_generation_mail(destinataire, sujet, corps)
                            code_erreur = self.env['erreur.edi'].search([('name','=', '0400')], limit=1) 
                            flux = self.env['flux.edi'].search([('name','=', 'DESADV')], limit=1)
                            message = "Le client {} n'est pas en gestion EDI. Le DESADV n'est pas envoyé. ".format(client.name) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                    else:
                        #
                        # Erreur sur envoi DESADV : La commande associée n'est pas une commande EDI
                        #
                        sujet = str(self.env.company.name) + ' - Gestion EDI - Bons de livraison du ' + str(today) 
                        corps = "La commande {} associé à la livraison {} n'est pas une commande EDI. <br/><br>".format(sale.name, picking.name) 
                        corps+= "Le DESADV n'est pas envoyé. <br/><br>"                         
                        corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                        destinataire = company_id.gestion_user_id.email
                        if destinataire:
                            self.edi_generation_mail(destinataire, sujet, corps)
                        code_erreur = self.env['erreur.edi'].search([('name','=', '0702')], limit=1) 
                        flux = self.env['flux.edi'].search([('name','=', 'DESADV')], limit=1)
                        message = "La commande {} associé à la livraison {} n'est pas une commande EDI. Le DESADV n'est pas envoyé.".format(sale.name, picking.name) 
                        self.edi_generation_erreur(code_erreur, flux, sujet, message)                         
                else:
                    #
                    # Erreur sur envoi DESADV : La commande associée n'existe plus
                    #
                    sujet = str(self.env.company.name) + ' - Gestion EDI - Bons de livraison du ' + str(today) 
                    corps = "La commande {} associé à la livraison {} n'existe plus dans la base Odoo. <br/><br>".format(picking.origin,picking.name) 
                    corps+= "Le DESADV n'est pas envoyé. <br/><br>"                         
                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                    destinataire = company_id.gestion_user_id.email
                    if destinataire:
                        self.edi_generation_mail(destinataire, sujet, corps)
                    code_erreur = self.env['erreur.edi'].search([('name','=', '0702')], limit=1) 
                    flux = self.env['flux.edi'].search([('name','=', 'DESADV')], limit=1)
                    message = "La commande {} associé à la livraison {} n'existe plus dans la base Odoo. Le DESADV n'est pas envoyé.".format(picking.origin, picking.name) 
                    self.edi_generation_erreur(code_erreur, flux, sujet, message)                        
            else:
                #
                # Livraison sans document d'origine
                # 
                #
                # Erreur sur envoi DESADV : Livraison sans document d'origine
                #
                sujet = str(self.env.company.name) + ' - Gestion EDI - Bons de livraison du ' + str(today) 
                corps = "La livraison {} n'est pas rattachée à une commande dans la base Odoo. <br/><br>".format(picking.name) 
                corps+= "Le DESADV n'est pas envoyé. <br/><br>"                         
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.edi_generation_mail(destinataire, sujet, corps)
                code_erreur = self.env['erreur.edi'].search([('name','=', '0703')], limit=1) 
                flux = self.env['flux.edi'].search([('name','=', 'DESADV')], limit=1)
                message = "La livraison {} n'est pas rattachée à une commande dans la base Odoo. Le DESADV n'est pas envoyé.".format(picking.name) 
                self.edi_generation_erreur(code_erreur, flux, sujet, message)   

            #
            # On met à jour le picking
            #
            picking.write({'desadv_edi_genere':True,
                            'desadv_edi_envoye':True,}) 
        #
        # on écrit le fichier d'export
        #
        if nb_enreg >= 1:
            date_generation = fields.Datetime.now()
            date_fic = fields.Datetime.from_string(date_generation)
            datefic = date_fic.strftime("%d%m%Y%H%M%S")

            edi_obj = self.env['parametre.edi']
            company_id =  self.env.company 
            gln_societe = company_id.partner_id.code_gln
            if company_id.param_edi_id:
                param = edi_obj.search([('id', '=', company_id.param_edi_id.id)])
                if len(param)>0:        
                    adresse_ftp = param.adresse_ftp
                    rep_export = param.rep_export_interne_edi 
                    if param.nom_fichier_desadv_edi_export:
                        fichier_desadv = param.nom_fichier_desadv_edi_export.strip()+'_%s_%s_%s' %(gln_societe,datefic,name_picking)  
                        fichier_desadv_txt = fichier_desadv+'.txt' 
                    else:
                        rep_export = 'data/export_ftp'
                        fichier_desadv = 'DESADV_%s_%s_%s' %(gln_societe,datefic,name_picking)  
                        fichier_desadv_txt = fichier_desadv +'.txt'  
                else:
                    rep_export = 'data/export_ftp' 
                    fichier_desadv = 'DESADV_%s_%s_%s' %(gln_societe,datefic,name_picking)  
                    fichier_desadv_txt = fichier_desadv +'.txt'  
            else:
                rep_export = 'data/export_ftp' 
                fichier_desadv = 'DESADV_%s_%s_%s' %(gln_societe,datefic,name_picking)   
                fichier_desadv_txt = fichier_desadv +'.txt'  
             
            fich_path = rep_export
            fichier_genere = fich_path + '/%s' % fichier_desadv_txt

            #logger.info("===========================================================================")
            #logger.info(fichier_desadv)
            #logger.info("===========================================================================")
            #logger.info(rows_to_write)
            #logger.info("===========================================================================")

            fichier_desadv_genere = open(fichier_genere, "w", encoding='iso_8859_1')
            for rows in rows_to_write:
                retour_chariot = '\n'    #'\r\n'
                #retour_chariot = retour_chariot.encode('ascii')
                rows += retour_chariot
                fichier_desadv_genere.write(str(rows))
            fichier_desadv_genere.close()        
        
            fichier_genere_dest = fich_path + '/%s.txt' % fichier_desadv   
            fichier_desadv_txt = '%s.txt' % fichier_desadv  
            #
            # On envoie le fichier généré par FTP ou SFTP
            #
            company_id =  self.env.company 
            param = edi_obj.search([('id', '=', company_id.param_edi_id.id)])
            if len(param)>0: 
                if param.type_connexion == 'ftp': 
                    #
                    # Envoi FTP
                    #  
                    ftp_user = param.compte_ftp_edi
                    ftp_password = param.mdp_edi
                    adresse_ftp = param.adresse_ftp
                    ftp_port = param.port_ftp
                    rep_envoi_ftp = param.repertoire_envoi_edi

                    ftp = ftplib.FTP() 
                    ftp.connect(adresse_ftp, ftp_port, 30*5) 
                    ftp.login(ftp_user, ftp_password)             
                    passif=True
                    ftp.set_pasv(passif)
                    ftp.cwd(rep_envoi_ftp)
                    with open(fichier_genere_dest,'rb') as fp:
                        ftp.storbinary('STOR '+ fichier_desadv_txt, fp)
                    ftp.quit()
                else: 
                    #
                    # Envoi SFTP
                    #                      
                    sftp_url = param.adresse_ftp
                    sftp_user = param.compte_ftp_edi
                    sftp_password = param.mdp_edi
                    sftp_port = param.port_ftp
                    rep_envoi_sftp = param.repertoire_envoi_edi
                    cnopts = pysftp.CnOpts()
                    cnopts.hostkeys = None

                    with pysftp.Connection(host=sftp_url,username=sftp_user,password=sftp_password,port=int(sftp_port),cnopts=cnopts) as sftp:
                        # on ouvre le dossier envoi
                        sftp.chdir(rep_envoi_sftp)
                        # export des fichiers
                        sftp.put(fichier_genere_dest,fichier_desadv_txt)

            #
            # On déplace le fichier généré dans le répertoire de sauvegarde 
            #
            if company_id.gestion_archivage:
                self.copie_fichier_traite(True, fichier_desadv_txt)

            #
            # Envoi DESADV : Fichier généré
            #
            sujet = str(self.env.company.name) + ' - Gestion EDI - Bons de livraison du ' + str(today) 
            corps = "Le fichier {} des bons de livraison client a été envoyé. <br/><br>".format(fichier_desadv) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.edi_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.edi'].search([('name','=', '0701')], limit=1) 
            flux = self.env['flux.edi'].search([('name','=', 'DESADV')], limit=1)
            message = "Le fichier {} des bons de livraison client a été envoyé.".format(fichier_desadv)
            self.edi_generation_erreur(code_erreur, flux, sujet, message)    

    #########################################################################################
    #                                                                                       #
    #                                 Export Enregistrement Entete                          #
    #                                                                                       #
    #########################################################################################   
    def export_desadv_entete(self,picking,sale): 

        espace = ' '    
        enreg_entete  = 'ENT' 
        enreg_entete += maxi(sale.edi_destinataire,35)
        enreg_entete += maxi(sale.edi_emetteur,35)
        if picking.no_bl_edi_desadv:
            enreg_entete += maxi(picking.no_bl_edi_desadv,17)                   #   M   74	90	an	17	n° du DESADV
        else:    
            enreg_entete += maxi(picking.name,17)                               #   M   74	90	an	17	n° du DESADV
        if picking.batch_id:
            enreg_entete += 'YA6'                                               #   M   91	93	an	3	Type de DESADV (220, 50E, 230, etc… (Desadv Alloti)
        else:
            enreg_entete += '351'                                               #   M   91	93	an	3	Type de DESADV (220, 50E, 230, etc… (Desadv non Alloti)
        enreg_entete += maxi(espace,3)                                          #   C   94	96	an	3	Code fonction
        date_desadv = datetime.now()  
        date_desadv_calc = self.transforme_date_heure(date_desadv,'date')
        heure_desadv_calc = self.transforme_date_heure(date_desadv,'heure')

        #
        # On ajoute un jour ouvré dans la date de livraison sur demande client dans le ticket #6907
        #
        date_livraison_plus_un = apik_calendar.calcul_date_ouvree(picking.date_done, 2, picking.company_id.nb_weekend_days, picking.company_id.zone_geo) 
        date_liv_calc = self.transforme_date_heure(date_livraison_plus_un,'date')
        heure_liv_calc = self.transforme_date_heure(date_livraison_plus_un,'heure')

        #date_liv_calc = self.transforme_date_heure(picking.date_done,'date')
        #heure_liv_calc = self.transforme_date_heure(picking.date_done,'heure')
        date_cde_calc = self.transforme_date_heure(sale.date_order,'date')
        heure_cde_calc = self.transforme_date_heure(sale.date_order,'heure')
        enreg_entete += maxi(date_desadv_calc,8)                                #   M    97	104	n	8	Date du DESADV
        enreg_entete += maxi(heure_desadv_calc,4)                               #   M   105	108	n	4	heure du DESADV
        enreg_entete += maxi(date_liv_calc,8)                                   #   M   109	116	n	8	Date de livraison
        enreg_entete += maxi(heure_liv_calc,4)                                  #   M   117	120	n	4	heure de livraison
        enreg_entete += maxi(espace,8)                                          #   C   121	128	n	8	Date de livraison estimée
        enreg_entete += maxi(espace,4)                                          #   C   129	132	n	4	heure de livraison estimée
        enreg_entete += maxi(espace,8)                                          #   C   133	140	n	8	Date d'expédition
        enreg_entete += maxi(espace,4)                                          #   C   141	144	n	4	heure d'expédition
        enreg_entete += maxi(espace,8)                                          #   C   145	152	n	8	Date d'enlèvement
        enreg_entete += maxi(espace,4)                                          #   C   153	156	n	4	heure d'enlèvement
        w_ref_cde_client_edi = sale.ref_cde_client_edi.strip()
        if sale.ref_cde_client_edi:
            w_ref_cde_client_edi = sale.ref_cde_client_edi.strip()
            if w_ref_cde_client_edi:
                enreg_entete += maxi(sale.ref_cde_client_edi,35)                #   M   157	191	an	35	n° de la commande RFF+ON
            else:
                enreg_entete += maxi(sale.no_cde_client,35)                     #   M   157	191	an	35	n° de la commande BGM   
        else:
            enreg_entete += maxi(sale.no_cde_client,35)                         #   M   157	191	an	35	n° de la commande BGM
        #if sale.ref_cde_client_edi:
        #    enreg_entete += maxi(sale.ref_cde_client_edi,35)                    #   M   157	191	an	35	n° de la commande RFF+ON
        #else:
        #    enreg_entete += maxi(sale.no_cde_client,35)                         #   M   157	191	an	35	n° de la commande BGM
        enreg_entete += maxi(date_cde_calc,8)                                   #   M   192	199	n	8	Date de la commande
        enreg_entete += maxi(heure_cde_calc,4)                                  #   M   200	203	n	4	heure de la commande
        if picking.batch_id:
            enreg_entete += maxi(picking.batch_id.name,35)                      #   M   204	238	an	35	n° du BL
        else:    
            enreg_entete += maxi(picking.name,35)                               #   M   204	238	an	35	n° du BL
        enreg_entete += maxi(date_liv_calc,8)                                   #   M   239	246	n	8	Date du BL
        enreg_entete += maxi(heure_liv_calc,4)                                  #   M   247	250	n	4	heure du BL
        enreg_entete += maxi(sale.no_ope_promo,35)                              #   C   251	285	an	35	Numéro d'opération promotionnelle
        poids_brut = self.calcul_poids_brut(picking)
        poids_brut_edi = str(poids_brut)
        enreg_entete += maxi(poids_brut_edi,8)                                  #   C   286	293	n	8	Poids brut total
        enreg_entete += maxi(poids_brut_edi,8)                                  #   C   294	301	n	8	Poids net total 
        nb_palette_edi  = str(picking.nb_palette_edi)    
        enreg_entete += maxi(nb_palette_edi,6)                                  #   C   302	307	n	6	Nombre total de palettes (UL)
        nb_roll_edi  = str(picking.nb_roll_edi)    
        enreg_entete += maxi(nb_roll_edi,6)                                     #   C   308	313	n	6	Nombre total de Rolls (UL)       
        nb_packet_edi  = str(picking.nb_packet_edi)    
        enreg_entete += maxi(nb_packet_edi,6)                                   #   C   314	319	n	6	Nombre total de colis (UC)
        enreg_entete += maxi(sale.madeco_transport_id.mode_transport_edi,3)     #   C   320	322	an	3	Mode de transpor
        enreg_entete += maxi(sale.madeco_transport_id.type_transport_edi,8)     #   C   323	330	an	8	Identification du type de moyen de transport
        #enreg_entete += maxi(sale.intrastat_transport_id.mode_transport_edi,3) #   C   320	322	an	3	Mode de transpor
        #enreg_entete += maxi(sale.intrastat_transport_id.type_transport_edi,8) #   C   323	330	an	8	Identification du type de moyen de transport
        enreg_entete += maxi(sale.cond_liv,3)                                   #   C   331	333	an	3	Conditions de livraison 
        enreg_entete += maxi(sale.incoterm.code ,3)                             #   C   334	336	an	3	Conditions Incoterms
        enreg_entete += maxi(espace,3)                                          #   C   337	339	an	3	Fractionnement de livraison
        enreg_entete += maxi(espace,3)                                          #   C   340	342	an	3	Total Fractionnement de livraison
        enreg_entete += maxi(sale.comment_edi,350)                              #   C   343	692	an	350	Commentaires
        enreg_entete += maxi(sale.ref_cde_client_final_edi,35)                  #   C   693	727	an	35	Reference Commande Client Final (RFF+UC)

        return enreg_entete

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement Paramétre                         #
    #                                                                                       #
    #########################################################################################   
    def export_desadv_param(self,typ_interv,picking,sale): 

        espace       = ' '
        enreg_param  = 'PAR' 
        '''
        BY ==> Acheteur
        SU ==> Vendeur
        DP ==> Livré à
        UC ==> Client final
        IV ==> Facturé à
        OB ==> Commandé par
        PR ==> Payé par
        UD ==> Client final
        '''
        if typ_interv == 'BY':
            enreg_param += 'BY '                                                        # Type d'intervenant (qualifiant)
            enreg_param += maxi(sale.partner_acheteur_id.code_gln,20)                   # Code identifiant de l'intervenant
            enreg_param += maxi(espace,3)                                               # Type d'identifiant
            enreg_param += maxi(sale.partner_acheteur_id.name,70)                       # Nom de l'intervenant
        else:
            if typ_interv == 'SU':
                enreg_param += 'SU '                                                    # Type d'intervenant (qualifiant)
                enreg_param += maxi(sale.partner_vendeur_id.code_gln,20)                # Code identifiant de l'intervenant
                enreg_param += maxi(espace,3)                                           # Type d'identifiant
                enreg_param += maxi(sale.partner_vendeur_id.name,70)                    # Nom de l'intervenant
            else:
                if typ_interv == 'DP':
                    enreg_param += 'DP '                                                # Type d'intervenant (qualifiant)
                    enreg_param += maxi(sale.partner_livre_a_id.code_gln,20)            # Code identifiant de l'intervenant
                    enreg_param += maxi(espace,3)                                       # Type d'identifiant
                    enreg_param += maxi(sale.partner_livre_a_id.name,70)                # Nom de l'intervenant
                else:
                    if typ_interv == 'UC':
                        enreg_param += 'UC '                                            # Type d'intervenant (qualifiant)
                        enreg_param += maxi(sale.partner_final_id.code_gln,20)          # Code identifiant de l'intervenant
                        enreg_param += maxi(espace,3)                                   # Type d'identifiant
                        enreg_param += maxi(sale.partner_final_id.name,70)              # Nom de l'intervenant
                    else:
                        if typ_interv == 'IV':
                            enreg_param += 'IV '                                        # Type d'intervenant (qualifiant)
                            enreg_param += maxi(sale.partner_facture_a_id.code_gln,20)  # Code identifiant de l'intervenant
                            enreg_param += maxi(espace,3)                               # Type d'identifiant
                            enreg_param += maxi(sale.partner_facture_a_id.name,70)      # Nom de l'intervenant
                        else:
                            if typ_interv == 'OB':
                                enreg_param += 'OB '                                            # Type d'intervenant (qualifiant)
                                enreg_param += maxi(sale.partner_commande_par_id.code_gln,20)   # Code identifiant de l'intervenant
                                enreg_param += maxi(espace,3)                                   # Type d'identifiant
                                enreg_param += maxi(sale.partner_commande_par_id.name,70)       # Nom de l'intervenant
                            else:
                                if typ_interv == 'PR':
                                    enreg_param += 'PR '                                        # Type d'intervenant (qualifiant)
                                    enreg_param += maxi(sale.partner_paye_par_id.code_gln,20)   # Code identifiant de l'intervenant
                                    enreg_param += maxi(espace,3)                               # Type d'identifiant
                                    enreg_param += maxi(sale.partner_paye_par_id.name,70)       # Nom de l'intervenant
                                else:
                                    if typ_interv == 'UD':
                                        enreg_param += 'UD '                                        # Type d'intervenant (qualifiant)
                                        enreg_param += maxi(sale.partner_final_ud_id.code_gln,20)   # Code identifiant de l'intervenant
                                        enreg_param += maxi(espace,3)                               # Type d'identifiant
                                        enreg_param += maxi(sale.partner_final_ud_id.name,70)       # Nom de l'intervenant
                                    else:
                                        enreg_param += 'SU '                                        # Type d'intervenant (qualifiant)
                                        enreg_param += maxi(sale.partner_vendeur_id.code_gln,20)    # Code identifiant de l'intervenant
                                        enreg_param += maxi(espace,3)                               # Type d'identifiant
                                        enreg_param += maxi(sale.partner_vendeur_id.name,70)        # Nom de l'intervenant
        enreg_param += maxi(espace,35)          # Ligne adresse 1 intervenant    
        enreg_param += maxi(espace,35)          # Ligne adresse 2 intervenant
        enreg_param += maxi(espace,35)          # Ligne adresse 3 intervenant
        enreg_param += maxi(espace,9)           # Code postal intervenant
        enreg_param += maxi(espace,35)          # Ville intervenant
        enreg_param += maxi(espace,2)           # Code pays intervenant
        enreg_param += maxi(espace,35)          # Identification Complémentaire 1
        enreg_param += maxi(espace,3)           # Type identification 1
        enreg_param += maxi(espace,35)          # Identification Complémentaire 2
        enreg_param += maxi(espace,3)           # Type identification 2
        enreg_param += maxi(espace,35)          # Identification Complémentaire 3
        enreg_param += maxi(espace,3)           # Type identification 3
        enreg_param += maxi(espace,35)          # Identification Complémentaire 4
        enreg_param += maxi(espace,3)           # Type identification 4
        enreg_param += maxi(espace,35)          # Nom contact
        enreg_param += maxi(espace,35)          # Telephone contact
        enreg_param += maxi(espace,35)          # Mail contact      

        return enreg_param

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement Palette                           #
    #                                                                                       #
    #########################################################################################   
    def export_desadv_palette(self,picking,sale,palette): 
        enreg_palette = False
        palette_obj = self.env['stock.quant.package']
        no_palette = palette.get('pal')
        palette = palette_obj.search([('id', '=', no_palette)],limit=1)
        if len(palette)>0: 
            espace       = ' '
            enreg_palette  = 'PAL' 
            poids_pal = self.calcul_poids_palette_desadv(palette)
            #poids  = str(palette.palletizing_weight)  
            poids = str(poids_pal)
            enreg_palette += maxi(poids,6)                      #	C   6	Poids brut palette      MEA w/ AAD
            enreg_palette += maxi(espace,8)                     #	C   8	DLC palette	YYYYMMDD    DTM+36
            enreg_palette += maxi(espace,8)                     #	C   8	DLUO palette YYYYMMDD   DTM+361
            enreg_palette += maxi(palette.name,18)              #	C   8	SSCC palette            GIN+BJ
            enreg_palette += maxi(espace,18)                    #	C   8	EAN palette (UL)        GIN+EU

        return enreg_palette

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement Roll                              #
    #                                                                                       #
    #########################################################################################   
    def export_desadv_roll(self,picking,sale,colis): 
        enreg_roll = False    
        if colis.package_id:
            espace       = ' '
            enreg_roll  = 'ROL'             
            poids  = str(colis.package_id.palletizing_weight)
            enreg_roll += maxi(poids,6)                             #	C   6	Poids brut rolls        MEA avec AAD
            enreg_roll += maxi(espace,8)                            #	C   8	DLC rolls	YYYYMMDD    DTM+36
            enreg_roll += maxi(espace,8)                            #	C   8	DLUO rolls YYYYMMDD     DTM+361
            enreg_roll += maxi(colis.package_id.name,18)            #	C   8	SSCC rolls              GIN+BJ
            enreg_roll += maxi(espace,18)                           #	C   8	EAN rolls (UL)          GIN+EU

        return enreg_roll

    #########################################################################################
    #                                                                                       #
    #                               Calcul poids de la palette                              #
    #                                                                                       #
    ######################################################################################### 
    def calcul_poids_palette_desadv(self,package):
        poids_pal = 0
        if package:            
            if package.quant_ids:
                for quant in package.quant_ids:                    
                    poids_pal += (quant.quantity * quant.product_id.weight)
        return poids_pal

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement Colis                             #
    #                                                                                       #
    #########################################################################################   
    def export_desadv_colis(self,picking,sale,colis): 
        enreg_colis = False  
        colis_obj = self.env['stock.quant.package']
        no_colis = colis.get('colis')
        colis = colis_obj.search([('id', '=', no_colis)],limit=1)
        if len(colis)>0: 
            espace       = ' '
            enreg_colis  = 'COL'
            qte = 1 
            nb_cartons  = str(qte) 
            enreg_colis += maxi(nb_cartons,6)              #	M   6	Nombre de cartons       PAC
            enreg_colis += maxi(espace,18)                 #	C   18	DUN 14 colis            GIN+EU
            enreg_colis += maxi(espace,15)                 #	M   15	PCB                     QTY+52
            enreg_colis += maxi(espace,3)                  #	C   3	Unité de mesure         QTY+52
            enreg_colis += maxi(espace,8)                  #	C   8	DLC colis YYYYMMDD      DTM+36
            enreg_colis += maxi(espace,8)                  #	C   8	DLUO colis YYYYMMDD     DTM+361
            enreg_colis += maxi(espace,18)                 #	C   18	N° de lot               GIN+BX
            enreg_colis += maxi(colis.name,18)             #	C   8	SSCC rolls              GIN+BJ
            pds_colis = self.calcul_poids_colis_desadv(colis)
            #poids  = str(colis.weight)  
            poids  = str(pds_colis)  
            enreg_colis += maxi(poids,6)                   #	C   6	Poids brut rolls        MEA avec AAD

        return enreg_colis 

    #########################################################################################
    #                                                                                       #
    #                               Calcul poids du colis                                   #
    #                                                                                       #
    ######################################################################################### 
    def calcul_poids_colis_desadv(self,colis):
        poids_colis = 0
        stock_move_lines = self.env['stock.move.line'].search([('package_id', '=', colis.id)])
        if stock_move_lines:                       
            for sml in stock_move_lines:                    
                poids_colis += (sml.qty_done * sml.product_id.weight)
        return poids_colis          

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement Ligne                             #
    #                                                                                       #
    #########################################################################################   
    def export_desadv_ligne(self,picking,sale,line,nb_ligne_desadv): 
        
        espace       = ' '
        enreg_ligne  = 'LIG'                                                    #   M   3	LIG    
        enreg_ligne += '0'                                                      #   M   1	Drapeau ligne manquante   
        nb_ligne_desadv_str = str(nb_ligne_desadv)
        enreg_ligne	+= maxi(nb_ligne_desadv_str,6)                              #	M   6	n° de ligne article
        #enreg_ligne	+= maxi(line.move_id.sale_line_id.no_ligne_edi,6)           #	M   6	n° de ligne article
        enreg_ligne	+= maxi(line.product_id.barcode,35)                         #   C   35	Code EAN article
        enreg_ligne += maxi(line.move_id.sale_line_id.code_art_vendeur,35)      #	C   35	Code article vendeur
        enreg_ligne += maxi(line.move_id.sale_line_id.code_art_acheteur,35)     #	C   35	Code article acheteur
        qty_done = str(line.qty_done)   
        enreg_ligne += maxi(qty_done,15)                                        #	M   15	Quantité expediée
        enreg_ligne += maxi(line.move_id.sale_line_id.product_uom.unite_edi,3)  #	C   3	Unité de mesure
        qte_pcb = str(line.move_id.sale_line_id.qte_pcb)
        enreg_ligne += maxi(qte_pcb,15)                                         #	C   15	Quantité par colis (PCB)
        enreg_ligne += maxi(line.move_id.sale_line_id.unite_pcb.unite_edi,3)    #	C   3	Unité de mesure
        qte_manquante = str(self.calcul_qte_manquante(picking,sale,line))
        enreg_ligne += maxi(qte_manquante,15)                                   #	M   15	Quantité manquante
        enreg_ligne += maxi(line.move_id.sale_line_id.product_uom.unite_edi,3)  #	C   3	Unité de mesure
        desc_ligne = self.suppression_retour_chariot_ligne(line.move_id.sale_line_id.name)
        enreg_ligne += maxi(desc_ligne,140)                                     #	C   140	Description article
        enreg_ligne += maxi(line.move_id.sale_line_id.pun_edi,9)                #	C   9	Prix unitaire net
        enreg_ligne += maxi(line.move_id.sale_line_id.mt_net_ligne_edi,18)      #	C   18	Montant net de ligne
        enreg_ligne += maxi(line.move_id.sale_line_id.nb_ul_edi,8)              #	C   8	Nombre d'unité de conditionnement
        #enreg_ligne += maxi(line.move_id.sale_line_id.product_uom.unite_edi,3)  #	C   3	Unité de mesure de la quantité
        enreg_ligne += maxi(espace,7)                                           #   C   7	Type d'emballage
        enreg_ligne += maxi(line.move_id.sale_line_id.ean_ul_edi,14)            #	C   14	Code EAN UL (DUN 14)

        #
        # On ajoute un jour ouvré dans la date de livraison sur demande client dans le ticket #6907
        #
        date_livraison_plus_un = apik_calendar.calcul_date_ouvree(picking.date_done, 2, picking.company_id.nb_weekend_days, picking.company_id.zone_geo) 
        date_liv_calc = self.transforme_date_heure(date_livraison_plus_un,'date')
        heure_liv_calc = self.transforme_date_heure(date_livraison_plus_un,'heure')

        #date_liv_calc = self.transforme_date_heure(picking.date_done,'date')
        #heure_liv_calc = self.transforme_date_heure(picking.date_done,'heure')
        enreg_ligne += maxi(date_liv_calc,8)                                    #	C   8	Date de livraison
        enreg_ligne += maxi(heure_liv_calc,4)                                   #	C   4	heure de livraison
        enreg_ligne += maxi(line.move_id.sale_line_id.no_cde_magasin,35)        #	C   35	n° de commande magasin
        enreg_ligne += maxi(line.move_id.sale_line_id.gln_magasin.code_gln,20)  #	C   20	Code (ou EAN) du magasin
        enreg_ligne += maxi(line.move_id.sale_line_id.no_lig_erp_cli,6)         #	C   6	Numéro de ligne de la commande d'origine
        enreg_ligne += maxi(line.move_id.sale_line_id.ref_cde_cli_final,35)     #	C   35	n° de la commande
        date_cde_calc = self.transforme_date_heure(sale.date_order,'date')
        heure_cde_calc = self.transforme_date_heure(sale.date_order,'heure')
        enreg_ligne += maxi(date_cde_calc,8)                                    #   M   8	Date de la commande
        enreg_ligne += maxi(heure_cde_calc,4)                                   #   M   4	heure de la commande
        enreg_ligne += maxi(line.move_id.sale_line_id.no_cde_remplace,35)       #	C   35	N° de commande remplacée
        enreg_ligne += maxi(line.move_id.sale_line_id.no_ope_promo,35)          #	C   35	Numéro d'opération promotionnelle
        enreg_ligne += maxi(line.move_id.sale_line_id.comment_edi,350)          #	C   350	Commentaires
        enreg_ligne += maxi(espace,15)                                          #	C   15	Différences de quantité
        enreg_ligne += maxi(espace,3)                                           #	C   3	Nature de l'écart (en code)
        return enreg_ligne

    #########################################################################################
    #                                                                                       #
    #                          suppression_retour_chariot_ligne                             #
    #                                                                                       #
    #########################################################################################
    def suppression_retour_chariot_ligne(self, libelle):
        desc = libelle.replace('\n',' ')
        return desc

    #########################################################################################
    #                                                                                       #
    #                                  transforme_date_heure                                #
    #                                                                                       #
    #########################################################################################
    def transforme_date_heure(self, date_origine, type):
        date_str = str(date_origine)
        if type=='heure':
            # 
            # On renvoie l'heure sur 4 positions au format HHMM
            #
            retour_date = date_str[11:13]+date_str[14:16]
        else:
            retour_date = date_str[0:4]+date_str[5:7]+date_str[8:10]
        return retour_date   

    #########################################################################################
    #                                                                                       #
    #                                    calcul_poids_brut                                  #
    #                                                                                       #
    #########################################################################################
    def calcul_poids_brut(self, picking):
        poids = 0
        for line in picking.move_line_ids:
            poids += (line.product_id.weight * line.qty_done)        

        return poids  

    #########################################################################################
    #                                                                                       #
    #                                  calcul_qte_manquante                                 #
    #                                                                                       #
    #########################################################################################
    def calcul_qte_manquante(self, picking,sale,line):
        stock_move_obj = self.env['stock.move']
        sale_line_obj = self.env['sale.order.line']
        qte_manq = 0
        stock_move = stock_move_obj.search([('id','=', line.move_id.id)],limit=1)
        if stock_move:
            sale_line = sale_line_obj.search([('id','=', stock_move.sale_line_id.id)],limit=1) 
            if sale_line:
                if line.qty_done != sale_line.product_uom_qty:
                    if sale_line.product_uom_qty > line.qty_done :
                        qte_manq = sale_line.product_uom_qty - line.qty_done 
                    else:
                        qte_manq = 0
                else:
                    qte_manq = 0
            else:
                qte_manq = 0
        else:
            qte_manq = 0                            

        return qte_manq           

    #########################################################################################
    #                                                                                       #
    #                                    Génération mail                                    #
    #                                                                                       #
    #########################################################################################
    def edi_generation_mail(self, destinataire, sujet, corps):
        #
        # On envoie un mail au destinataire reçu
        #
        mail_obj = self.env['mail.mail']
        today = fields.Date.from_string(fields.Date.context_today(self))
        if len(destinataire)>0:
            mail_data = {
                        'subject': sujet,
                        'body_html': corps,
                        'email_from': self.env.user.email,
                        'email_to': destinataire,                        
                        }
            mail_id = mail_obj.create(mail_data)
            mail_id.send()
        
    #########################################################################################
    #                                                                                       #
    #                                     Génération erreur EDI                             #
    #                                                                                       #
    #########################################################################################
    def edi_generation_erreur(self, erreur, flux, sujet, corps):
        #
        # On cree un enregistrement dans le suivi EDI
        #
        company_id =  self.env.user.company_id 
        suivi_edi = self.env['suivi.edi']
        today = fields.Date.from_string(fields.Date.context_today(self))
        if len(sujet)>0:
            suivi_data = {
                        'company_id': company_id.id,
                        'name': sujet,
                        'libelle_mvt_edi': corps,
                        'flux_id': flux.id,
                        'erreur_id': erreur.id,                        
                        }

            suivi = suivi_edi.create(suivi_data)

    #########################################################################################
    #                                                                                       #
    #                                     Création stock picking                            #
    #                                                                                       #
    #########################################################################################          
    @api.model
    def create(self, vals):
        res = super().create(vals)        
        if res:
            for pick in res:
                if pick.group_id:
                    cde_vte = self.env['sale.order'].search([('name','=', pick.group_id.name)],limit=1) 
                else:
                    if pick.origin:
                        cde_vte = self.env['sale.order'].search([('name','=', pick.origin.strip())],limit=1)            
                    else:
                        cde_vte = False
                if cde_vte:  
                    if cde_vte.picking_ids: 
                        for picking in cde_vte.picking_ids.sorted(key=lambda m: (m.id)):
                            if not pick.no_bl_edi_desadv:
                                name_picking = cde_vte.recherche_nom_picking_cmde(pick, cde_vte)
                                if name_picking:
                                    pick.no_bl_edi_desadv = name_picking 
        return res   
