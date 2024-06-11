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
from ftplib import FTP

import pysftp

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


class ArcCommandeEDIExport(models.TransientModel):
    _name = "apik_edi.wizard_arc_cde"
    _description = "Export des ARC de commandes EDI"
    
    export_date = fields.Date("Date de l'export",default=fields.Date.today())
    arcedi_data = fields.Binary('Fichier Export')
    filename = fields.Char(string='Filename', size=256)
    
    #########################################################################################
    #                                                                                       #
    #                          Bouton Export des ARC de commandes EDI                       #
    #                                                                                       #
    #########################################################################################        
    def export_arc_cde_edi(self):           
        self.ensure_one()
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company                 
        
        partner_obj = self.env['res.partner']
        sale_obj = self.env['sale.order']
        sale_ids = sale_obj.search([('id', 'in', self._context.get('active_ids', True))])
        
        nb_enreg = 1
        rows_to_write = []
        
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

        for sale in sale_ids:           
            if sale.partner_id.client_edi:
                if sale.partner_id.edi_ordrsp:
                    #
                    # On génére l'enregistrement Entête
                    #
                    enreg_ent = self.export_arc_entete(sale)
                    if enreg_ent:
                        rows_to_write.append(enreg_ent)
                        nb_enreg = nb_enreg + 1
                    #
                    # On génère l'enregistrement NAD+BY
                    # 
                    if sale.partner_id:
                        enreg_par = self.export_arc_param('BY',sale) 
                        if enreg_par:
                            rows_to_write.append(enreg_par)
                            nb_enreg = nb_enreg + 1 
                    #
                    # On génère l'enregistrement NAD+SU
                    # 
                    if sale.partner_vendeur_id:
                        enreg_par = self.export_arc_param('SU',sale)
                        if enreg_par:
                            rows_to_write.append(enreg_par)
                            nb_enreg = nb_enreg + 1  
                    #
                    # On génère l'enregistrement NAD+DP
                    # 
                    if sale.partner_shipping_id:
                        enreg_par = self.export_arc_param('DP',sale)
                        if enreg_par:
                            rows_to_write.append(enreg_par)
                            nb_enreg = nb_enreg + 1  
                    #
                    # On génère l'enregistrement NAD+UC
                    # 
                    if sale.partner_final_id:
                        enreg_par = self.export_arc_param('UC',sale)
                        if enreg_par:
                            rows_to_write.append(enreg_par)
                            nb_enreg = nb_enreg + 1  
                    #
                    # On génère l'enregistrement NAD+IV
                    # 
                    if sale.partner_invoice_id:
                        enreg_par = self.export_arc_param('IV',sale)
                        if enreg_par:
                            rows_to_write.append(enreg_par)
                            nb_enreg = nb_enreg + 1  
                    #
                    # On génère l'enregistrement NAD+OB
                    # 
                    if sale.partner_commande_par_id:
                        enreg_par = self.export_arc_param('OB',sale)
                        if enreg_par:
                            rows_to_write.append(enreg_par)
                            nb_enreg = nb_enreg + 1  
                    #
                    # On génère l'enregistrement NAD+PR
                    # 
                    if sale.partner_paye_par_id:
                        enreg_par = self.export_arc_param('PR',sale)
                        if enreg_par:
                            rows_to_write.append(enreg_par)
                            nb_enreg = nb_enreg + 1   
                    #
                    # On génère l'enregistrement NAD+PR
                    # 
                    if sale.partner_paye_par_id:
                        enreg_par = self.export_arc_param('UD',sale)
                        if enreg_par:
                            rows_to_write.append(enreg_par)
                            nb_enreg = nb_enreg + 1            

                    #
                    # On génère les enregistrements ligne
                    # 
                    for line in sale.order_line:      
                        enreg_lig = self.export_arc_ligne(sale,line) 
                        if enreg_lig:
                            rows_to_write.append(enreg_lig)
                            nb_enreg = nb_enreg + 1  
                else:
                    client = partner_obj.search([('id','=', sale.partner_id.id)],limit=1)
                    #
                    # Erreur sur envoi ARC : Client ne recoit pas les ARC en EDI
                    #
                    sujet = str(self.env.company.name) + ' - Gestion EDI - Accusè de reception de commandes du ' + str(today) 
                    corps = "Le client {} ne reçoit pas les accusés de reception en EDI. <br/><br>".format(client.name) 
                    corps+= "L'ARC n'est pas envoyé. <br/><br>"                         
                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                    destinataire = company_id.gestion_user_id.email
                    if destinataire:
                        self.edi_generation_mail(destinataire, sujet, corps)
                    code_erreur = self.env['erreur.edi'].search([('name','=', '0402')], limit=1) 
                    flux = self.env['flux.edi'].search([('name','=', 'ORDRSP')], limit=1)
                    message = "Le client {} ne reçoit pas les accusés de reception en EDI. . L'ARC n'est pas envoyé. ".format(client.name) 
                    self.edi_generation_erreur(code_erreur, flux, sujet, message)    
            else:
                client = partner_obj.search([('id','=', sale.partner_id.id)],limit=1)
                #
                # Erreur sur envoi ARC : Client pas en gestion EDI
                #
                sujet = str(self.env.company.name) + ' - Gestion EDI - Accusè de reception de commandes du ' + str(today) 
                corps = "Le client {} n'est pas en gestion EDI. <br/><br>".format(client.name) 
                corps+= "L'ARC n'est pas envoyé. <br/><br>"                         
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.edi_generation_mail(destinataire, sujet, corps)
                code_erreur = self.env['erreur.edi'].search([('name','=', '0400')], limit=1) 
                flux = self.env['flux.edi'].search([('name','=', 'ORDRSP')], limit=1)
                message = "Le client {} n'est pas en gestion EDI. L'ARC n'est pas envoyé. ".format(client.name) 
                self.edi_generation_erreur(code_erreur, flux, sujet, message)

            #
            # On met à jour la commande
            #
            sale.write({'arc_edi_envoye':True}) 

            client = partner_obj.search([('id','=', sale.partner_id.id)],limit=1)
            #
            # Envoi ARC : Envoi généré
            #
            sujet = str(self.env.company.name) + ' - Gestion EDI - Accusè de reception de commandes du ' + str(today) 
            corps = "L'ARC de la commande {} pour le client {} a été envoyé. <br/><br>".format(sale.name, client.name) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.edi_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.edi'].search([('name','=', '0600')], limit=1) 
            flux = self.env['flux.edi'].search([('name','=', 'ORDRSP')], limit=1)
            message = "L'ARC de la commande {} pour le client {} a été envoyé. ".format(sale.name, client.name) 
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
            gln_societe = company_id.partner_id.code_gln
            if company_id.param_edi_id:
                param = edi_obj.search([('id', '=', company_id.param_edi_id.id)])
                if len(param)>0:        
                    rep_export = param.rep_export_interne_edi 
                    if param.nom_fichier_arc_cde_edi_export:
                        fichier_arc_dest = param.nom_fichier_arc_cde_edi_export.strip()+'_%s_%s' %(gln_societe,datefic) 
                        fichier_arc = fichier_arc_dest+'.txt'                     
                    else:
                        rep_export = 'data/export_ftp'
                        fichier_arc_dest = 'ORDRSP_%s_%s' %(gln_societe,datefic)  
                        fichier_arc = fichier_arc_dest+'.txt'  
                else:
                    rep_export = 'data/export_ftp' 
                    fichier_arc_dest = 'ORDRSP_%s_%s' %(gln_societe,datefic) 
                    fichier_arc = fichier_arc_dest+'.txt'  
            else:
                rep_export = 'data/export_ftp'
                fichier_arc_dest = 'ORDRSP_%s_%s' %(gln_societe,datefic) 
                fichier_arc = fichier_arc_dest+'.txt' 

            self.filename = fichier_arc
            
            logger.info("___________")
            logger.info(rows_to_write)
            logger.info("___________")

            #fich_path = '%s/' % get_module_path('apik_edi') 
            fich_path = rep_export
            fichier_genere = fich_path + '/%s' % self.filename
            
            fichier_ordrsp = open(fichier_genere, "w")
            for rows in rows_to_write:
                retour_chariot = '\n'    #'\r\n'
                #retour_chariot = retour_chariot.encode('ascii')
                rows += retour_chariot
                fichier_ordrsp.write(str(rows))

            fichier_ordrsp.close()   

            fichier_genere_dest = fich_path + '/%s.txt' % fichier_arc_dest   
            fichier_arc_dest_txt = '%s.txt' % fichier_arc_dest  

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
                        ftp.storbinary('STOR '+ fichier_arc_dest, fp)
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
                        sftp.put(fichier_genere_dest,fichier_arc_dest_txt)

            #
            # On déplace le fichier généré dans le répertoire de sauvegarde 
            #
            if company_id.gestion_archivage:
                self.copie_fichier_traite(True, self.filename)

            #
            # Envoi ARC : Fichier généré
            #
            sujet = str(self.env.company.name) + ' - Gestion EDI - Accusè de reception de commandes du ' + str(today) 
            corps = "Le fichier {} des accusés de réception de commande client a été envoyé. <br/><br>".format(fichier_arc) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.edi_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.edi'].search([('name','=', '0601')], limit=1) 
            flux = self.env['flux.edi'].search([('name','=', 'ORDRSP')], limit=1)
            message = "Le fichier {} des accusés de réception de commande client a été envoyé.".format(fichier_arc)
            self.edi_generation_erreur(code_erreur, flux, sujet, message)    
        else:
            raise UserError(_("Aucun accusé de commande EDI à envoyer."))    

    #########################################################################################
    #                                                                                       #
    #                                 Export Enregistrement Entete                          #
    #                                                                                       #
    #########################################################################################   
    def export_arc_entete(self,sale): 
        espace = ' '    
        enreg_entete  = 'ENT' 
        enreg_entete += maxi(sale.edi_destinataire,35)
        enreg_entete += maxi(sale.edi_emetteur,35)
        enreg_entete += maxi(sale.no_cde_client,35)
        #enreg_entete += maxi(sale.code_function_id.name,3)
        enreg_entete += maxi(sale.reponse_cde_edi,3)

        if sale.date_order:
            str_date = str(sale.date_order)
            date_yyyymmdd = str_date[0:4]+str_date[5:7]+str_date[8:10]
            date_hhmm = str_date[11:13]+str_date[14:16]
        else:
            date_yyyymmdd = ''
            date_hhmm = ''
        enreg_entete += maxi(date_yyyymmdd,8)
        enreg_entete += maxi(date_hhmm,4)
        enreg_entete += maxi(espace,8)
        enreg_entete += maxi(espace,4)
        enreg_entete += maxi(espace,8)
        enreg_entete += maxi(espace,4)
        enreg_entete += maxi(espace,8)
        enreg_entete += maxi(espace,4)
        enreg_entete += maxi(espace,8)
        enreg_entete += maxi(espace,4)
        enreg_entete += maxi(sale.no_cde_client,35)
        enreg_entete += maxi(espace,8)
        enreg_entete += maxi(espace,4)
        enreg_entete += maxi(espace,35)
        enreg_entete += maxi(espace,35) 
        enreg_entete += maxi(espace,35)
        enreg_entete += maxi(espace,35)       
        enreg_entete += maxi(espace,8)
        enreg_entete += maxi(espace,4)
        enreg_entete += maxi(sale.currency_id.name,3)
        enreg_entete += maxi(espace,350)
        if sale.comment_edi:
            commentaire_edi =  sale.comment_edi.replace('/n','')
        else:
            commentaire_edi = ''    
        enreg_entete += maxi(commentaire_edi,350)
        enreg_entete += maxi(sale.motif_refus_edi,350)
        enreg_entete += maxi(espace,3)
        enreg_entete += maxi(espace,20)
        enreg_entete += maxi(sale.cond_liv,3)
        enreg_entete += maxi(sale.incoterm.code ,3)
        return enreg_entete

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement Paramétre                         #
    #                                                                                       #
    #########################################################################################   
    def export_arc_param(self,typ_interv,sale): 
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
        espace       = ' '
        enreg_param  = 'PAR'         
        if typ_interv == 'BY':
            enreg_param += 'BY '                                                            # Type d'intervenant (qualifiant)
            enreg_param += maxi(sale.partner_acheteur_id.code_gln,20)                       # Code identifiant de l'intervenant
            enreg_param += maxi(espace,3)                                                   # Type d'identifiant
            enreg_param += maxi(sale.partner_acheteur_id.name,70)                           # Nom de l'intervenant
            enreg_param += maxi(sale.partner_acheteur_id.street,35)                         # Ligne adresse 1 intervenant    
            enreg_param += maxi(sale.partner_acheteur_id.street2,35)                        # Ligne adresse 2 intervenant
            enreg_param += maxi(espace,35)                                                  # Ligne adresse 3 intervenant
            enreg_param += maxi(sale.partner_acheteur_id.zip,9)                             # Code postal intervenant
            enreg_param += maxi(sale.partner_acheteur_id.city,35)                           # Ville intervenant
            enreg_param += maxi(sale.partner_acheteur_id.country_id.code,2)                 # Code pays intervenant
        else:
            if typ_interv == 'SU':
                enreg_param += 'SU '                                                        # Type d'intervenant (qualifiant)
                enreg_param += maxi(sale.partner_vendeur_id.code_gln,20)                    # Code identifiant de l'intervenant
                enreg_param += maxi(espace,3)                                               # Type d'identifiant
                enreg_param += maxi(sale.partner_vendeur_id.name,70)                        # Nom de l'intervenant
                enreg_param += maxi(sale.partner_vendeur_id.street,35)                      # Ligne adresse 1 intervenant    
                enreg_param += maxi(sale.partner_vendeur_id.street2,35)                     # Ligne adresse 2 intervenant
                enreg_param += maxi(espace,35)                                              # Ligne adresse 3 intervenant
                enreg_param += maxi(sale.partner_vendeur_id.zip,9)                          # Code postal intervenant
                enreg_param += maxi(sale.partner_vendeur_id.city,35)                        # Ville intervenant
                enreg_param += maxi(sale.partner_vendeur_id.country_id.code,2)              # Code pays intervenant              
            else:
                if typ_interv == 'DP':
                    enreg_param += 'DP '                                                    # Type d'intervenant (qualifiant)
                    enreg_param += maxi(sale.partner_livre_a_id.code_gln,20)                # Code identifiant de l'intervenant
                    enreg_param += maxi(espace,3)                                           # Type d'identifiant
                    enreg_param += maxi(sale.partner_livre_a_id.name,70)                    # Nom de l'intervenant
                    enreg_param += maxi(sale.partner_livre_a_id.street,35)                  # Ligne adresse 1 intervenant    
                    enreg_param += maxi(sale.partner_livre_a_id.street2,35)                 # Ligne adresse 2 intervenant
                    enreg_param += maxi(espace,35)                                          # Ligne adresse 3 intervenant
                    enreg_param += maxi(sale.partner_livre_a_id.zip,9)                      # Code postal intervenant
                    enreg_param += maxi(sale.partner_livre_a_id.city,35)                    # Ville intervenant
                    enreg_param += maxi(sale.partner_livre_a_id.country_id.code,2)          # Code pays intervenant                  
                else:
                    if typ_interv == 'UC':
                        enreg_param += 'UC '                                                # Type d'intervenant (qualifiant)
                        enreg_param += maxi(sale.partner_final_id.code_gln,20)              # Code identifiant de l'intervenant
                        enreg_param += maxi(espace,3)                                       # Type d'identifiant
                        enreg_param += maxi(sale.partner_final_id.name,70)                  # Nom de l'intervenant
                        enreg_param += maxi(sale.partner_final_id.street,35)                # Ligne adresse 1 intervenant    
                        enreg_param += maxi(sale.partner_final_id.street2,35)               # Ligne adresse 2 intervenant
                        enreg_param += maxi(espace,35)                                      # Ligne adresse 3 intervenant
                        enreg_param += maxi(sale.partner_final_id.zip,9)                    # Code postal intervenant
                        enreg_param += maxi(sale.partner_final_id.city,35)                  # Ville intervenant
                        enreg_param += maxi(sale.partner_final_id.country_id.code,2)        # Code pays intervenant                     
                    else:
                        if typ_interv == 'IV':
                            enreg_param += 'IV '                                            # Type d'intervenant (qualifiant)
                            enreg_param += maxi(sale.partner_facture_a_id.code_gln,20)      # Code identifiant de l'intervenant
                            enreg_param += maxi(espace,3)                                   # Type d'identifiant
                            enreg_param += maxi(sale.partner_facture_a_id.name,70)          # Nom de l'intervenant
                            enreg_param += maxi(sale.partner_facture_a_id.street,35)        # Ligne adresse 1 intervenant    
                            enreg_param += maxi(sale.partner_facture_a_id.street2,35)       # Ligne adresse 2 intervenant
                            enreg_param += maxi(espace,35)                                  # Ligne adresse 3 intervenant
                            enreg_param += maxi(sale.partner_facture_a_id.zip,9)            # Code postal intervenant
                            enreg_param += maxi(sale.partner_facture_a_id.city,35)          # Ville intervenant
                            enreg_param += maxi(sale.partner_facture_a_id.country_id.code,2)# Code pays intervenant                         
                        else:
                            if typ_interv == 'OB':
                                enreg_param += 'OB '                                                # Type d'intervenant (qualifiant)
                                enreg_param += maxi(sale.partner_commande_par_id.code_gln,20)       # Code identifiant de l'intervenant
                                enreg_param += maxi(espace,3)                                       # Type d'identifiant
                                enreg_param += maxi(sale.partner_commande_par_id.name,70)           # Nom de l'intervenant
                                enreg_param += maxi(sale.partner_commande_par_id.street,35)         # Ligne adresse 1 intervenant    
                                enreg_param += maxi(sale.partner_commande_par_id.street2,35)        # Ligne adresse 2 intervenant
                                enreg_param += maxi(espace,35)                                      # Ligne adresse 3 intervenant
                                enreg_param += maxi(sale.partner_commande_par_id.zip,9)             # Code postal intervenant
                                enreg_param += maxi(sale.partner_commande_par_id.city,35)           # Ville intervenant
                                enreg_param += maxi(sale.partner_commande_par_id.country_id.code,2) # Code pays intervenant                           
                            else:    
                                if typ_interv == 'PR':
                                    enreg_param += 'PR '                                            # Type d'intervenant (qualifiant)
                                    enreg_param += maxi(sale.partner_paye_par_id.code_gln,20)       # Code identifiant de l'intervenant
                                    enreg_param += maxi(espace,3)                                   # Type d'identifiant
                                    enreg_param += maxi(sale.partner_paye_par_id.name,70)           # Nom de l'intervenant
                                    enreg_param += maxi(sale.partner_paye_par_id.street,35)         # Ligne adresse 1 intervenant    
                                    enreg_param += maxi(sale.partner_paye_par_id.street2,35)        # Ligne adresse 2 intervenant
                                    enreg_param += maxi(espace,35)                                  # Ligne adresse 3 intervenant
                                    enreg_param += maxi(sale.partner_paye_par_id.zip,9)             # Code postal intervenant
                                    enreg_param += maxi(sale.partner_paye_par_id.city,35)           # Ville intervenant
                                    enreg_param += maxi(sale.partner_paye_par_id.country_id.code,2) # Code pays intervenant                               
                                else:    
                                    if typ_interv == 'UD':
                                        enreg_param += 'UD '                                            # Type d'intervenant (qualifiant)
                                        enreg_param += maxi(sale.partner_final_ud_id.code_gln,20)       # Code identifiant de l'intervenant
                                        enreg_param += maxi(espace,3)                                   # Type d'identifiant
                                        enreg_param += maxi(sale.partner_final_ud_id.name,70)           # Nom de l'intervenant
                                        enreg_param += maxi(sale.partner_final_ud_id.street,35)         # Ligne adresse 1 intervenant    
                                        enreg_param += maxi(sale.partner_final_ud_id.street2,35)        # Ligne adresse 2 intervenant
                                        enreg_param += maxi(espace,35)                                  # Ligne adresse 3 intervenant
                                        enreg_param += maxi(sale.partner_final_ud_id.zip,9)             # Code postal intervenant
                                        enreg_param += maxi(sale.partner_final_ud_id.city,35)           # Ville intervenant
                                        enreg_param += maxi(sale.partner_final_ud_id.country_id.code,2) # Code pays intervenant

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
    def export_arc_ligne(self,sale,line): 
        espace       = ' '
        enreg_ligne  = 'LIG'       
        enreg_ligne	+= maxi(line.no_ligne_edi,6)                #	6	n° de ligne article
        enreg_ligne	+= maxi(line.product_id.barcode,35)         #   35	Code EAN article
        enreg_ligne	+= maxi(sale.code_function_id.name,3)       #	3	Code fonction
        enreg_ligne += maxi(espace,35)                          #	35	Code article vendeur
        enreg_ligne += maxi(espace,35)                          #	35	Code article acheteur
        enreg_ligne += maxi(espace,35)                          #	35	Code EAN article remplace
        enreg_ligne += maxi(espace,18)                          #	18	n° de lot
        enreg_ligne += maxi(line.name,140)                      #	140	Description article
        str_qty  = str(line.product_uom_qty)                   
        enreg_ligne += maxi(str_qty,15)                         #	15	Quantité expédiée
        enreg_ligne += maxi(str_qty,15)                         #	15	Quantité commandée
        enreg_ligne += maxi(espace,15)                          #	15	Quantité rejetée
        enreg_ligne += maxi(espace,15)                          #	15	Quantité gratuit
        enreg_ligne += maxi(espace,15)                          #	15	Quantité non reconnue
        enreg_ligne += maxi(espace,15)                          #	15	Quantité en rupture de stock
        enreg_ligne += maxi(espace,15)                          #	15	Quantité restante à livrer
        enreg_ligne += maxi(espace,3)                           #	3	Unité de mesure de la quantité
        enreg_ligne += maxi(espace,9)                           #  9	Prix unitaire Brut
        enreg_ligne += maxi(espace,9)                           #	9	Prix unitaire net
        enreg_ligne += maxi(espace,17)                          #	17	Taux de TVA
        enreg_ligne += maxi(espace,3)                           #	3	Catégorie TVA 1
        enreg_ligne += maxi(espace,9)                           #	9	Ancien Prix unitaire net
        enreg_ligne += maxi(espace,8)                           #	8	Date de livraison
        enreg_ligne += maxi(espace,4)                           #	4	heure de livraison
        enreg_ligne += maxi(espace,8)                           #	8	Date d'expéditon
        enreg_ligne += maxi(espace,4)                           #	4	heure d'expéditon
        enreg_ligne += maxi(espace,8)                           #	8	Date d'enlèvement
        enreg_ligne += maxi(espace,4)                           #	4	heure d'enlèvement
        enreg_ligne += maxi(espace,8)                           #	8	Date de livraison demandée dans la commande intitiale
        enreg_ligne += maxi(espace,4)                           #	4	Heure de livraison demandée dans la commande intitiale
        enreg_ligne += maxi(espace,8)                           #	8	Date de disponibilité
        enreg_ligne += maxi(espace,4)                           #	4	heure de disponibilité
        enreg_ligne += maxi(espace,8)                           #	8	Date de livraison Estime
        enreg_ligne += maxi(espace,4)                           #	4	heure de livraison Estime
        enreg_ligne += maxi(espace,6)                           #	6	Numéro de ligne de la commande d'origine
        enreg_ligne += maxi(espace,35)                          #	35	n° de commande
        enreg_ligne += maxi(espace,8)                           #	8	date de la commande d'origine
        enreg_ligne += maxi(espace,4)                           #	4	heure de la commande d'origine
        enreg_ligne += maxi(espace,35)                          #	35	n° de contrat
        enreg_ligne += maxi(espace,35)                          #	35	N° d'opération promotionnelle
        enreg_ligne += maxi(espace,15)                          #	15	Différences de quantité
        enreg_ligne += maxi(espace,3)                           #	3	Nature de l'écart (en code)
        enreg_ligne += maxi(espace,350)                         #	350	Commentaires de Livraison
        enreg_ligne += maxi(espace,350)                         #	350	Commentaires de Commande
        enreg_ligne += maxi(espace,350)                         #	350	Autre Commentaire
        return enreg_ligne

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
                        #'date_mvt_edi': today,
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
    #             On déplace le fichier traité dans les répertoires de stockage             #
    #                                                                                       #
    #########################################################################################
    def copie_fichier_traite(self,trait_ok,filename):
        company_id =  self.env.company 
        edi_obj = self.env['parametre.edi']
        param = edi_obj.search([('id', '=', company_id.param_edi_id.id)])
        if len(param)>0:
            fichier_path = '%s/' % get_module_path('apik_edi') 
            rep_depart = fichier_path + param.rep_import_interne_edi.strip()
            fichier = filename.strip()
            fichier_a_deplacer = rep_depart + '/' + fichier
            if trait_ok:
                #
                # On transfère le fichier dans le répertoire de stockage ok
                #
                rep_destination = fichier_path + param.rep_sauvegarde_fichier_traite.strip()
            else:
                #
                # On transfère le fichier dans le répertoire de stockage des fichiers en échec
                #
                rep_destination = fichier_path + param.rep_sauvegarde_fichier_erreur.strip()

            ordre_a_executer = 'mv %s %s '%(fichier_a_deplacer, rep_destination)
            exec = os.system(ordre_a_executer)

            copy_ok = True   
        else:
            copy_ok = False 
          