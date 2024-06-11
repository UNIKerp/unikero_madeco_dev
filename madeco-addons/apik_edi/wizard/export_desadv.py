# -*- coding: utf-8 -*-

import base64
import io
import os
import ftplib

from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning
from odoo.tools import float_is_zero, pycompat
from datetime import datetime, timedelta
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules import get_module_resource
from odoo.modules import get_module_path

import logging
logger = logging.getLogger(__name__)

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


class DesadvEDIExport(models.TransientModel):
    _name = "apik_edi.wizard_desadv"
    _description = "Export des Bons de livraison EDI"
    
    export_date = fields.Date("Date de l'export",default=fields.Date.today())
    arcedi_data = fields.Binary('Fichier Export')
    filename = fields.Char(string='Filename', size=256)
    
    #########################################################################################
    #                                                                                       #
    #                          Bouton Export des ARC de commandes EDI                       #
    #                                                                                       #
    #########################################################################################        
    def export_desadv_edi(self):           
        self.ensure_one()
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company                 
        
        partner_obj = self.env['res.partner']
        picking_obj = self.env['stock.picking']
        picking_ids = picking_obj.search([('id', 'in', self._context.get('active_ids', True))])
        
        nb_enreg = 1
        rows_to_write = []

        for picking in picking_ids:           
            if picking.partner_id.client_edi:
                if picking.partner_id.edi_desadv:
                    #
                    # On recherche la commande de vente rattaché à la livraison
                    #
                    if picking.origin:
                        sale = sale_obj.search([('name', '=', pick.origin)],limit=1)
                        if len(sale)>0:
                            if sale.commande_edi:
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
                                enreg_par = self.export_desadv_param('BY',picking,sale) 
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1 
                                #
                                # On génère l'enregistrement NAD+SU
                                # 
                                enreg_par = self.export_desadv_param('SU',picking,sale)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1  
                                #
                                # On génère l'enregistrement NAD+DP
                                # 
                                enreg_par = self.export_desadv_param('DP',picking,sale)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1  
                                #
                                # On génère l'enregistrement NAD+UC
                                # 
                                enreg_par = self.export_desadv_param('UC',picking,sale)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1  
                                #
                                # On génère l'enregistrement NAD+IV
                                # 
                                enreg_par = self.export_desadv_param('IV',picking,sale)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1  
                                #
                                # On génère les enregistrements ligne
                                # 
                                for line in picking.move_line_ids:      
                                    enreg_lig = self.export_desadv_ligne(picking,sale,line) 
                                    if enreg_lig:
                                        rows_to_write.append(enreg_lig)
                                        nb_enreg = nb_enreg + 1  
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
                else:
                    client = partner_obj.search([('id','=', picking.partner_id.id)],limit=1)
                    #
                    # Erreur sur envoi ARC : Client ne recoit pas les BLs en EDI
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
                client = partner_obj.search([('id','=', picking.partner_id.id)],limit=1)
                #
                # Erreur sur envoi ARC : Client pas en gestion EDI
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

            #
            # On met à jour la commande
            #
            picking.write({'desadv_edi_envoye':True}) 

            client = partner_obj.search([('id','=', picking.partner_id.id)],limit=1)
            #
            # Envoi ARC : Envoi généré
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

        #
        # on écrit le fichier d'export
        #
        if nb_enreg >= 1:
            date_generation = fields.Datetime.now()
            date_fic = fields.Datetime.from_string(date_generation)
            datefic = date_fic.strftime("%d%m%Y%H%M%S")

            edi_obj = self.env['parametre.edi']
            company_id =  self.env.company 
            if company_id.param_edi_id:
                param = edi_obj.search([('id', '=', company_id.param_edi_id.id)])
                if len(param)>0:        
                    adresse_ftp = param.adresse_ftp
                    rep_export = param.rep_export_interne_edi 
                    if param.nom_fichier_arc_cde_edi_export:
                        fichier_desadv = param.nom_fichier_desadv_edi_export.strip()+'_%s.txt' %(datefic) 
                    else:
                        rep_export = 'data/export_ftp'
                        fichier_desadv = 'DESADV_%s.txt' %(datefic)  
                else:
                    rep_export = 'data/export_ftp' 
                    fichier_desadv = 'DESADV_%s.txt' %(datefic) 
            else:
                rep_export = 'data/export_ftp' 
                fichier_desadv = 'DESADV_%s.txt' %(datefic) 
             

            self.filename = fichier_desadv
            
            #fich_path = '%s/' % get_module_path('apik_edi') 
            fich_path = rep_export
            fichier_genere = fich_path + '/%s' % self.filename
            
            fichier_desadv_genere = open(fichier_genere, "w")
            for rows in rows_to_write:
                retour_chariot = '\n'    #'\r\n'
                #retour_chariot = retour_chariot.encode('ascii')
                rows += retour_chariot
                fichier_desadv_genere.write(str(rows))
                
            fichier_desadv_genere.close()        
        
            #
            # ICI
            # On envoie le fichier généré par FTP
            #

            #
            # ICI
            # On déplace le fichier généré dans le répertoire de sauvegarde 
            #

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
        else:
            raise UserError(_("Aucun bon de livraison EDI à envoyer."))    

    #########################################################################################
    #                                                                                       #
    #                                 Export Enregistrement Entete                          #
    #                                                                                       #
    #########################################################################################   
    def export_desadv_entete(self,picking,sale): 

        espace = ' '    
        enreg_entete  = 'ENT' 
        enreg_entete += maxi(sale.edi_emetteur,35)
        enreg_entete += maxi(sale.edi_destinataire,35)
        enreg_entete += maxi(picking.name,17)               #   M   74	90	an	17	N° du DESADV
        enreg_entete += '351'                               #   M   91	93	an	3	Type de DESADV (220, 50E, 230, etc…
        enreg_entete += maxi(espace,3)                      #   C   94	96	an	3	Code fonction


        date_desadv = datetime.now()  
        date_desadv_calc = self.transforme_date_heure(date_desadv,'date')
        heure_desadv_calc = self.transforme_date_heure(date_desadv,'heure')
        date_liv_calc = self.transforme_date_heure(picking.date_done,'date')
        heure_liv_calc = self.transforme_date_heure(picking.date_done,'heure')
        date_cde_calc = self.transforme_date_heure(sale.date_order,'date')
        heure_cde_calc = self.transforme_date_heure(sale.date_order,'heure')
        enreg_entete += maxi(date_desadv_calc,8)            #   M    97	104	n	8	Date du DESADV
        enreg_entete += maxi(heure_desadv_calc,4)           #   M   105	108	n	4	heure du DESADV
        enreg_entete += maxi(date_liv_calc,8)               #   M   109	116	n	8	Date de livraison
        enreg_entete += maxi(heure_liv_calc,4)              #   M   117	120	n	4	heure de livraison
        
        enreg_entete += maxi(espace,8)                      #   C   121	128	n	8	Date de livraison estimée
        enreg_entete += maxi(espace,4)                      #   C   129	132	n	4	heure de livraison estimée
        enreg_entete += maxi(espace,8)                      #   C   133	140	n	8	Date d'expédition
        enreg_entete += maxi(espace,4)                      #   C   141	144	n	4	heure d'expédition
        enreg_entete += maxi(espace,8)                      #   C   145	152	n	8	Date d'enlèvement
        enreg_entete += maxi(espace,4)                      #   C   153	156	n	4	heure d'enlèvement
        enreg_entete += maxi(sale.no_cde_client,35)         #   M   157	191	an	35	n° de la commande
        enreg_entete += maxi(date_cde_calc,8)               #   M   192	199	n	8	Date de la commande
        enreg_entete += maxi(heure_cde_calc,4)              #   M   200	203	n	4	heure de la commande
        enreg_entete += maxi(picking.name,35)               #   M   204	238	an	35	n° du BL
        enreg_entete += maxi(date_liv_calc,8)               #   M   239	246	n	8	Date du BL
        enreg_entete += maxi(heure_liv_calc,4)              #   M   247	250	n	4	heure du BL
        enreg_entete += maxi(espace,35)                     #   C   251	285	an	35	Numéro d'opération promotionnelle
        
        poids_brut = self.calcul_poids_brut(picking)
        enreg_entete += maxi(poids_brut,8)                  #   C   286	293	n	8	Poids brut total
        enreg_entete += maxi(espace,8)                      #   C   294	301	n	8	Poids net total 
        enreg_entete += maxi(espace,6)                      #   C   302	307	n	6	Nombre total de palettes (UL)
        enreg_entete += maxi(espace,6)                      #   C   308	313	n	6	Nombre total de Rolls (UL)       
        enreg_entete += maxi(espace,6)                      #   C   314	319	n	6	Nombre total de colis (UC)
        enreg_entete += maxi(espace,3)                      #   C   320	322	an	3	Mode de transpor
        enreg_entete += maxi(espace,8)                      #   C   323	330	an	8	Identification du type de moyen de transport
        enreg_entete += maxi(sale.cond_liv,3)               #   C   331	333	an	3	Conditions de livraison 
        enreg_entete += maxi(sale.incoterm.code ,3)         #   C   334	336	an	3	Conditions Incoterms
        enreg_entete += maxi(espace,3)                      #   C   337	339	an	3	Fractionnement de livraison
        enreg_entete += maxi(espace,3)                      #   C   340	342	an	3	Total Fractionnement de livraison
        enreg_entete += maxi(sale.comment_edi,350)          #   C   343	692	an	350	Commentaires

        return enreg_entete

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement Paramétre                         #
    #                                                                                       #
    #########################################################################################   
    def export_desadv_param(self,typ_interv,picking,sale): 

        espace       = ' '
        enreg_param  = 'PAR' 
        
        if typ_interv == 'BY':
            enreg_param += 'BY '                                                        # Type d'intervenant (qualifiant)
            enreg_param += maxi(sale.edi_emetteur,20)                                   # Code identifiant de l'intervenant
            enreg_param += maxi(espace,3)                                               # Type d'identifiant
            enreg_param += maxi(sale.partner_id.name,20)                                # Nom de l'intervenant
        else:
            if typ_interv == 'SU':
                enreg_param += 'SU '                                                    # Type d'intervenant (qualifiant)
                enreg_param += maxi(sale.edi_emetteur,20)                               # Code identifiant de l'intervenant
                enreg_param += maxi(espace,3)                                           # Type d'identifiant
                enreg_param += maxi(sale.partner_vendeur_id.name,70)                    # Nom de l'intervenant
            else:
                if typ_interv == 'DP':
                    enreg_param += 'DP '                                                # Type d'intervenant (qualifiant)
                    enreg_param += maxi(sale.edi_emetteur,20)                           # Code identifiant de l'intervenant
                    enreg_param += maxi(espace,3)                                       # Type d'identifiant
                    enreg_param += maxi(sale.partner_shipping_id.name,70)               # Nom de l'intervenant
                else:
                    if typ_interv == 'UC':
                        enreg_param += 'UC '                                            # Type d'intervenant (qualifiant)
                        enreg_param += maxi(sale.edi_emetteur,20)                       # Code identifiant de l'intervenant
                        enreg_param += maxi(espace,3)                                   # Type d'identifiant
                        enreg_param += maxi(sale.partner_final_id.name,70)              # Nom de l'intervenant
                    else:
                        if typ_interv == 'IV':
                            enreg_param += 'SU '                                        # Type d'intervenant (qualifiant)
                            enreg_param += maxi(sale.edi_emetteur,20)                   # Code identifiant de l'intervenant
                            enreg_param += maxi(espace,3)                               # Type d'identifiant
                            enreg_param += maxi(sale.partner_invoice_id.name,70)        # Nom de l'intervenant
                        else:
                            enreg_param += 'SU '                                        # Type d'intervenant (qualifiant)
                            enreg_param += maxi(sale.edi_emetteur,20)                   # Code identifiant de l'intervenant
                            enreg_param += maxi(espace,3)                               # Type d'identifiant
                            enreg_param += maxi(sale.partner_id.name,70)                # Nom de l'intervenant
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
    #                               Export Enregistrement Ligne                             #
    #                                                                                       #
    #########################################################################################   
    def export_desadv_ligne(self,picking,sale,line): 

        espace       = ' '
        enreg_ligne  = 'LIG'                                    #   M   3	LIG    
        enreg_ligne += '0'                                      #   M   1	Drapeau ligne manquante   
        enreg_ligne	+= maxi(line.no_ligne_edi,6)                #	M   6	n° de ligne article
        enreg_ligne	+= maxi(line.product_id.barcode,35)         #   C   35	Code EAN article
        enreg_ligne += maxi(espace,35)                          #	C   35	Code article vendeur
        enreg_ligne += maxi(espace,35)                          #	C   35	Code article acheteur
        enreg_ligne += maxi(line.qty_done,15)                   #	M   15	Quantité expediée
        enreg_ligne += maxi(espace,3)                           #	C   3	Unité de mesure
        enreg_ligne += maxi(espace,15)                          #	C   15	Quantité par colis (PCB)
        enreg_ligne += maxi(espace,3)                           #	C   3	Unité de mesure
     
        qte_manquante = self.calcul_qte_manquante(picking,sale,line)
        enreg_ligne += maxi(qte_manquante,15)               #	M   15	Quantité manquante

        enreg_ligne += maxi(espace,3)                           #	C   3	Unité de mesure
        enreg_ligne += maxi(line.name,140)                      #	C   140	Description article
        enreg_ligne += maxi(espace,9)                           #	C   9	Prix unitaire net
        enreg_ligne += maxi(espace,18)                          #	C   18	Montant net de ligne
        enreg_ligne += maxi(espace,8)                           #	C   8	Nombre d'unité de conditionnement
        enreg_ligne += maxi(espace,3)                           #	C   3	Unité de mesure de la quantité
        enreg_ligne += maxi(espace,7)                           #   C   7	Type d'emballage

        enreg_ligne += maxi(espace,14)                          #	C   14	Code EAN UL (DUN 14)
        enreg_ligne += maxi(espace,8)                           #	C   8	Date de livraison
        enreg_ligne += maxi(espace,4)                           #	C   4	heure de livraison
        enreg_ligne += maxi(espace,35)                          #	C   35	n° de commande magasin
        enreg_ligne += maxi(espace,20)                          #	C   20	Code (ou EAN) du magasin
        enreg_ligne += maxi(espace,6)                           #	C   6	Numéro de ligne de la commande d'origine
        enreg_ligne += maxi(espace,35)                          #	C   35	n° de la commande

        date_cde_calc = self.transforme_date_heure(sale.date_order,'date')
        heure_cde_calc = self.transforme_date_heure(sale.date_order,'heure')
        enreg_ligne += maxi(date_cde_calc,8)                    #   M   8	Date de la commande
        enreg_ligne += maxi(heure_cde_calc,4)                   #   M   4	heure de la commande

        enreg_ligne += maxi(espace,35)                          #	C   35	N° de commande remplacée
        enreg_ligne += maxi(espace,35)                          #	C   35	Numéro d'opération promotionnelle
        enreg_ligne += maxi(espace,350)                         #	C   350	Commentaires
        enreg_ligne += maxi(espace,15)                          #	C   15	Différences de quantité
        enreg_ligne += maxi(espace,3)                           #	C   3	Nature de l'écart (en code)

        return enreg_ligne

    #########################################################################################
    #                                                                                       #
    #                                  transforme_date_heure                                #
    #                                                                                       #
    #########################################################################################
    def transforme_date_heure(self, date_origine, type):
        if type=='heure':
            # 
            # On renvoie l'heure sur 4 positions au format HHMM
            #
            retour = '1115'
        else:
            retour = '19690326'

        return retour   

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
    #                                    calcul_poids_brut                                  #
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
            #logger.info("============================================================")
            #logger.info("=         On a envoyé un mail au destinataire reçu         =")
            #logger.info("============================================================")        
        
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

            #logger.info("============================================================")
            #logger.info("=         On a écrit une erreur dans le suivi EDI          =")
            #logger.info("============================================================")            
              
