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


class InvoicEDIExport(models.TransientModel):
    _name = "apik_edi.wizard_invoic"
    _description = "Export des Factures EDI"
    
    export_date = fields.Date("Date de l'export",default=fields.Date.today())
    arcedi_data = fields.Binary('Fichier Export')
    filename = fields.Char(string='Filename', size=256)


    def export_invoic_edi(self):           
        self.ensure_one()
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company  

        raise UserError(_("Aucune facture EDI à envoyer."))  
    
    #########################################################################################
    #                                                                                       #
    #                               Bouton Export des Factures EDI                          #
    #                                                                                       #
    #########################################################################################        
    def export_invoic_edi_old(self):           
        self.ensure_one()
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company                 
        
        partner_obj = self.env['res.partner']
        sale_obj = self.env['sale.order']
        move_obj = self.env['account.move']
        move_ids = move_obj.search([('id', 'in', self._context.get('active_ids', True))])
        
        nb_enreg = 1
        rows_to_write = []

        for move in move_ids:           
            if move.partner_id.client_edi:
                if move.partner_id.edi_invoic:
                    #
                    # On recherche la première commande de vente rattaché à la facture
                    #
                    if move.invoice_origin:
                        commande_origine = self.recherche_commande_origin(move.invoice_origin)
                        if commande_origine:
                            sale = sale_obj.search([('id', '=', commande_origine)],limit=1)
                            if len(sale)>0:
                                if sale.commande_edi:                                      
                                    #
                                    # On génére l'enregistrement Entête
                                    #
                                    enreg_ent = self.export_invoic_entete(move,sale)
                                    if enreg_ent:
                                        rows_to_write.append(enreg_ent)
                                        nb_enreg = nb_enreg + 1
                                    #
                                    # On génère l'enregistrement NAD+BY
                                    # 
                                    enreg_par = self.export_invoic_param('BY',move,sale) 
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1 
                                    #
                                    # On génère l'enregistrement NAD+SU
                                    # 
                                    enreg_par = self.export_invoic_param('SU',move,sale)
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1  
                                    #
                                    # On génère l'enregistrement NAD+DP
                                    # 
                                    enreg_par = self.export_invoic_param('DP',move,sale)
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1  
                                    #
                                    # On génère l'enregistrement NAD+UC
                                    # 
                                    enreg_par = self.export_invoic_param('UC',move,sale)
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1  
                                    #
                                    # On génère l'enregistrement NAD+IV
                                    # 
                                    enreg_par = self.export_invoic_param('IV',move,sale)
                                    if enreg_par:
                                        rows_to_write.append(enreg_par)
                                        nb_enreg = nb_enreg + 1  
                                    #
                                    # On génère les enregistrements ligne
                                    # 
                                    for line in move.invoice_line_ids:      
                                        enreg_lig = self.export_invoic_ligne(move,sale,line) 
                                        if enreg_lig:
                                            rows_to_write.append(enreg_lig)
                                            nb_enreg = nb_enreg + 1 
                                    #
                                    # On génére l'enregistrement Pied
                                    #
                                    enreg_pie = self.export_invoic_pied(move)
                                    if enreg_pie:
                                        rows_to_write.append(enreg_pie)
                                        nb_enreg = nb_enreg + 1
                                    #
                                    # On génére l'enregistrement TVA
                                    #
                                    detail_tva = move.amount_by_group
                                    nb_tx = len(detail_tva)
                                    if nb_tx >= 1:
                                        nb = 0
                                        while nb < nb_tx:
                                            lig_tva = str(detail_tva[nb])
                                            lig_tva = lig_tva.replace('(','')
                                            lig_tva = lig_tva.replace(')','')
                                            cpt = 0
                                            enr_tva = []
                                            for ltva in lig_tva.split(','):
                                                cpt = cpt + 1
                                                if cpt == 1:
                                                    values_1 = ltva
                                                if cpt == 2:
                                                    values_2 = ltva
                                                if cpt == 3:
                                                    values_3 = ltva
                                                    values_tva = {'taux_tva': values_1,
                                                                  'mtt_tva': values_2,
                                                                  'base_tva': values_3,
                                                                  }
                                                    enr_tva.append(values_tva) 

                                            enreg_tva = self.export_invoic_tva(enr_tva)
                                            if enreg_tva:
                                                rows_to_write.append(enreg_tva)
                                                nb_enreg = nb_enreg + 1
                                            nb += 1    
                                else:
                                    #
                                    # Erreur sur envoi INVOIC : La commande associée n'est pas une commande EDI
                                    #
                                    sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du ' + str(today) 
                                    corps = "Aucune commande associée à la facture {} n'est pas une commande EDI. <br/><br>".format(move.name) 
                                    corps+= "L'INVOIC n'est pas envoyé. <br/><br>"                         
                                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                                    destinataire = company_id.gestion_user_id.email
                                    if destinataire:
                                        self.edi_generation_mail(destinataire, sujet, corps)
                                    code_erreur = self.env['erreur.edi'].search([('name','=', '0802')], limit=1) 
                                    flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                                    message = "Aucune commande associée à la facture {} n'est pas une commande EDI. L'INVOIC n'est pas envoyé.".format(move.name) 
                                    self.edi_generation_erreur(code_erreur, flux, sujet, message) 
                            else:                                 
                                #
                                # Erreur sur envoi INVOIC : La commande associée n'est pas une commande EDI
                                #
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du ' + str(today) 
                                corps = "Aucune commande associée à la facture {} n'est pas une commande EDI. <br/><br>".format(move.name) 
                                corps+= "L'INVOIC n'est pas envoyé. <br/><br>"                         
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)
                                code_erreur = self.env['erreur.edi'].search([('name','=', '0802')], limit=1) 
                                flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                                message = "Aucune commande associée à la facture {} n'est pas une commande EDI. L'INVOIC n'est pas envoyé.".format(move.name) 
                                self.edi_generation_erreur(code_erreur, flux, sujet, message) 
                        else:
                            #
                            # Erreur sur envoi INVOIC : La commande associée n'existe plus
                            #
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du ' + str(today) 
                            corps = "La commande associée à la facture {} n'existe plus dans la base Odoo. <br/><br>".format(move.name) 
                            corps+= "L'INVOIC n'est pas envoyé. <br/><br>"                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.edi_generation_mail(destinataire, sujet, corps)
                            code_erreur = self.env['erreur.edi'].search([('name','=', '0702')], limit=1) 
                            flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                            message = "La commande associée à la facture {} n'existe plus dans la base Odoo. L'INVOIC n'est pas envoyé.".format(move.name) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)  
                    else:
                        #
                        # facture sans document d'origine
                        # 
                        #
                        # Erreur sur envoi INVOIC : Livraison sans document d'origine
                        #
                        sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du ' + str(today) 
                        corps = "La facture {} n'est pas rattachée à une commande dans la base Odoo. <br/><br>".format(move.name) 
                        corps+= "L'INVOIC n'est pas envoyé. <br/><br>"                         
                        corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                        destinataire = company_id.gestion_user_id.email
                        if destinataire:
                            self.edi_generation_mail(destinataire, sujet, corps)
                        code_erreur = self.env['erreur.edi'].search([('name','=', '0703')], limit=1) 
                        flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                        message = "La facture {} n'est pas rattachée à une commande dans la base Odoo. L'INVOIC n'est pas envoyé.".format(move.name) 
                        self.edi_generation_erreur(code_erreur, flux, sujet, message)      
                else:
                    client = partner_obj.search([('id','=', move.partner_id.id)],limit=1)
                    #
                    # Erreur sur envoi ARC : Client ne recoit pas les factures en EDI
                    #
                    sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du ' + str(today) 
                    corps = "Le client {} ne reçoit pas les factures en EDI. <br/><br>".format(client.name) 
                    corps+= "L'INVOIC n'est pas envoyé. <br/><br>"                         
                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                    destinataire = company_id.gestion_user_id.email
                    if destinataire:
                        self.edi_generation_mail(destinataire, sujet, corps)
                    code_erreur = self.env['erreur.edi'].search([('name','=', '0405')], limit=1) 
                    flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                    message = "Le client {} ne reçoit pas les factures en EDI. L'INVOIC n'est pas envoyé. ".format(client.name) 
                    self.edi_generation_erreur(code_erreur, flux, sujet, message)    
            else:
                client = partner_obj.search([('id','=', move.partner_id.id)],limit=1)
                #
                # Erreur sur envoi ARC : Client pas en gestion EDI
                #
                sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du  ' + str(today) 
                corps = "Le client {} n'est pas en gestion EDI. <br/><br>".format(client.name) 
                corps+= "L' INVOIC n'est pas envoyé. <br/><br>"                         
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.edi_generation_mail(destinataire, sujet, corps)
                code_erreur = self.env['erreur.edi'].search([('name','=', '0400')], limit=1) 
                flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                message = "Le client {} n'est pas en gestion EDI. L'INVOIC n'est pas envoyé. ".format(client.name) 
                self.edi_generation_erreur(code_erreur, flux, sujet, message)

            #
            # On met à jour la commande
            #
            move.write({'invoic_edi_envoye':True}) 

            client = partner_obj.search([('id','=', move.partner_id.id)],limit=1)
            #
            # Envoi ARC : Envoi généré
            #
            sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du ' + str(today) 
            corps = "La facture {} pour le client {} a été envoyé. <br/><br>".format(move.name, client.name) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.edi_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.edi'].search([('name','=', '0800')], limit=1) 
            flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
            message = "La facture {} pour le client {} a été envoyé. ".format(move.name, client.name) 
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
                        fichier_invoic = param.nom_fichier_invoic_edi_export.strip()+'_%s.txt' %(datefic) 
                    else:
                        rep_export = 'data/export_ftp'
                        fichier_invoic = 'INVOIC_%s.txt' %(datefic)  
                else:
                    rep_export = 'data/export_ftp' 
                    fichier_invoic = 'INVOIC_%s.txt' %(datefic) 
            else:
                rep_export = 'data/export_ftp' 
                fichier_invoic = 'INVOIC_%s.txt' %(datefic) 
             

            self.filename = fichier_invoic
            
            #fich_path = '%s/' % get_module_path('apik_edi') 
            fich_path = rep_export
            fichier_genere = fich_path + '/%s' % self.filename
            
            fichier_invoic_genere = open(fichier_genere, "w")
            for rows in rows_to_write:
                retour_chariot = '\n'    #'\r\n'
                #retour_chariot = retour_chariot.encode('ascii')
                rows += retour_chariot
                fichier_invoic_genere.write(str(rows))
                
            fichier_invoic_genere.close()        
        
            #
            # ICI
            # On envoie le fichier généré par FTP
            #

            #
            # ICI
            # On déplace le fichier généré dans le répertoire de sauvegarde 
            #

            #
            # Envoi INVOIC : Fichier généré
            #
            sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du ' + str(today) 
            corps = "Le fichier {} des factures client a été envoyé. <br/><br>".format(fichier_invoic) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.edi_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.edi'].search([('name','=', '0801')], limit=1) 
            flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
            message = "Le fichier {} des factures client a été envoyé.".format(fichier_invoic)
            self.edi_generation_erreur(code_erreur, flux, sujet, message)    
        else:
            raise UserError(_("Aucune facture EDI à envoyer."))    

    #########################################################################################
    #                                                                                       #
    #                                 Export Enregistrement Entete                          #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_entete(self,move,sale): 
        company_id =  self.env.company 
        espace = ' '    
        enreg_entete  = 'ENT' 
        enreg_entete += maxi(sale.edi_emetteur,35)              #   M   4	38	an	35	N° Emetteur
        enreg_entete += maxi(sale.edi_destinataire,35)          #   M   39	73	an	35	N° Destinataire
        if move.move_type == 'out_refund':
            enreg_entete += '381'                               #   M   74	76	n	3	Type de facture
        else:    
            enreg_entete += '380'                               #   M   74	76	n	3	Type de facture
        enreg_entete += maxi(move.name,35)                      #   M   77	111	an	35	N° de facture
        date_invoic_calc = self.transforme_date_heure(move.invoice_date,'date')
        heure_invoic_calc = self.transforme_date_heure(move.invoice_date,'heure')
        enreg_entete += maxi(date_invoic_calc,8)                #   M   112	119	n	8	Date de facture
        enreg_entete += maxi(heure_invoic_calc,4)               #   M   120	123	n	4	Heure de facture
        enreg_entete += maxi(company_id.name,70)                #   M   124	193	an	70	Dénomination sociale vendeur
        enreg_entete += maxi(company_id.type_societe,70)        #   M   194	263	an	70	Type de société vendeur
        enreg_entete += maxi(company_id.capital_social,70)      #   M   264	333	an	70	Capital social vendeur
        enreg_entete += maxi(move.currency_id.name,3)           #   M   334	336	an	3	Devise de facture
        enreg_entete += maxi(espace,3)                          #   C   337	339	an	3	Devise de paiement
        enreg_entete += maxi(espace,12)                         #   C   340	351	an	12	Taux de change
        enreg_entete += maxi(sale.no_cde_client,35)             #   M   352	386	an	35	n° de la commande
        date_cde_calc = self.transforme_date_heure(sale.date_order,'date')
        enreg_entete += maxi(date_cde_calc,8)                   #   M   387	394	n	8	Date de la commande
        picking = self.recherche_bon_livraison_client(sale)
        if picking:
            date_liv_calc = self.transforme_date_heure(picking.date_done,'date')
            enreg_entete += maxi(picking.name,35)               #   M   395	429	n	8	No de DESADV
            enreg_entete += maxi(date_liv_calc,8)               #   M   430	437	n	8	Date de DESADV
        else:
            enreg_entete += maxi(espace,35)                     #   M   395	429	n	8	No de DESADV
            enreg_entete += maxi(espace,8)                      #   M   430	437	n	8	Date de DESADV
        enreg_entete += maxi(espace,35)                         #   C   438 472 an  35  N° de contrat
        enreg_entete += maxi(move.name,35)                      #   M   473	507	an	35	N° de facture origine
        enreg_entete += maxi(date_invoic_calc,8)                #   M   508	515	n	8	Date de facture origine
        enreg_entete += maxi(espace,35)                         #   C   516 550 an  35  N° de retour
        enreg_entete += maxi(espace,8)                          #   C   551 558 n   8   Date de retour
        enreg_entete += maxi(espace,8)                          #   C   559 566 n   8   Date du taux de change
        date_ech_calc = self.transforme_date_heure(move.invoice_date_due,'date')
        enreg_entete += maxi(date_ech_calc,8)                   #   M   567	574	n	8	Date d'échéance du règlement
        enreg_entete += maxi(espace,3)                          #   C   575	577	n	3	Nombre de jour avant la date d'échéance
        if picking:
            date_liv_calc = self.transforme_date_heure(picking.date_done,'date')
            enreg_entete += maxi(date_liv_calc,8)               #   M   578	585	n	8	Date réelle de livraison
            enreg_entete += maxi(date_liv_calc,8)               #   M   586	593	n	8	Date d'expédition
            enreg_entete += maxi(date_liv_calc,8)               #   M   594	601	n	8	Date d'enlèvement
        else:
            enreg_entete += maxi(espace,8)                      #   M   578	585	n	8	Date réelle de livraison
            enreg_entete += maxi(espace,8)                      #   M   586	593	n	8	Date d'expédition
            enreg_entete += maxi(espace,8)                      #   M   594	601	n	8	Date d'enlèvement  
        enreg_entete += maxi(move.payment_mode_id.payment_method_edi.name,2)    #   M   602	603	n	2	Moyen de paiement
        enreg_entete += maxi(espace,3)                          #   C   604	613	an	10	Pourcentage des pénalités
        enreg_entete += maxi(espace,3)                          #   C   614	614	n	1	Régime TVA
        enreg_entete += maxi(move.invoice_incoterm_id.code,3)   #   C   615	617	an	3	Conditions Incoterms

        return enreg_entete

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement Paramétre                         #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_param(self,typ_interv,move,sale): 

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
    def export_invoic_ligne(self,move,sale,line): 

        espace       = ' '
        enreg_ligne  = 'LIG'                                    #   M   3	LIG    
        #enreg_ligne	+= maxi(line.no_ligne_edi,6)            #	M   6	n° de ligne article
        enreg_ligne	+= maxi(espace,6)                           #	M   6	n° de ligne article
        enreg_ligne	+= maxi(line.product_id.barcode,35)         #   M   35	Code EAN article
        enreg_ligne += maxi(espace,35)                          #	C   35	Code article vendeur
        enreg_ligne += maxi(espace,35)                          #	C   35	Code article acheteur
        enreg_ligne += maxi(line.name,140)                      #	M   140	Description article
        enreg_ligne += maxi(espace,140)                         #	M   140	Certification Bio        

        enreg_ligne += maxi(line.quantity,15)                   #	M   15	Quantité facturée
        enreg_ligne += maxi(espace,3)                           #	M   3	Unité de quantité facturée
        enreg_ligne += maxi(espace,15)                          #	M   15	Quantité gratuite
        enreg_ligne += maxi(espace,3)                           #	M   3	Unité de quantité gratuite
        enreg_ligne += maxi(espace,15)                          #	C   15	Quantité par colis (PCB)
        enreg_ligne += maxi(espace,3)                           #	C   3	Unité de quantité par colis

        enreg_ligne += maxi(line.price_subtotal,18)             #	M   18	Montant net de ligne
        enreg_ligne += maxi(line.price_unit,15)                 #	M   15	Prix brut unitaire
        enreg_ligne += maxi(line.price_unit,9)                  #	M   9	Base de prix brut unitaire
        enreg_ligne += maxi(espace,3)                           #	M   3	Unité de base de prix brut unitaire
        if line.quantity:
            punet = line.price_subtotal / line.quantity
        else:
            punet = 0   
        enreg_ligne += maxi(punet,15)                           #	M   15	Prix net unitaire
        enreg_ligne += maxi(espace,3)                           #	M   3	Unité de prix net unitaire
        enreg_ligne += maxi(punet,9)                            #	M   9	Base de prix net unitaire
        enreg_ligne += maxi(espace,3)                           #	M   3	Unité de base de prix net unitaire
        enreg_ligne += maxi(espace,5)                           #	C   5	Taux de TVA

        return enreg_ligne

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement Pied                              #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_pied(self,move): 

        espace      = ' '
        enreg_pied  = 'PIE'                                    #    M   3	PIE    
        enreg_pied += maxi(move.amount_untaxed,18)             #    M   18	Montant taxable
        enreg_pied += maxi(move.amount_total,18)               #    M   18	Montant TTC
        enreg_pied += maxi(move.amount_tax,18)                 #	M   18	Montant Taxe
        enreg_pied += maxi(espace,18)                          #	C   18	Montant net ristournable
        enreg_pied += maxi(espace,18)                          #	C   18	Montant total des taxes dont parafiscales

        return enreg_pied

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement TVA                               #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_tva(self,enr_tva): 

        espace      = ' '
        tx_tva = enr_tva[0].get('taux_tva')
        tx_tva = tx_tva.replace("'TVA ","")
        tx_tva = tx_tva.replace("%'","")

        lg_tx = len(tx_tva)
        if lg_tx == 0:
            tx_tva = '00.00'
        if lg_tx == 1:
            tx_tva = '0'+tx_tva+'.00'  
        if lg_tx == 2:
            tx_tva = tx_tva+'.00' 
        if lg_tx == 3:
            tx_tva = tx_tva+'00'
        if lg_tx == 4:
            tx_tva = tx_tva+'0'

        mtt_tva = enr_tva[0].get('mtt_tva').strip()
        base_tva = enr_tva[0].get('base_tva').strip()

        enreg_taxe  = 'TXP'                                    #    M   3	TXP    
        enreg_taxe += maxi(tx_tva,5)                           #    M   5	Taux de TVA
        enreg_taxe += maxi(base_tva,18)                        #    M   18	Montant taxable
        enreg_taxe += maxi(espace,1)                           #	M   1	Catégorie TVA
        enreg_taxe += maxi(mtt_tva,18)                         #	M   18	Montant TVA

        return enreg_taxe     




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
    def calcul_poids_brut(self, move):
        poids = 0
        for line in move.move_line_ids:
            poids += (line.product_id.weight * line.qty_done)        

        return poids  

    #########################################################################################
    #                                                                                       #
    #                                    calcul_poids_brut                                  #
    #                                                                                       #
    #########################################################################################
    def calcul_qte_manquante(self, move,sale,line):
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
        company_id =  self.env.company 
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
              
    #########################################################################################
    #                                                                                       #
    #                                Recherche Commande Origine                             #
    #                                                                                       #
    #########################################################################################
    def recherche_commande_origin(self,invoice_origin):
        sale_obj = self.env['sale.order']
        if invoice_origin:
            for origin in invoice_origin.split():
                if origin != ',': 
                    sale = sale_obj.search([('name', '=', origin)],limit=1)
                    if len(sale)>0:
                        if sale.commande_edi:
                            commande_origine = sale.id
                            break
                        else:
                            commande_origine = False
                    else:
                        commande_origine = False        
                else:
                    commande_origine = False
            else:
                commande_origine = False
        else:
            commande_origine = False
        return commande_origine  

    #########################################################################################
    #                                                                                       #
    #                                Recherche BL Client                                    #
    #                                                                                       #
    #########################################################################################
    def recherche_bon_livraison_client(self,sale):
        livraison = False

        return livraison
