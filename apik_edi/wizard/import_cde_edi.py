# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import timedelta, datetime

from tempfile import TemporaryFile
import base64
import io
import logging
logger = logging.getLogger(__name__)

from odoo.modules import get_module_resource
from odoo.modules import get_module_path

import os
import ftplib
import subprocess
import pysftp

from odoo.addons.apik_calendar.models import apik_calendar

class CommandeEDIImport(models.TransientModel):
    _name = "commande.edi.import"
    _description = "Import des commandes EDI"
    
    file_to_import = fields.Binary(
        string='Fichier à importer', required=True,
        help="Fichier contenant les commandes EDI à importer.")
    filename = fields.Char()
    file_format = fields.Selection([
        ('edi_tx2', 'EDI (TX2)'),
        ('edi_agp', 'EDI (@Gp)'),
        ('edi_csv', 'EDI (csv)'),
        ], string='Format du fichier', required=True, default="_calcul_format_edi")
    file_encoding = fields.Selection([
        ('ascii', 'ASCII'),
        ('latin1', 'ISO 8859-15 (alias Latin1)'),
        ('utf-8', 'UTF-8'),
        ('utf-8-sig', 'UTF-8 with BOM')
        ], string='Type Encodage du fichier', default='latin1')
    edi_txt_field_separator = fields.Selection([('aucun','pas de séparateur'),
        ('pipe', '| (pipe)'),
        ('tab', 'Tabulation'),
        ], string='Séparateur de champ', default='aucun')
    import_auto = fields.Boolean("Import automatique par FTP",default=True,required=True)
    type_fichier = fields.Char("Type de fichier import", required=False)
    
    #########################################################################################
    #                                                                                       #
    #                                   calcul_format_edi                                   #
    #                                                                                       #
    #########################################################################################     
    def _calcul_format_edi(self):
        edi_obj = self.env['parametre.edi']
        company_id =  self.env.company
        file_format=''
        if company_id.param_edi_id:
            param = edi_obj.search([('id', '=', company_id.param_edi_id.id)])
            if len(param)>0:
                if param.file_format:
                    file_format = param.file_format
                else:
                    file_format = 'edi_csv'
            else:
                file_format = 'edi_csv'
        else:
            file_format = 'edi_csv'

        return file_format
   
    #########################################################################################
    #                                                                                       #
    #                                   Traitement du fichier                               #
    #                                                                                       #
    #########################################################################################     
    def file2import_edi(self, fileobj, file_bytes, fichier_import):
        file_format = self.file_format
        if file_format == 'edi_tx2':

            type_fichier_a_traiter = fichier_import[0:6]

            if type_fichier_a_traiter == 'ORDCHG':
                return self.edi_import_tx2_import_ordchg(file_bytes,fichier_import)
            else:
                return self.edi_import_tx2_import_orders(file_bytes,fichier_import)
        else:
            if file_format == 'edi_agp':
                return self.edi_import_agp_import_edi(file_bytes, fichier_import)
            else:    
                raise UserError(_("Vous devvez sélectionner un fichier au format EDI."))

    #########################################################################################
    #                                                                                       #
    #                               Bouton import des commandes EDI                         #
    #                                                                                       #
    #########################################################################################                  
    def run_import_cde_edi(self):
        self.ensure_one()
        company_id =  self.env.company  
        today = fields.Date.to_string(datetime.now())   

        logger.info("**********************************************")
        logger.info("*  lancement de l'import des commandes EDI   *")
        logger.info(self.env.company.name)
        logger.info("**********************************************")

        sujet = str(self.env.company.name) + ' - Lancement Intégration Commandes EDI : ' + str(today)        
        code_erreur = self.env['erreur.edi'].search([('name','=', '9000')], limit=1) 
        flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1)        
        message = "Le traitement de l'intégration des commandes EDI a été lancé sur la société {} . ".format(str(self.env.company.name) )  
        self.edi_generation_erreur(code_erreur, flux, sujet, message)   

        if self.import_auto:
            edi_obj = self.env['parametre.edi']
            param = edi_obj.search([('id', '=', company_id.param_edi_id.id)])
            if len(param)>0:  
                if param.type_connexion == 'ftp':
                    #
                    # Connexion FTP 
                    #  
                    ftp_user = param.compte_ftp_edi
                    ftp_password = param.mdp_edi
                    adresse_ftp = param.adresse_ftp
                    ftp_port = param.port_ftp
                    rep_recup_ftp = param.repertoire_recup_edi
                                            
                    rep_import = param.rep_import_interne_edi
                    if not rep_import:
                        rep_import = '/tmp'
                    
                    fich_path = rep_import
                    fichier_import = param.nom_fichier_cde_edi_import
                    if not fichier_import:
                        fichier_import = 'ORDERS*'
                    
                    fich_edi = fich_path + '/%s' % fichier_import

                    ftp = ftplib.FTP() 
                    ftp.connect(adresse_ftp, ftp_port, 30*5) 
                    ftp.login(ftp_user, ftp_password)             
                    passif=True
                    ftp.set_pasv(passif)
                    ftp.cwd(rep_recup_ftp)
                    #fich_copie = os.path.basename(fich_edi)
                                
                    filenames = ftp.nlst()

                    for filename in filenames:

                        fileobj = TemporaryFile('wb+')
                        fich_integ_edi = fich_path + '/%s' % filename
                        fichier_import = filename

                        if filename == '.' or filename == '..':
                            continue

                        fich_copie = os.path.basename(fich_integ_edi)
                        fichier_cde_edi = open(fich_integ_edi, "wb")                
                        with fichier_cde_edi as f:
                            ftp.retrbinary('RETR ' + fichier_import, f.write)                
                        #fichier_donnees_edi = os.path.basename(fich_integ_edi)    
                        with open(fich_integ_edi, "rb") as fileread:
                            byte_data = fileread.read()
                        file_bytes = byte_data
                        fileobj.write(file_bytes)
                        fileobj.seek(0)  # We must start reading from the beginning !

                        lignes = self.file2import_edi(fileobj, file_bytes, fichier_import)
                        fileobj.close()

                        if lignes:
                            moves = self.create_commande_edi_from_import_edi(lignes)
                        else:
                            moves = False

                        logger.info("____________________________________")
                        logger.info("On met à jour la base de données EDI")
                        logger.info("____________________________________")
                        self.env.cr.commit()
                        #
                        # On supprime le fichier sur le serveur FTP
                        #
                        ftp.delete(filename)

                        logger.info("_____________________________________________")
                        logger.info("Suppression du fichier sur le serveur FTP EDI")
                        logger.info(filename)
                        logger.info("_____________________________________________")

                        if moves:
                            if company_id.gestion_archivage:
                                self.copie_fichier_traite(True, fichier_import)
                            else:
                                self.delete_fichier_traite(fichier_import)    
                        else:
                            if company_id.gestion_archivage:
                                self.copie_fichier_traite(False, fichier_import)
                            else:
                                self.delete_fichier_traite(fichier_import)       

                    ftp.quit()   
                else:
                    #
                    # Connexion SFTP 
                    #  
                    sftp_user = param.compte_ftp_edi
                    sftp_password = param.mdp_edi
                    sftp_url = param.adresse_ftp
                    sftp_port = param.port_ftp
                    rep_recup_sftp = param.repertoire_recup_edi
                    cnopts = pysftp.CnOpts()
                    cnopts.hostkeys = None
                                            
                    rep_import = param.rep_import_interne_edi
                    if not rep_import:
                        rep_import = '/tmp'
                    
                    fich_path = rep_import
                    fichier_import = param.nom_fichier_cde_edi_import
                    if not fichier_import:
                        fichier_import = 'ORDERS*'
                    
                    fich_edi = fich_path + '/%s' % fichier_import


                    with pysftp.Connection(host=sftp_url,username=sftp_user,password=sftp_password,port=int(sftp_port),cnopts=cnopts) as sftp:
                        # on ouvre le dossier images
                        sftp.chdir(rep_recup_sftp)
                        # liste des fichiers 
                        filenames = sftp.listdir()
                        for filename in filenames:
                            
                            fileobj = TemporaryFile('wb+')
                            fich_integ_edi = fich_path + '/%s' % filename
                            fichier_import = filename

                            #fich_copie = os.path.basename(fich_edi)  
                            #logger.info(fich_copie)

                            fichier_import = os.path.basename(fich_integ_edi) 

                            sftp.get(fichier_import,fich_integ_edi)

                            #encoding = self.file_encoding
                            #logger.info(encoding)
                            with open(fich_integ_edi, "rb") as f:
                                byte_data = f.read()

                            file_bytes = byte_data
                            fileobj.write(file_bytes)

                            fileobj.seek(0)  # We must start reading from the beginning !

                            lignes = self.file2import_edi(fileobj, file_bytes, fichier_import)
                            fileobj.close()
                            
                            if lignes:
                                moves = self.create_commande_edi_from_import_edi(lignes)
                            else:
                                moves = False   

                            logger.info("____________________________________")
                            logger.info("On met à jour la base de données EDI")
                            logger.info("____________________________________")
                            self.env.cr.commit()
                            #
                            # On supprime le fichier sur le serveur SFTP
                            #
                            sftp.remove(filename)

                            logger.info("______________________________________________")
                            logger.info("Suppression du fichier sur le serveur SFTP EDI")
                            logger.info(filename)
                            logger.info("______________________________________________")

                            if moves:
                                if company_id.gestion_archivage:
                                    self.copie_fichier_traite(True, fichier_import)
                                else:
                                    self.delete_fichier_traite(fichier_import)    
                            else:
                                if company_id.gestion_archivage:
                                    self.copie_fichier_traite(False, fichier_import)
                                else:
                                    self.delete_fichier_traite(fichier_import)       

        else:
            fileobj = TemporaryFile('wb+')

            file_bytes = base64.b64decode(self.file_to_import)
            fileobj.write(file_bytes)
            fileobj.seek(0)  # We must start reading from the beginning !
            lignes = self.file2import_edi(fileobj, file_bytes, self.filename)
            fileobj.close()
            if lignes:
                moves = self.create_commande_edi_from_import_edi(lignes)
            else:
                moves = False    
            if moves:
                if company_id.gestion_archivage:
                    self.copie_fichier_traite(True, self.filename)
                else:
                    self.delete_fichier_traite(self.filename)     
            else:
                if company_id.gestion_archivage:
                    self.copie_fichier_traite(False, self.filename)
                else:
                    self.delete_fichier_traite(self.filename)         
        
        sujet = str(self.env.company.name) + ' - Lancement Intégration Commandes EDI : ' + str(today)        
        code_erreur = self.env['erreur.edi'].search([('name','=', '9000')], limit=1) 
        flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1)        
        message = "Le traitement de l'intégration des commandes EDI est terminé sur la société {} . ".format(str(self.env.company.name) )  
        self.edi_generation_erreur(code_erreur, flux, sujet, message)   

        logger.info("**********************************************")
        logger.info("*      Fin de l'import des commandes EDI     *")
        logger.info(self.env.company.name)
        logger.info("**********************************************")

    #########################################################################################
    #                                                                                       #
    #      On lit le fichier et on génère une liste de données pour les commandes TX2       #
    #                                                                                       #
    #########################################################################################    
    def edi_import_tx2_import_orders(self, file_bytes, file_name):
        company_id =  self.env.company
        nb_lig = 0
        res = []
        res_ent = []
        res_par = []
        res_com = []
        res_lig = []
        creat_ligne_sans_erreur = False
        au_moins_une_ligne = False

        file_str = file_bytes.decode(self.file_encoding)

        today = fields.Date.to_string(datetime.now())

        self.type_fichier = file_name[0:6]

        if self.type_fichier not in ('ORDERS','ORDWEB'):
            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
            corps = "Le type de fichier est incorrect. Il doit être de type 'ORDERS' ou 'ORDWEB'. <br/><br>" 
            corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
            if not flux:
               flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
            if flux.envoi_auto_mail:   
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.edi_generation_mail(destinataire, sujet, corps)

            code_erreur = self.env['erreur.edi'].search([('name','=', '9003')], limit=1) 
            
            message = "Le type de fichier est incorrect. Il doit être de type 'ORDERS' ou 'ORDWEB'. "
            message+= "Le fichier {} a été rejeté. ".format(file_name)  
            self.edi_generation_erreur(code_erreur, flux, sujet, message)   
            return res    
        
        for l in file_str.split('\n'):
            nb_lig += 1
            if len(l) < 4 :
                continue
            if l[0] != '':
                creat_cde = False
                type_ligne  = l[0:3]

                if type_ligne not in ('ENT','COM','PAR','LIG'):
                    #
                    # Erreur sur type de ligne
                    #
                    sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                    corps = "Le type de ligne est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                    corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                    flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                    if not flux:
                        flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                    if flux.envoi_auto_mail:   
                        destinataire = company_id.gestion_user_id.email
                        if destinataire:
                            self.edi_generation_mail(destinataire, sujet, corps)
                            
                    code_erreur = self.env['erreur.edi'].search([('name','=', '9004')], limit=1) 

                    message = "Le type de ligne est incorrect à la ligne {}.".format(nb_lig) 
                    message+= "Le fichier {} a été rejeté. ".format(file_name) 
                    self.edi_generation_erreur(code_erreur, flux, sujet, message)
                    break 
                if type_ligne == 'ENT':
                    #
                    # Si on a déjà une entête, on intégre la commande dans les données à intégrer si on a au moins une ligne de commande
                    #   
                    if len(res_ent)>=1 and creat_ligne_sans_erreur and au_moins_une_ligne:
                       
                        for entete in res_ent:
                            res.append(entete)
                        for param in res_par:
                            res.append(param)
                        for comment in res_com:
                            res.append(comment)    
                        for ligne in res_lig:
                            res.append(ligne) 

                        au_moins_une_ligne = False    

                    #ICI On remet à zero les tables
                    # 
                    # On réinitialise les tables
                    #
                    res_ent = []        
                    res_par = [] 
                    res_com = [] 
                    res_lig = []

                    creat_ligne_sans_erreur = True 

                    # 
                    # Ligne entête
                    #
                    if len(l) < 404:
                        #
                        # Erreur sur longueur d'enregistrement
                        #
                        sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                        corps = "La longueur de l'enregistrement de l'entête est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                        corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
                        corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                        
                        flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                        if not flux:
                            flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                        if flux.envoi_auto_mail:   
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.edi_generation_mail(destinataire, sujet, corps)

                        code_erreur = self.env['erreur.edi'].search([('name','=', '9001')], limit=1) 

                        message = "La longueur de l'enregistrement de l'entête est incorrect à la ligne {}. ".format(nb_lig)
                        message+= "Le fichier {} a été rejeté. ".format(file_name)  
                        self.edi_generation_erreur(code_erreur, flux, sujet, message)
                        break
                    else:  
                        client_ok = True  
                        ccli_emet           = l[3:38]
                        ccli_dest           = l[38:73]
                        no_cde              = l[73:108]  #BGM
                        type_cde            = l[108:111]
                        code_function       = l[111:114]
                        date_cde            = l[114:122]
                        heure_cde           = l[122:126]
                        date_liv            = l[126:134]
                        heure_liv           = l[134:138]
                        date_enlev          = l[138:146]
                        heure_enlev         = l[146:150]
                        no_contrat          = l[150:185]
                        ref_cde_client      = l[185:220]
                        no_cde_rempl        = l[220:255]
                        no_ope_promo        = l[255:290]
                        devise              = l[290:293]
                        cond_liv            = l[293:296]
                        incoterms           = l[296:299]
                        ref1_div            = l[299:334]
                        ref2_div            = l[334:369]
                        ref_cde_client_final= l[369:404]
                        
                        no_cde = no_cde.strip()
                        ctrl_emet = self.controle_partenaire(ccli_emet.strip())
                        if ctrl_emet:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                            corps = "Le GLN du partenaire {} est inconnu à la ligne {}. <br/><br>".format(ccli_emet,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            
                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)

                            code_erreur = self.env['erreur.edi'].search([('name','=', '0001')], limit=1) 

                            message = "Le GLN du partenaire {} est inconnu à la ligne {}. ".format(ccli_emet,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            client_ok = False
                        
                        ctrl_dest = self.controle_partenaire(ccli_dest.strip())
                        if ctrl_dest:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                            corps = "Le GLN du partenaire {} est inconnu à la ligne {}. <br/><br>".format(ccli_dest,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)

                            code_erreur = self.env['erreur.edi'].search([('name','=', '0001')], limit=1) 

                            message = "Le GLN du partenaire {} est inconnu à la ligne {}. ".format(ccli_dest,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            client_ok = False
                        
                        if client_ok:
                            creat_cde = True
                        else:
                            creat_cde = False    

                        ctrl_type_cde = self.controle_type_commande(type_cde,'ORDERS')    
                        if ctrl_type_cde:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                            corps = "Le type de commande {} est inconnu à la ligne {}. <br/><br>".format(type_cde,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)

                            code_erreur = self.env['erreur.edi'].search([('name','=', '0005')], limit=1) 

                            message = "Le type de commande {} est inconnu à la ligne {}. ".format(type_cde,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            creat_cde = False
                        else:
                            creat_cde = True 

                        ctrl_code_function = self.controle_function_commande(code_function)    
                        if ctrl_code_function:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                            corps = "La fonction de la commande {} est inconnue à la ligne {}. <br/><br>".format(code_function,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)

                            code_erreur = self.env['erreur.edi'].search([('name','=', '0006')], limit=1) 

                            message = "La fonction de la commande {} est inconnue à la ligne {}. ".format(code_function,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            creat_cde = False
                        else:
                            creat_cde = True 

                        devise = devise.strip()
                        if not devise:
                            devise = 'EUR'
                        ctrl_devise = self.controle_devise(devise)    
                        if ctrl_devise:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                            corps = "La devise de la commande {} est inconnue à la ligne {}. <br/><br>".format(devise,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)

                            code_erreur = self.env['erreur.edi'].search([('name','=', '0007')], limit=1) 

                            message = "La devise de la commande {} est inconnue à la ligne {}. ".format(devise,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            creat_cde = False
                        else:
                            creat_cde = True  

                        incoterms = incoterms.strip()
                        if incoterms:
                            ctrl_incoterms = self.controle_incoterms(incoterms)    
                            if ctrl_incoterms:
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                                corps = "Le code incoterm de la commande {} est inconnu à la ligne {}. <br/><br>".format(incoterms,nb_lig) 
                                corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                if not flux:
                                    flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                if flux.envoi_auto_mail:   
                                    destinataire = company_id.gestion_user_id.email
                                    if destinataire:
                                        self.edi_generation_mail(destinataire, sujet, corps)

                                code_erreur = self.env['erreur.edi'].search([('name','=', '0008')], limit=1) 

                                message = "Le code incoterm de la commande {} est inconnu à la ligne {}. ".format(incoterms,nb_lig) 
                                message+= "La pièce {} a été rejetée. ".format(no_cde) 
                                self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                creat_cde = False
                            else:
                                creat_cde = True         

                        if creat_cde:
                            vals_ent = {
                                'type': type_ligne,
                                'no_client_emet': ccli_emet,
                                'no_client_dest': ccli_dest,
                                'no_cde': no_cde,
                                'type_cde': type_cde,
                                'code_function': code_function,
                                'date_cde': date_cde,                                                    
                                'heure_cde': heure_cde,
                                'date_liv': date_liv,                                                    
                                'heure_liv': heure_liv,
                                'date_enlev': date_enlev,                                                    
                                'heure_enlev': heure_enlev,
                                'no_contrat': no_contrat,
                                'ref_cde_client': ref_cde_client,
                                'no_cde_rempl': no_cde_rempl,
                                'no_ope_promo': no_ope_promo, 
                                'devise': devise,
                                'cond_liv' : cond_liv,
                                'incoterms': incoterms,
                                'ref1_div': ref1_div,
                                'ref2_div': ref2_div,
                                'line': nb_lig,
                                'ref_cde_client_final': ref_cde_client_final,
                            }               
                            res_ent.append(vals_ent)

                if type_ligne == 'PAR': #and creat_cde:
                    # 
                    # Ligne parametre
                    #                  
                    if not client_ok:
                        continue
                    if len(l) < 506:
                        #
                        # Erreur sur longueur d'enregistrement
                        #
                        sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                        corps = "La longueur de l'enregistrement paramêtre est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                        corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
                        corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                        flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                        if not flux:
                            flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                        if flux.envoi_auto_mail:   
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.edi_generation_mail(destinataire, sujet, corps)

                        code_erreur = self.env['erreur.edi'].search([('name','=', '9001')], limit=1) 

                        message = "La longueur de l'enregistrement paramêtre est incorrect à la ligne {}. ".format(nb_lig) 
                        message+= "Le fichier {} a été rejeté. ".format(file_name)  
                        self.edi_generation_erreur(code_erreur, flux, sujet, message)
                        client_ok = False
                        break
                    else:
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
                        type_interv         = l[3:6]
                        code_interv         = l[6:26]
                        ident_interv        = l[26:29]
                        nom_interv          = l[29:99]
                        adr1_interv         = l[99:134]
                        adr2_interv         = l[134:169]
                        adr3_interv         = l[169:204]
                        cpos_interv         = l[204:213]
                        vil_interv          = l[213:248]
                        pays_interv         = l[248:250]
                        ident_compl1        = l[250:285]
                        type_ident1         = l[285:288]
                        ident_compl2        = l[288:323]
                        type_ident2         = l[323:326]
                        ident_compl3        = l[326:361]
                        type_ident3         = l[361:364]
                        ident_compl4        = l[364:399]
                        type_ident4         = l[399:402]
                        nom_contact         = l[402:437]
                        tel_contact         = l[437:472]
                        mail_contact        = l[472:507]   

                        type_interv = type_interv.strip()
                        code_interv = code_interv.strip()
                        ident_interv = ident_interv.strip()     

                        ctrl_type_interv = self.controle_type_intervenant(type_interv)    
                        if ctrl_type_interv:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                            corps = "Le type d'intervenant qualifiant de la commande {} est inconnu à la ligne {}. <br/><br>".format(type_interv,nb_lig) 
                            corps+= "La pièce {} a été rejetée. ".format(no_cde) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)

                            code_erreur = self.env['erreur.edi'].search([('name','=', '0009')], limit=1) 

                            message = "Le type d'intervenant qualifiant de la commande {} est inconnu à la ligne {}. ".format(type_interv,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            client_ok = False
                            continue                         

                        # NAD+UC  -  NAD+DP  -  NAD+UD      
                        if type_interv == company_id.par_uc_id.name or type_interv == company_id.par_dp_id.name or type_interv == company_id.par_ud_id.name:
                            if not code_interv:
                                # 
                                # On doit créer une adresse (autres adresses) liés avec le PAR+BY
                                # 
                                ctrl_code_interv = False
                            else:
                                ctrl_code_interv = self.controle_partenaire(code_interv) 
                        else:                
                            ctrl_code_interv = self.controle_partenaire(code_interv)    

                        if ctrl_code_interv:
                            segment_par = 'PAR+'+type_interv
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                            corps = "Le code identifiant {} de l'intervenant de la commande {} est inconnu à la ligne {}. <br/><br>".format(segment_par,code_interv,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)

                            code_erreur = self.env['erreur.edi'].search([('name','=', '0001')], limit=1) 

                            message = "Le code identifiant {} de l'intervenant de la commande {} est inconnu à la ligne {}.".format(segment_par,code_interv,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            client_ok = False
                            continue                         
                        
                        vals_par = {
                            'type': type_ligne,
                            'type_interv': type_interv,
                            'code_interv': code_interv,
                            'ident_interv': ident_interv,
                            'nom_interv': nom_interv,
                            'adr1_interv': adr1_interv,
                            'adr2_interv': adr2_interv,                                                    
                            'adr3_interv': adr3_interv,
                            'cpos_interv': cpos_interv,                                                    
                            'vil_interv': vil_interv,
                            'pays_interv': pays_interv,                                                    
                            'ident_compl1': ident_compl1,
                            'type_ident1': type_ident1,
                            'ident_compl2': ident_compl2,
                            'type_ident2': type_ident2,
                            'ident_compl3': ident_compl3,
                            'type_ident3': type_ident3,
                            'ident_compl4': ident_compl4,
                            'type_ident4': type_ident4,
                            'nom_contact': nom_contact,
                            'tel_contact': tel_contact,
                            'mail_contact': mail_contact,                             
                            'line': nb_lig,
                            'no_cde': no_cde,
                        }               
                        res_par.append(vals_par) 

                if type_ligne == 'COM':
                    # 
                    # Ligne commentaire
                    #
                    if not client_ok:
                        continue
                    if len(l) < 356:
                        #
                        # Erreur sur longueur d'enregistrement
                        #
                        sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                        corps = "La longueur de l'enregistrement commentaire est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                        corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
                        corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                        flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                        if not flux:
                            flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                        if flux.envoi_auto_mail:   
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.edi_generation_mail(destinataire, sujet, corps)

                        code_erreur = self.env['erreur.edi'].search([('name','=', '9001')], limit=1) 

                        message = "La longueur de l'enregistrement commentaire est incorrect à la ligne {}.".format(nb_lig) 
                        message+= "Le fichier {} a été rejeté. ".format(file_name) 
                        self.edi_generation_erreur(code_erreur, flux, sujet, message)
                        break
                    else:
                        type_comm           = l[3:6]
                        comm1               = l[6:76]
                        comm2               = l[76:146]
                        comm3               = l[146:216]
                        comm4               = l[216:286]
                        comm5               = l[286:356]                                           
                        comm1 = comm1.strip()
                        comm2 = comm2.strip()
                        comm3 = comm3.strip()
                        comm4 = comm4.strip()
                        comm5 = comm5.strip()
                        vals_com = {
                            'type': type_ligne,
                            'type_comm': type_comm,
                            'comm1': comm1,
                            'comm2': comm2,
                            'comm3': comm3,
                            'comm4': comm4,
                            'comm5': comm5,                                                    
                            'line': nb_lig,
                        }               
                        res_com.append(vals_com) 

                if type_ligne == 'LIG':
                    # 
                    # Ligne Articles
                    #
                    if not client_ok:
                        continue

                    if len(l) < 912:
                        #
                        # Erreur sur longueur d'enregistrement
                        #
                        sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                        corps = "La longueur de l'enregistrement de la ligne est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                        corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)

                        sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                        corps = "La longueur de l'enregistrement commentaire est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                        corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
                        corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                        flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                        if not flux:
                            flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                        if flux.envoi_auto_mail:   
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.edi_generation_mail(destinataire, sujet, corps)

                        code_erreur = self.env['erreur.edi'].search([('name','=', '9001')], limit=1) 

                        message = "La longueur de l'enregistrement de la ligne est incorrect à la ligne {}.".format(nb_lig) 
                        message+= "Le fichier {} a été rejeté. ".format(file_name)
                        self.edi_generation_erreur(code_erreur, flux, sujet, message)
                        break
                    else:
                        creat_lig = True
                        no_ligne            = l[3:9]
                        ean                 = l[9:44]
                        code_art_vendeur    = l[44:79]
                        code_art_acheteur   = l[79:114]
                        qte_cde             = l[114:129]
                        unite_cde           = l[129:132]
                        qte_pcb             = l[132:147]
                        unite_pcb           = l[147:150]
                        qte_gratuit         = l[150:165]
                        unite_gratuit       = l[165:168]
                        desc_art            = l[168:308]
                        pub                 = l[308:317]
                        pun                 = l[317:326]
                        pvc                 = l[326:335]
                        mt_net_ligne        = l[335:353]
                        nb_ul               = l[353:360]
                        type_emballage      = l[360:368]
                        ean_ul              = l[368:382]
                        date_liv            = l[382:390]
                        heure_liv           = l[390:394]
                        no_cde_magasin      = l[394:429]
                        gln_magasin         = l[429:442]
                        comment             = l[442:792]
                        ref_cde_cli_final   = l[792:827]
                        no_cde_remplace     = l[827:862]
                        no_ope_promo        = l[862:897]
                        no_lig_erp_cli      = l[897:903]
                        pourc_remise        = l[903:913]

                        ctrl_ean_article = self.controle_ean_article(ean.strip())    
                        if ctrl_ean_article:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                            corps = "L'article de la commande {} est inconnu à la ligne {}. <br/><br>".format(ean,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)

                            code_erreur = self.env['erreur.edi'].search([('name','=', '0010')], limit=1) 

                            message = "L'article de la commande {} est inconnu à la ligne {}.".format(ean,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde)   
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            creat_lig = False
                            creat_ligne_sans_erreur = False
                            continue                        

                        unite_cde = unite_cde.strip()
                        if unite_cde:
                            ctrl_unite_cde = self.controle_unite(unite_cde)    
                            if ctrl_unite_cde:
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                                corps = "L'unité de la quantité commandée de la commande {} est inconnu à la ligne {}. <br/><br>".format(unite_cde,nb_lig) 
                                corps+= "La pièce {} a été rejetée . <br/><br>".format(no_cde)                         
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                if not flux:
                                    flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                if flux.envoi_auto_mail:   
                                    destinataire = company_id.gestion_user_id.email
                                    if destinataire:
                                        self.edi_generation_mail(destinataire, sujet, corps)

                                code_erreur = self.env['erreur.edi'].search([('name','=', '0011')], limit=1) 

                                message = "L'unité de la quantité commandée de la commande {} est inconnu à la ligne {}.".format(unite_cde,nb_lig)
                                message+= "La pièce {} a été rejetée . ".format(no_cde)  
                                self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                creat_lig = False
                                creat_ligne_sans_erreur = False
                                continue                           

                        unite_pcb = unite_pcb.strip()
                        if unite_pcb:
                            ctrl_unite_pcb = self.controle_unite(unite_pcb)    
                            if ctrl_unite_pcb:
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                                corps = "L'unité de pcb de l'article de la commande {} est inconnu à la ligne {}. <br/><br>".format(unite_pcb,nb_lig) 
                                corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                if not flux:
                                    flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                if flux.envoi_auto_mail:   
                                    destinataire = company_id.gestion_user_id.email
                                    if destinataire:
                                        self.edi_generation_mail(destinataire, sujet, corps)

                                code_erreur = self.env['erreur.edi'].search([('name','=', '0011')], limit=1) 

                                message = "L'unité de pcb de l'article de la commande {} est inconnu à la ligne {}.".format(unite_pcb,nb_lig) 
                                message+= "La pièce {} a été rejetée. ".format(no_cde)  
                                self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                creat_lig = False
                                creat_ligne_sans_erreur = False
                                continue  

                        unite_gratuit = unite_gratuit.strip()
                        if unite_gratuit:
                            ctrl_unite_gratuit = self.controle_unite(unite_gratuit)    
                            if ctrl_unite_gratuit:
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                                corps = "L'unité de la quantité gratuite de la commande {} est inconnu à la ligne {}. <br/><br>".format(unite_gratuit,nb_lig) 
                                corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                if not flux:
                                    flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                if flux.envoi_auto_mail:   
                                    destinataire = company_id.gestion_user_id.email
                                    if destinataire:
                                        self.edi_generation_mail(destinataire, sujet, corps)

                                code_erreur = self.env['erreur.edi'].search([('name','=', '0011')], limit=1) 

                                messacommentge = "L'unité de la quantité gratuite de la commande {} est inconnu à la ligne {}.".format(unite_gratuit,nb_lig)
                                message+= "La pièce {} a été rejetée. ".format(no_cde)  
                                self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                creat_lig = False
                                creat_ligne_sans_erreur = False
                                continue

                        gln_magasin = gln_magasin.strip()                        
                        if gln_magasin:
                            ctrl_gln_magasin = self.controle_partenaire(gln_magasin)    
                            if ctrl_gln_magasin:
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                                corps = "Le GLN magasin {} de la commande {} est inconnu à la ligne {}. <br/><br>".format(gln_magasin,no_cde,nb_lig) 
                                corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                       
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                if not flux:
                                    flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                if flux.envoi_auto_mail:   
                                    destinataire = company_id.gestion_user_id.email
                                    if destinataire:
                                        self.edi_generation_mail(destinataire, sujet, corps)

                                code_erreur = self.env['erreur.edi'].search([('name','=', '0001')], limit=1) 

                                message = "Le GLN magasin {} de la commande {} est inconnu à la ligne {}.".format(gln_magasin,no_cde,nb_lig)
                                message+= "La pièce {} a été rejetée. ".format(no_cde)  
                                self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                creat_lig = False
                                creat_ligne_sans_erreur = False  
                                continue                                

                        if creat_lig:
                            no_cde_magasin = no_cde_magasin.strip()
                            vals_lig = {
                                'type': type_ligne,
                                'no_ligne': no_ligne,
                                'ean': ean,
                                'code_art_vendeur': code_art_vendeur.strip(),
                                'code_art_acheteur': code_art_acheteur.strip(),
                                'qte_cde': qte_cde,
                                'unite_cde': unite_cde,   
                                'qte_pcb': qte_pcb,
                                'unite_pcb': unite_pcb,                                                  
                                'qte_gratuit': qte_gratuit,
                                'unite_gratuit': unite_gratuit,
                                'desc_art': desc_art,
                                'pub': pub,
                                'pun': pun,
                                'pvc': pvc,
                                'mt_net_ligne': mt_net_ligne,
                                'nb_ul': nb_ul,
                                'type_emballage': type_emballage,
                                'ean_ul': ean_ul,
                                'date_liv': date_liv,                                                    
                                'heure_liv': heure_liv,
                                'no_cde_magasin': no_cde_magasin,                                                    
                                'gln_magasin': gln_magasin,
                                'comment': comment.strip(),
                                'ref_cde_cli_final': ref_cde_cli_final,
                                'no_cde_remplace': no_cde_remplace,
                                'no_ope_promo': no_ope_promo, 
                                'no_lig_erp_cli': no_lig_erp_cli,
                                'pourc_remise' : pourc_remise,
                                'line': nb_lig,
                            }  
                            au_moins_une_ligne = True             
                            res_lig.append(vals_lig)  

        #
        # on doit intégrer la dernière commande si on en a une
        #  
        if len(res_ent)>=1 and creat_ligne_sans_erreur and au_moins_une_ligne:
            for entete in res_ent:
                res.append(entete)
            for param in res_par:
                res.append(param)
            for comment in res_com:
                res.append(comment)    
            for ligne in res_lig:
                res.append(ligne)     
            res_ent = []        
            res_par = [] 
            res_com = [] 
            res_lig = []

        #logger.info("=== res après lecture du fichier =============================================================")
        #logger.info(res)  
        #logger.info("==============================================================================================")                       
                
        return res
    
    #########################################################################################
    #                                                                                       #
    #      On lit le fichier et on génère une liste de données pour les commandes @Gp       #
    #                                                                                       #
    #########################################################################################    
    def edi_import_agp_import_edi(self, file_bytes, file_name):
        i = 0
        res = []
        file_str = file_bytes.decode(self.file_encoding)
        
        #for l in file_str.split('\n'):
        #    i += 1
        #    if len(l) < 10:
        #        continue            
                
        return res

    #########################################################################################
    #                                                                                       #
    #        A partir de la liste de données, on créé la ou les commandes client            #
    #                                                                                       #
    #########################################################################################
    def create_commande_edi_from_import_edi(self, lignes_import):
        company_id =  self.env.company 
        sale_obj = self.env['sale.order']        

        sale = False
        new_piece = False
        values_entete = []
        values_param = []
        values_comment = []
        values_lignes = []
        premier_passage = True
        piece_a_creer = False
        
        for lignes in lignes_import:
            type_ligne = lignes['type']
            if type_ligne == 'ENT':
                #
                # Entête de commande
                #
                if not new_piece:
                    values_param = []
                    values_comment = []
                    values_lignes = []                   
                    new_piece = True
                    if premier_passage:
                        piece_a_creer = lignes['no_cde']
                        premier_passage = False

                no_cde = lignes['no_cde']
                if new_piece and no_cde != piece_a_creer:
                    #
                    # On génére la commande avec les données connues
                    # 
                    sale = self.genere_commande_vente(values_entete,values_param,values_comment,values_lignes)
                    
                    values_entete = []
                    values_param = []
                    values_comment = []
                    values_lignes = []
                    piece_a_creer = lignes['no_cde']
                    new_piece = True                        

                ccli_emet = lignes['no_client_emet']
                ccli_dest = lignes['no_client_dest']
                no_cde = lignes['no_cde']
                type_cde = lignes['type_cde']
                code_function = lignes['code_function']
                date_cde = lignes['date_cde']                                                    
                heure_cde = lignes['heure_cde']
                date_liv = lignes['date_liv']                                                   
                heure_liv = lignes['heure_liv']
                date_enlev = lignes['date_enlev']                                                   
                heure_enlev = lignes['heure_enlev']
                no_contrat = lignes['no_contrat']
                ref_cde_client = lignes['ref_cde_client']
                no_cde_rempl = lignes['no_cde_rempl']
                no_ope_promo = lignes['no_ope_promo']
                devise = lignes['devise']
                cond_liv = lignes['cond_liv']
                incoterms = lignes['incoterms']
                ref1_div = lignes['ref1_div']
                ref2_div = lignes['ref2_div']
                nb_lig = lignes['line']
                edi_emet = lignes['no_client_emet']
                edi_dest = lignes['no_client_dest']
                ref_cde_client_final = lignes['ref_cde_client_final']

                ccli_dest = ccli_dest.strip()
                partner_id = self.recherche_partenaire(ccli_dest)
                ccli_emet = ccli_emet.strip()
                partner_emet_id = self.recherche_partenaire(ccli_emet)
                devise = devise.strip()
                devise_id = self.recherche_devise(devise)
                incoterms = incoterms.strip()
                incoterm_id = self.recherche_incoterms(incoterms)
                type_cde = type_cde.strip()
                type_cde_id = self.recherche_type_commande(type_cde)
                code_function = code_function.strip()
                code_function_id = self.recherche_function_commande(code_function)

                #date_moment = fields.Date.to_string(datetime.now())
                date_order = self.conversion_en_datetime(date_cde,heure_cde)
                if date_liv:
                    date_livraison = self.conversion_en_datetime(date_liv,heure_liv)
                else:
                    date_livraison = date_order    
                date_expected = self.conversion_en_datetime(date_liv,heure_liv)
                if date_enlev.strip():
                    date_enlevement = self.conversion_en_datetime(date_enlev,heure_enlev)
                else:
                    date_enlevement = False    

                if len(company_id.param_edi_id.name)>3:
                    type_param_edi = company_id.param_edi_id.name[:3]
                else:   
                    type_param_edi = company_id.param_edi_id.name

                if type_param_edi == "TX2":
                    ref_cde_client = ref_cde_client.strip()
                    ref_cde_client_final = ref_cde_client_final.strip()
                    no_contrat = no_contrat.strip()
                    ref1_div = ref1_div.strip()
                    ref2_div = ref2_div.strip() 
                    cond_liv = cond_liv.strip()

                    if type_cde == '220' and code_function == '9':
                        #
                        # On créé la commande
                        #                                                
                        values_ent = {
                            'partner_id': partner_id,
                            'commande_edi': True,
                            'partner_emet_id': partner_emet_id,
                            'date_order': date_order,
                            'date_devis_edi': date_order,
                            'date_livraison_demandee': date_livraison,
                            'expected_date': date_expected,
                            'date_enlev': date_enlevement,
                            'client_order_ref': no_cde.strip(),
                            'no_cde_client': no_cde.strip(),
                            'no_contrat': no_contrat,
                            'no_cde_rempl': no_cde_rempl,
                            'no_ope_promo': no_ope_promo,
                            'cond_liv': cond_liv,
                            'ref1_div': ref1_div,
                            'ref2_div': ref2_div,
                            'type_cde_id': type_cde_id.id,
                            'code_function_id': code_function_id.id,
                            'currency_id': devise_id,
                            'incoterm': incoterm_id,                            
                            'partner_shipping_id': False,
                            'partner_invoice_id': False,
                            'partner_vendeur_id': partner_emet_id,
                            'partner_final_id': partner_emet_id,
                            'partner_acheteur_id': False,
                            'partner_commande_par_id': False,
                            'partner_paye_par_id': False,
                            'partner_livre_a_id': False,
                            'partner_facture_a_id': False,
                            'partner_final_ud_id': False,
                            'edi_emetteur': edi_emet,
                            'edi_destinataire': edi_dest,
                            'ref_cde_client_edi': ref_cde_client,
                            'ref_cde_client_final_edi': ref_cde_client_final,
                        }
                        values_entete.append(values_ent) 
                else: 
                    #
                    # On créé la commande
                    #
                    values_ent = {
                        'partner_id': partner_emet_id,
                        'commande_edi': True,
                        'partner_emet_id': partner_emet_id,
                        'date_order': date_order,
                        'date_devis_edi': date_order,
                        'date_livraison_demandee': date_livraison,
                        'expected_date': date_expected,
                        'date_enlev': date_enlevement,
                        'client_order_ref': no_cde.strip(),
                        'no_cde_client': no_cde.strip(),                        
                        'no_contrat': no_contrat,
                        'no_cde_rempl': no_cde_rempl,
                        'no_ope_promo': no_ope_promo,
                        'cond_liv': cond_liv,
                        'ref1_div': ref1_div,
                        'ref2_div': ref2_div,
                        'type_cde_id': type_cde_id.id,
                        'code_function_id': code_function_id.id,
                        'currency_id': devise_id,
                        'incoterm': incoterm_id,
                        'partner_shipping_id': False,
                        'partner_invoice_id': False,
                        'partner_vendeur_id': partner_emet_id,
                        'partner_final_id': partner_emet_id,
                        'partner_acheteur_id': False,
                        'partner_commande_par_id': False,
                        'partner_paye_par_id': False,
                        'partner_livre_a_id': False,
                        'partner_facture_a_id': False,
                        'partner_final_ud_id': False,
                        'edi_emetteur': edi_emet,
                        'edi_destinataire': edi_dest,
                        'ref_cde_client_edi': ref_cde_client,
                        'ref_cde_client_final_edi': ref_cde_client_final,
                    }
                    values_entete.append(values_ent)       


            if type_ligne == 'PAR':
                #
                # Paramêtre de commande
                #
                type_interv = lignes['type_interv']
                code_interv = lignes['code_interv']
                ident_interv = lignes['ident_interv']
                nom_interv = lignes['nom_interv']
                adr1_interv = lignes['adr1_interv']
                adr2_interv = lignes['adr2_interv']
                adr3_interv = lignes['adr3_interv']
                cpos_interv = lignes['cpos_interv']
                vil_interv = lignes['vil_interv']
                pays_interv = lignes['pays_interv']
                ident_compl1 = lignes['ident_compl1']
                type_ident1 = lignes['type_ident1']
                ident_compl2 = lignes['ident_compl2']
                type_ident2 = lignes['type_ident2']
                ident_compl3 = lignes['ident_compl3']
                type_ident3 = lignes['type_ident3']
                ident_compl4 = lignes['ident_compl4']
                type_ident4 = lignes['type_ident4']
                nom_contact = lignes['nom_contact']
                tel_contact = lignes['tel_contact']
                mail_contact = lignes['mail_contact']
                nb_lig_par = lignes['line']
                no_cde_par = lignes['no_cde']

                type_interv = type_interv.strip()
                type_interv_id = self.recherche_type_intervenant(type_interv)
                code_interv = code_interv.strip()
                code_interv_id = self.recherche_partenaire(code_interv)  
                ident_interv = ident_interv.strip() 
                ident_interv_id = self.recherche_partenaire(ident_interv)   

                values_par = {
                    'type_interv_id': type_interv_id,
                    'code_interv_id': code_interv_id,
                    'ident_interv_id': ident_interv_id,
                    'nom_interv': nom_interv,
                    'adr1_interv': adr1_interv,
                    'adr2_interv': adr2_interv,
                    'adr3_interv': adr3_interv,
                    'cpos_interv': cpos_interv,
                    'vil_interv': vil_interv,
                    'pays_interv': pays_interv,
                    'ident_compl1': ident_compl1,
                    'type_ident1': type_ident1,
                    'ident_compl2': ident_compl2,
                    'type_ident2': type_ident2,
                    'ident_compl3': ident_compl3,
                    'type_ident3': type_ident3,
                    'ident_compl4': ident_compl4,
                    'type_ident4': type_ident4,
                    'nom_contact': nom_contact,
                    'tel_contact': tel_contact,
                    'mail_contact': mail_contact,
                    'nad_by_id': partner_emet_id,
                    'no_lig': nb_lig_par,
                    'no_cde': no_cde_par,
                    }   
                values_param.append(values_par)    

            if type_ligne == 'COM':
                #
                # Commentaire de commande
                #
                type_comm = lignes['type_comm']
                comm1 = lignes['comm1']
                comm2 = lignes['comm2']
                comm3 = lignes['comm3']
                comm4 = lignes['comm4']
                comm5 = lignes['comm5']                
                commentaire = comm1 
                if comm2:
                    commentaire += '/n' + comm2 
                if comm3:    
                    commentaire += '/n' + comm3 
                if comm4:    
                    commentaire += '/n' + comm4 
                if comm5:    
                    commentaire += '/n' + comm5     
                values_com = {
                    'type_comm': type_comm,
                    'comment': commentaire,
                    }   
                values_comment.append(values_com)    

            if type_ligne == 'LIG':
                #
                # Ligne de commande
                #  
                no_ligne = lignes['no_ligne']
                ean = lignes['ean']
                code_art_vendeur = lignes['code_art_vendeur']
                code_art_acheteur = lignes['code_art_acheteur']
                qte_cde = self.conversion_en_flaot(lignes['qte_cde'])   
                unite_cde = lignes['unite_cde']
                qte_pcb = self.conversion_en_flaot(lignes['qte_pcb'])
                unite_pcb = lignes['unite_pcb']
                qte_gratuit = self.conversion_en_flaot(lignes['qte_gratuit'])
                unite_gratuit = lignes['unite_gratuit']
                desc_art = lignes['desc_art']
                pub = self.conversion_en_flaot(lignes['pub'])              
                pun = self.conversion_en_flaot(lignes['pun'])
                pvc = self.conversion_en_flaot(lignes['pvc'])
                mt_net_ligne = self.conversion_en_flaot(lignes['mt_net_ligne'])
                nb_ul = self.conversion_en_flaot(lignes['nb_ul'])
                type_emballage = lignes['type_emballage']
                ean_ul = lignes['ean_ul']
                date_liv = lignes['date_liv']
                heure_liv = lignes['heure_liv']
                no_cde_magasin = lignes['no_cde_magasin']
                gln_magasin = lignes['gln_magasin']
                comment = lignes['comment']
                ref_cde_cli_final = lignes['ref_cde_cli_final']
                no_cde_remplace = lignes['no_cde_remplace']
                no_ope_promo = lignes['no_ope_promo']
                no_lig_erp_cli = lignes['no_lig_erp_cli']
                pourc_remise = self.conversion_en_flaot(lignes['pourc_remise'])                
                
                ean = ean.strip() 
                ean_id = self.recherche_ean_article(ean)
                unite_cde = unite_cde.strip() 
                unite_cde_id = self.recherche_unite(unite_cde,ean_id)
                unite_pcb = unite_pcb.strip() 
                unite_pcb_id = self.recherche_unite(unite_pcb,ean_id)
                unite_gratuit = unite_gratuit.strip() 
                unite_gratuit_id = self.recherche_unite(unite_gratuit,ean_id)
                ean_ul = ean_ul.strip() 
                ean_ul_id = self.recherche_ean_article(ean_ul)
                gln_magasin = gln_magasin.strip() 
                gln_magasin_id = self.recherche_partenaire(gln_magasin)

                if date_liv.strip():
                    date_liv_edi = self.conversion_en_datetime(date_liv,heure_liv)
                else:
                    date_liv_edi = False    
                desc_art = desc_art.strip()
                if desc_art:                        
                    values_lig = {
                        'product_id': ean_id,
                        'lig_commande_edi': True,
                        'code_art_vendeur': code_art_vendeur,
                        'code_art_acheteur': code_art_acheteur,
                        'product_uom_qty' : qte_cde, 
                        'product_uom': unite_cde_id, 
                        'qte_pcb': qte_pcb,
                        'unite_pcb': unite_pcb_id,
                        'qte_gratuit': qte_gratuit,
                        'unite_gratuit': unite_gratuit_id,
                        'name': desc_art,
                        'pub_edi': pub,
                        'pun_edi': pun,
                        'pvc_edi': pvc,
                        'mt_net_ligne_edi': mt_net_ligne,
                        'nb_ul_edi': nb_ul,
                        'type_emballage': type_emballage,
                        'ean_ul_edi': ean_ul_id,
                        'date_liv_edi': date_liv_edi,
                        'no_cde_magasin': no_cde_magasin,
                        'gln_magasin': gln_magasin_id,
                        'comment_edi': comment,
                        'ref_cde_cli_final': ref_cde_cli_final,
                        'no_cde_remplace': no_cde_remplace,
                        'no_ope_promo': no_ope_promo,
                        'no_lig_erp_cli': no_lig_erp_cli,
                        'pourc_remise_edi': pourc_remise, 
                        'no_ligne_edi': no_ligne,            
                    }
                else:
                    values_lig = {
                        'product_id': ean_id,
                        'lig_commande_edi': True,
                        'code_art_vendeur': code_art_vendeur,
                        'code_art_acheteur': code_art_acheteur,
                        'product_uom_qty' : qte_cde, 
                        'product_uom': unite_cde_id, 
                        'qte_pcb': qte_pcb,
                        'unite_pcb': unite_pcb_id,
                        'qte_gratuit': qte_gratuit,
                        'unite_gratuit': unite_gratuit_id,
                        'pub_edi': pub,
                        'pun_edi': pun,
                        'pvc_edi': pvc,
                        'mt_net_ligne_edi': mt_net_ligne,
                        'nb_ul_edi': nb_ul,
                        'type_emballage': type_emballage,
                        'ean_ul_edi': ean_ul_id,
                        'date_liv_edi': date_liv_edi,
                        'no_cde_magasin': no_cde_magasin,
                        'gln_magasin': gln_magasin_id,
                        'comment_edi': comment,
                        'ref_cde_cli_final': ref_cde_cli_final,
                        'no_cde_remplace': no_cde_remplace,
                        'no_ope_promo': no_ope_promo,
                        'no_lig_erp_cli': no_lig_erp_cli,
                        'pourc_remise_edi': pourc_remise, 
                        'no_ligne_edi': no_ligne,             
                    }

                values_lignes.append(values_lig)

        if new_piece:            
            #
            # On génére la commande avec les données connues
            # 
            sale = self.genere_commande_vente(values_entete,values_param,values_comment,values_lignes)
                    
        return sale

    #########################################################################################
    #                                                                                       #
    #                                   Conversion en Float                                 #
    #                                                                                       #
    #########################################################################################
    def conversion_en_flaot(self, chaine_a_convertir):
        nombre_str = chaine_a_convertir.strip()
        if nombre_str:
            nombre = float(nombre_str)
        else:
            nombre = 0  
        return nombre    

    #########################################################################################
    #                                                                                       #
    #                                   Conversion en DateTime                              #
    #                                                                                       #
    #########################################################################################
    def conversion_en_datetime(self, chaine_date, chaine_heure):
        date_str = chaine_date.strip()
        heure_str = chaine_heure.strip()
        if date_str:
            if heure_str:
                date = date_str[0:4] +'-'+ date_str[4:6] +'-'+ date_str[6:8] +' '+ heure_str[0:2] +':'+ heure_str[2:4] +':00'  
            else:
                date = date_str[0:4] +'-'+ date_str[4:6] +'-'+ date_str[6:8]   
        else:
            date = datetime.now()  
        return date    

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

    #########################################################################################
    #                                                                                       #
    #                                     Controle Partenaire EDI                           #
    #                                                                                       #
    #########################################################################################
    def controle_partenaire(self, ccli):
        erreur = True
        partner_obj = self.env['res.partner']
        partner = partner_obj.search([('code_gln','=', ccli)],limit=1)
        if partner:
            erreur = False
            return erreur
        else:
            partner = partner_obj.search([('name','=', ccli)],limit=1)
            if partner:
                erreur = False
                return erreur
        return erreur        

    #########################################################################################
    #                                                                                       #
    #                                  Controle type de cde EDI                             #
    #                                                                                       #
    #########################################################################################
    def controle_type_commande(self, type, flux):
        erreur = True
        #flux = 'ORDERS'
        type_obj = self.env['type.flux']
        type_vte = type_obj.search([('name','=', type),('code_gencod_id','=',flux)],limit=1)
        if type_vte:
            erreur = False
        return erreur 

    #########################################################################################
    #                                                                                       #
    #                              Controle function de cde EDI                             #
    #                                                                                       #
    #########################################################################################
    def controle_function_commande(self, function):
        erreur = True
        flux = 'ORDERS'
        funct = function.strip()
        function_obj = self.env['function.flux']
        function_vte = function_obj.search([('name','=', funct),('code_gencod_id','=',flux)],limit=1)
        if function_vte:
            erreur = False
        return erreur 

    #########################################################################################
    #                                                                                       #
    #                                     Controle devise                                   #
    #                                                                                       #
    #########################################################################################
    def controle_devise(self, devise):
        erreur = True
        devise_obj = self.env['res.currency']
        devise_vte = devise_obj.search([('name','=', devise)],limit=1)
        if devise_vte:
            erreur = False
        return erreur 

    #########################################################################################
    #                                                                                       #
    #                                     Controle incoterm                                 #
    #                                                                                       #
    #########################################################################################
    def controle_incoterms(self, incoterm):
        erreur = True
        code_obj = self.env['account.incoterms']
        code_vte = code_obj.search([('code','=', incoterm)],limit=1)
        if code_vte:
            erreur = False
        return erreur 

    #########################################################################################
    #                                                                                       #
    #                                     Controle type intervenant                         #
    #                                                                                       #
    #########################################################################################
    def controle_type_intervenant(self, interv):
        erreur = True
        interv_obj = self.env['type.intervenant']
        interv_vte = interv_obj.search([('name','=', interv)],limit=1)
        if interv_vte:
            erreur = False
        return erreur 

    #########################################################################################
    #                                                                                       #
    #                                     Controle ean                                      #
    #                                                                                       #
    #########################################################################################
    def controle_ean_article(self, ean):
        erreur = True

        template_obj = self.env['product.template']
        product_obj = self.env['product.product']
        product_vte = product_obj.search([('barcode','=', ean)],limit=1)
        if product_vte:
            erreur = False
        else:
            templ_vte = template_obj.search([('barcode','=', ean)],limit=1)
            if templ_vte:
                erreur = False

        return erreur 

    #########################################################################################
    #                                                                                       #
    #                                   Controle unité                                      #
    #                                                                                       #
    #########################################################################################
    def controle_unite(self, unite):
        erreur = True
        unite_obj = self.env['uom.uom']
        unite_vte = unite_obj.search([('unite_edi','=', unite)],limit=1)
        if unite_vte:
            erreur = False        
        return erreur    

    #########################################################################################
    #                                                                                       #
    #                                Recherche Partenaire EDI                               #
    #                                                                                       #
    #########################################################################################
    def recherche_partenaire(self, ccli):
        partenaire = False
        partner_obj = self.env['res.partner']
        partner = partner_obj.search([('code_gln','=', ccli)],limit=1)
        if partner:
            partenaire = partner.id
            return partenaire
        else:
            partner = partner_obj.search([('name','=', ccli)],limit=1)
            if partner:
                partenaire = partner.id
                return partenaire
                  
        return partenaire      

    #########################################################################################
    #                                                                                       #
    #                                   Recherche Partner                                   #
    #                                                                                       #
    #########################################################################################
    def recherche_partner(self, ccli):
        partenaire = False
        partner_obj = self.env['res.partner']
        partner = partner_obj.search([('id','=', ccli)],limit=1)
        if partner:
            partenaire = partner.id
            return partenaire
        else:
            partner = partner_obj.search([('name','=', ccli)],limit=1)
            if partner:
                partenaire = partner.id
            return partenaire
        return partenaire      

    #########################################################################################
    #                                                                                       #
    #                                    Recherche devise                                   #
    #                                                                                       #
    #########################################################################################
    def recherche_devise(self, devise):
        company_id =  self.env.company 
        devise_id = company_id.currency_id.id
        devise_obj = self.env['res.currency']
        devise_vte = devise_obj.search([('name','=', devise)],limit=1)
        if devise_vte:
            devise_id = devise_vte.id
        return devise_id 
    
    #########################################################################################
    #                                                                                       #
    #                                     Recherche incoterm                                #
    #                                                                                       #
    #########################################################################################
    def recherche_incoterms(self, incoterm):
        incoterm_id = False
        code_obj = self.env['account.incoterms']
        code_vte = code_obj.search([('code','=', incoterm)],limit=1)
        if code_vte:
            incoterm_id = code_vte.id
        return incoterm_id         

    #########################################################################################
    #                                                                                       #
    #                                 Recherche type de cde EDI                             #
    #                                                                                       #
    #########################################################################################
    def recherche_type_commande(self, type):
        type_cde = False
        flux = 'ORDERS'
        type_obj = self.env['type.flux']
        type_vte = type_obj.search([('name','=', type),('code_gencod_id','=',flux)],limit=1)
        if type_vte:
            type_cde = type_vte
        return type_cde 

    #########################################################################################
    #                                                                                       #
    #                              Controle function de cde EDI                             #
    #                                                                                       #
    #########################################################################################
    def recherche_function_commande(self, function):
        function_cde = False
        flux = 'ORDERS'
        funct = function.strip()
        function_obj = self.env['function.flux']
        function_vte = function_obj.search([('name','=', funct),('code_gencod_id','=',flux)],limit=1)
        if function_vte:
            function_cde = function_vte
        return function_cde 

    #########################################################################################
    #                                                                                       #
    #                             Recherche type intervenant                                #
    #                                                                                       #
    #########################################################################################
    def recherche_type_intervenant(self, interv):
        type_interv = False
        interv_obj = self.env['type.intervenant']
        interv_vte = interv_obj.search([('name','=', interv)],limit=1)
        if interv_vte:
            type_interv = interv_vte
        return type_interv     

    #########################################################################################
    #                                                                                       #
    #                                    Recherche ean                                      #
    #                                                                                       #
    #########################################################################################
    def recherche_ean_article(self, ean):
        ean_id = False
        template_obj = self.env['product.template']
        product_obj = self.env['product.product']
        product_vte = product_obj.search([('barcode','=', ean)],limit=1)
        if product_vte:
            ean_id = product_vte.id
        else:
            templ_vte = template_obj.search([('barcode','=', ean)],limit=1)
            if templ_vte:
                ean_id = templ_vte.id
        return ean_id  

    #########################################################################################
    #                                                                                       #
    #                                  Recherche unité                                      #
    #                                                                                       #
    #########################################################################################
    def recherche_unite(self, unite, article_id):
        company_id =  self.env.company 
        edi_obj = self.env['parametre.edi'] 
        article_obj = self.env['product.product']       
        unite_id = False
        unite_obj = self.env['uom.uom']
        unite_vte = unite_obj.search([('unite_edi','=', unite)],limit=1)
        if unite_vte:
            unite_id = unite_vte.id  
        if unite_id == False:
            article_unite = article_obj.search([('id','=', article_id)],limit=1)
            if article_unite:
                unite_id = article_unite.uom_id.id
            else:
                unite_id = False
            if unite_id == False:
                if company_id.param_edi_id:
                    param = edi_obj.search([('id', '=', company_id.param_edi_id.id)])
                    if len(param)>0:
                        if param.unite_par_defaut:
                            unite_id = param.unite_par_defaut.id        

        return unite_id                                 

    #########################################################################################
    #                                                                                       #
    #                                    Recherche pays                                     #
    #                                                                                       #
    #########################################################################################
    def recherche_pays(self, pays_search):
        pays_id = False
        pays_obj = self.env['res.country']
        pays = pays_obj.search([('name','=', pays_search)],limit=1)
        if pays:
            pays_id = pays.id
        else:
            pays = pays_obj.search([('code','=', pays_search)],limit=1)
            if pays:
                pays_id = pays.id    
        return pays_id    

    #########################################################################################
    #                                                                                       #
    #                            Génération d'une commande EDI                              #
    #                                                                                       #
    #########################################################################################
    def genere_commande_vente(self,values_entete,values_param,values_comment,values_lignes):
        sale_obj = self.env['sale.order']
        sale_line_obj = self.env['sale.order.line']
        sale = False
        today = fields.Date.to_string(datetime.now())

        company_id =  self.env.company 

        if values_entete:
            for values_ent in values_entete:
                controle_cde = self.controle_commande_existante(values_ent, values_param)
                if not controle_cde:
                    controle_client_edi = self.controle_gestion_commande_edi_partner(values_ent)
                    if controle_client_edi:
                        if values_comment:
                            for values_com in values_comment:
                                commentaire = values_com['comment']
                                values_ent.update({
                                    'comment_edi': commentaire,
                                    })
                                break
                        #
                        # On prend en compte les partenaires des segments PARAM
                        #  
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
                        partner_acheteur = False
                        partner_nad_dp_id = False 
                        partner_livre_a = False
                        if values_param:
                            for values_par in values_param: 
                                type_intervention = values_par['type_interv_id']
                                if type_intervention.name == company_id.par_by_id.name:
                                    ccli_acheteur = values_par['code_interv_id']
                                    partner_acheteur = self.recherche_partner(ccli_acheteur)
                                    if partner_acheteur:
                                        values_ent.update({
                                            'partner_id': partner_acheteur,
                                            'partner_acheteur_id': partner_acheteur,
                                            }) 

                                #
                                # On gère le cas du PAR+DP sans GLN
                                #    
                                if type_intervention.name == company_id.par_dp_id.name:
                                    ccli_livre_a = values_par['code_interv_id']
                                    if ccli_livre_a:
                                        partner_livre_a = self.recherche_partner(ccli_livre_a)
                                        if partner_livre_a:
                                            values_ent.update({
                                                'partner_shipping_id': partner_livre_a,
                                                'partner_livre_a_id' : partner_livre_a, 
                                                })
                                            partner_nad_dp_id = partner_livre_a   
                                    else:
                                        #
                                        # Pas de GLN dans le PAR+UC, on créé une adresse client liés au NAD+BY
                                        #    
                                        nad_by_id = values_par['nad_by_id']
                                        nom_interv = values_par['nom_interv']
                                        adr1_interv = values_par['adr1_interv']
                                        adr2_interv = values_par['adr2_interv']
                                        cpos_interv = values_par['cpos_interv']
                                        vil_interv = values_par['vil_interv']
                                        pays_interv = values_par['pays_interv']
                                        tel_contact = values_par['tel_contact']
                                        mail_contact = values_par['mail_contact']
                                        no_lig_par = values_par['no_lig']
                                        no_cde_par = values_par['no_cde']

                                        values_adresse_dp = {
                                                'type_adresse' : 'other',
                                                'partner_id' : partner_acheteur,
                                                'nom' : nom_interv,                
                                                'rue1' : adr1_interv,               
                                                'rue2' : adr2_interv,               
                                                'cp' : cpos_interv,                 
                                                'ville' : vil_interv,             
                                                'pays' : pays_interv,                
                                                'email' : mail_contact,              
                                                'tel' : tel_contact,       
                                            }

                                        new_partner_ok = self.creation_adresse_client_final(values_adresse_dp)
                                        if not new_partner_ok:
                                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                                            corps = "Erreur lors de la création de l'adresse du client livré à de la ligne {}. <br/><br>".format(nb_lig_par) 
                                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde_par)                         
                                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                            if not flux:
                                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                            if flux.envoi_auto_mail:   
                                                destinataire = company_id.gestion_user_id.email
                                                if destinataire:
                                                    self.edi_generation_mail(destinataire, sujet, corps)

                                            code_erreur = self.env['erreur.edi'].search([('name','=', '0013')], limit=1) 

                                            message = "Erreur lors de la création de l'adresse du client livré à de la ligne {}. ".format(nb_lig_par) 
                                            message+= "La pièce {} a été rejetée.".format(no_cde_par)  
                                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                            partner_nad_dp_id = False
                                        else:
                                            values_ent.update({
                                                'partner_shipping_id': new_partner_ok.id,
                                                'partner_livre_a_id' : new_partner_ok.id, 
                                                }) 
                                            partner_nad_dp_id = new_partner_ok.id       

                                if type_intervention.name == 'IV':
                                    ccli_facture_a = values_par['code_interv_id']
                                    partner_facture_a = self.recherche_partner(ccli_facture_a)
                                    if partner_facture_a:
                                        values_ent.update({
                                            'partner_invoice_id': partner_facture_a,
                                            'partner_facture_a_id' : partner_facture_a,
                                            })   
                                if type_intervention.name == 'SU':
                                    ccli_vendeur = values_par['code_interv_id']
                                    partner_vendeur = self.recherche_partner(ccli_vendeur)
                                    if partner_vendeur:
                                        values_ent.update({
                                            'partner_vendeur_id': partner_vendeur,
                                            })
                                if type_intervention.name == 'OB':
                                    ccli_commande_par = values_par['code_interv_id']
                                    partner_commande_par = self.recherche_partner(ccli_commande_par)
                                    if partner_commande_par:
                                        values_ent.update({
                                            'partner_id': partner_commande_par,
                                            'partner_commande_par_id': partner_commande_par,
                                            }) 
                                if type_intervention.name == 'PR':
                                    ccli_paye_par = values_par['code_interv_id']
                                    partner_paye_par = self.recherche_partner(ccli_paye_par)
                                    if partner_paye_par:
                                        values_ent.update({
                                            'partner_paye_par_id': partner_paye_par,
                                            })    

                                if type_intervention.name == company_id.par_uc_id.name:
                                    ccli_final = values_par['code_interv_id']
                                    if ccli_final:
                                        partner_final = self.recherche_partner(ccli_final)
                                        if partner_final:
                                            values_ent.update({
                                                'partner_final_id': partner_final,
                                                #'partner_shipping_id': partner_final,
                                                })
                                    else:
                                        #
                                        # Pas de GLN dans le PAR+UC, on créé une adresse client liés au NAD+DP au lieu NAD+BY
                                        #    
                                        nad_by_id = values_par['nad_by_id']
                                        nom_interv = values_par['nom_interv']
                                        adr1_interv = values_par['adr1_interv']
                                        adr2_interv = values_par['adr2_interv']
                                        cpos_interv = values_par['cpos_interv']
                                        vil_interv = values_par['vil_interv']
                                        pays_interv = values_par['pays_interv']
                                        tel_contact = values_par['tel_contact']
                                        mail_contact = values_par['mail_contact']
                                        no_lig_par = values_par['no_lig']
                                        no_cde_par = values_par['no_cde']

                                        if partner_nad_dp_id:
                                            values_adresse_uc = {
                                                    'type_adresse' : 'other',
                                                    'partner_id' : partner_nad_dp_id,
                                                    'nom' : nom_interv,                
                                                    'rue1' : adr1_interv,               
                                                    'rue2' : adr2_interv,               
                                                    'cp' : cpos_interv,                 
                                                    'ville' : vil_interv,             
                                                    'pays' : pays_interv,                
                                                    'email' : mail_contact,              
                                                    'tel' : tel_contact,       
                                                }
                                        else:
                                            values_adresse_uc = {
                                                    'type_adresse' : 'other',
                                                    'partner_id' : partner_acheteur,
                                                    'nom' : nom_interv,                
                                                    'rue1' : adr1_interv,               
                                                    'rue2' : adr2_interv,               
                                                    'cp' : cpos_interv,                 
                                                    'ville' : vil_interv,             
                                                    'pays' : pays_interv,                
                                                    'email' : mail_contact,              
                                                    'tel' : tel_contact,       
                                                }

                                        new_partner_ok = self.creation_adresse_client_final(values_adresse_uc)
                                        if not new_partner_ok:
                                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                                            corps = "Erreur lors de la création de l'adresse du client final de la ligne {}. <br/><br>".format(nb_lig_par) 
                                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde_par)                         
                                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                            if not flux:
                                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                            if flux.envoi_auto_mail:   
                                                destinataire = company_id.gestion_user_id.email
                                                if destinataire:
                                                    self.edi_generation_mail(destinataire, sujet, corps)

                                            code_erreur = self.env['erreur.edi'].search([('name','=', '0013')], limit=1) 

                                            message = "Erreur lors de la création de l'adresse du client final de la ligne {}. ".format(nb_lig_par) 
                                            message+= "La pièce {} a été rejetée.".format(no_cde_par)  
                                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                        else:
                                            values_ent.update({
                                                'partner_final_id': new_partner_ok.id,
                                                #'partner_shipping_id': new_partner_ok.id,
                                                })   

                                if type_intervention.name == company_id.par_ud_id.name:
                                    ccli_final_ud = values_par['code_interv_id']
                                    if ccli_final_ud:
                                        partner_final_ud = self.recherche_partner(ccli_final_ud)
                                        if partner_final_ud:
                                            values_ent.update({
                                                'partner_final_ud_id': partner_final_ud,
                                                })
                                    else:
                                        #
                                        # Pas de GLN dans le PAR+UC, on créé une adresse client liés au NAD+BY
                                        #    
                                        nad_by_id = values_par['nad_by_id']
                                        nom_interv = values_par['nom_interv']
                                        adr1_interv = values_par['adr1_interv']
                                        adr2_interv = values_par['adr2_interv']
                                        cpos_interv = values_par['cpos_interv']
                                        vil_interv = values_par['vil_interv']
                                        pays_interv = values_par['pays_interv']
                                        tel_contact = values_par['tel_contact']
                                        mail_contact = values_par['mail_contact']
                                        no_lig_par = values_par['no_lig']
                                        no_cde_par = values_par['no_cde']

                                        values_adresse_ud = {
                                                'type_adresse' : 'other',
                                                'partner_id' : partner_acheteur,
                                                'nom' : nom_interv,                
                                                'rue1' : adr1_interv,               
                                                'rue2' : adr2_interv,               
                                                'cp' : cpos_interv,                 
                                                'ville' : vil_interv,             
                                                'pays' : pays_interv,                
                                                'email' : mail_contact,              
                                                'tel' : tel_contact,       
                                            }

                                        new_partner_ok = self.creation_adresse_client_final(values_adresse_ud)
                                        if not new_partner_ok:
                                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                                            corps = "Erreur lors de la création de l'adresse du client final UD de la ligne {}. <br/><br>".format(nb_lig_par) 
                                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde_par)                         
                                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                            if not flux:
                                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                            if flux.envoi_auto_mail:   
                                                destinataire = company_id.gestion_user_id.email
                                                if destinataire:
                                                    self.edi_generation_mail(destinataire, sujet, corps)

                                            code_erreur = self.env['erreur.edi'].search([('name','=', '0013')], limit=1) 

                                            message = "Erreur lors de la création de l'adresse du client final UD de la ligne {}. ".format(nb_lig_par) 
                                            message+= "La pièce {} a été rejetée.".format(no_cde_par)  
                                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                        else:
                                            values_ent.update({
                                                'partner_final_ud_id': new_partner_ok.id,
                                                })   

                            #
                            # Si client livraison directe, on affecte NAD+UC dans PAR+DP  
                            # 
                            #if partner_acheteur:
                            if partner_livre_a:    
                                livre_a_edi = client = self.env['res.partner'].search([('id','=', partner_livre_a)], limit=1)
                                if livre_a_edi:
                                    if livre_a_edi.edi_liv_directe:
                                        partner_dp = values_ent.get('partner_livre_a_id')    
                                        partner_uc = values_ent.get('partner_final_id') 
                                        if partner_uc: 
                                            values_ent.update({
                                                    'partner_shipping_id': partner_uc,
                                                    'partner_livre_a_id' : partner_uc, 
                                                    })

                        #
                        # On recherche si on a un commentaire FTX+GEN
                        #
                        if values_comment:
                            for values_com in values_comment:
                                typecom = values_com['type_comm']
                                commentaire_gen = values_com['comment']
                                if typecom == 'GEN':
                                    values_ent.update({
                                        'segment_ftx_gen': True,
                                        'comment_ftx_gen': commentaire_gen,
                                        })
                                break

                        #
                        # On controle la présence du partner_shipping_id et du partner_invoice_id
                        #
                        partner = values_ent.get('partner_id')
                        partner_shipping = values_ent.get('partner_shipping_id')
                        partner_invoice = values_ent.get('partner_invoice_id')

                        # On doit rechercher le partner_shipping_id par défaut si non renseigné
                        if partner_shipping == False:
                            client = self.env['res.partner'].search([('id','=', partner)], limit=1)
                            if client.adresse_liv_id:
                                partner_shipping = client.adresse_liv_id.id
                            else:    
                                addr = client.address_get(['delivery', 'invoice'])
                                partner_shipping = addr['delivery']
                            values_ent.update({
                                            'partner_shipping_id': partner_shipping,
                                            }) 


       
                        # On doit rechercher le partner_invoice_id par défaut si non renseigné
                        if partner_invoice == False:
                            client = self.env['res.partner'].search([('id','=', partner)], limit=1)
                            if client.adresse_fac_id:
                                partner_invoice = client.adresse_fac_id.id
                            else: 
                                addr = client.address_get(['delivery', 'invoice'])
                                partner_invoice = addr['invoice']
                            values_ent.update({
                                            'partner_invoice_id': partner_invoice,
                                            }) 

                        #
                        # On ajoute la remise globale du client s'il en a une et le mode de paiement
                        # 
                        client = self.env['res.partner'].search([('id','=', partner)], limit=1)   
                        if client:
                            if client.sale_global_discount:
                                global_discount_client = client.sale_global_discount  
                                values_ent.update({
                                            'global_discount': global_discount_client,
                                            }) 
                            if client.property_payment_term_id:
                                values_ent.update({
                                            'payment_term_id': client.property_payment_term_id.id,
                                            }) 

                            date_livraison_demandee = values_ent.get('date_livraison_demandee')
                            date_order_edi = values_ent.get('date_order')

                            date_livraison_demandee = datetime.strptime(date_livraison_demandee, '%Y-%m-%d')
                            date_order_edi = datetime.strptime(date_order_edi, '%Y-%m-%d')
                            
                            date_livraison_demandee = apik_calendar.calcul_date_ouvree(date_livraison_demandee, 0, company_id.nb_weekend_days, company_id.zone_geo)  
            
                            if date_order_edi:
                                if client.delai_livraison:
                                    nb_jour = client.delai_livraison
                                else:
                                    nb_jour = 0  

                                #date_livraison_calculee = date_order_edi + timedelta(days=nb_jour) 
                                date_livraison_calculee = apik_calendar.calcul_date_ouvree(date_order_edi, nb_jour, company_id.nb_weekend_days, company_id.zone_geo)  
                            else:
                                if client.delai_livraison:
                                    nb_jour = client.delai_livraison
                                else:
                                    nb_jour = 0 
                                date_du_jour = datetime.now()    
                                #date_livraison_calculee = date_du_jour + timedelta(days=nb_jour)
                                date_livraison_calculee = apik_calendar.calcul_date_ouvree(date_du_jour, nb_jour, company_id.nb_weekend_days, company_id.zone_geo)  
  
                            #date_livraison_calculee = sale_obj.calcule_jour_ouvre_francais(date_livraison_calculee) 
                            
                            if date_livraison_calculee and date_livraison_demandee:
                                if date_livraison_calculee > date_livraison_demandee:
                                    date_livraison_finale = date_livraison_calculee
                                else:
                                    date_livraison_finale = date_livraison_demandee
                            else:
                                date_livraison_finale = date_order_edi 

                            values_ent.update({
                                'date_livraison_calculee': date_livraison_calculee,
                                'commitment_date': date_livraison_finale,
                                }) 

                        shipping_partner = values_ent.get('partner_shipping_id')        
                        client_liv = self.env['res.partner'].search([('id','=', shipping_partner)], limit=1)   
                        if client_liv:
                            cde_xdock = False
                            if client_liv.xdock:
                                cde_xdock = True
                            if client_liv.intrastat_transport_id:
                                intrastat_transport_id = client_liv.intrastat_transport_id.id 
                            else:
                                intrastat_transport_id = False
                            if client_liv.madeco_transport_id:
                                madeco_transport_id = client_liv.madeco_transport_id.id 
                            else:
                                madeco_transport_id = False    
                            values_ent.update({
                                'xdock': cde_xdock,
                                'intrastat_transport_id': intrastat_transport_id,
                                'madeco_transport_id': madeco_transport_id,
                                })        
                        #logger.info("__________________________________________________________")
                        #logger.info(values_ent)
                        #logger.info("__________________________________________________________")


                        sale = sale_obj.create(values_ent)
                        
                        if sale:
                            if values_lignes:
                                for values_lig in values_lignes:
                                    values_lig.update({
                                        'order_id': sale.id,
                                        })

                                    sale_lig = sale_line_obj.create(values_lig)

                            sale.fiscal_position_id = self.env['account.fiscal.position'].with_company(sale.company_id).get_fiscal_position(sale.partner_id.id, sale.partner_shipping_id.id)

                            #
                            # On met à jour les commandes intégrées 
                            #
                            if sale.state in ('draft','sent'):
                                affect = sale.affectation_routes_logistiques_sale_order_line(sale)

                            if not sale.route_id:
                                ent_route_id = sale.recherche_route_unique_sur_commande(sale)   
                                if ent_route_id:
                                    sale.route_id = ent_route_id 

                                if not sale.intrastat_transport_id:
                                    if sale.partner_shipping_id.intrastat_transport_id:
                                        sale.intrastat_transport_id = sale.partner_shipping_id.intrastat_transport_id.id   
                                if not sale.madeco_transport_id:
                                    if sale.partner_shipping_id.madeco_transport_id:
                                        sale.madeco_transport_id = sale.partner_shipping_id.madeco_transport_id.id   

                            #
                            # On recherche la politique d'expédition à affecter
                            #
                            if sale.segment_ftx_gen:
                                sale.picking_policy = 'one'
                            else:
                                # Le champ RFF+ON / RFF+UC où RFF+CR où RFF+CT est renseigné
                                ref2_div = sale.ref2_div.strip()
                                ref_cde_client_edi = sale.ref_cde_client_edi.strip()
                                ref_cde_client_final_edi = sale.ref_cde_client_final_edi.strip()
                                no_contrat = sale.no_contrat.strip()
                                '''
                                logger.info("ref2_div RFF+CR")
                                logger.info(ref2_div)
                                logger.info(len(ref2_div))
                                logger.info("ref_cde_client_edi RFF+ON")
                                logger.info(ref_cde_client_edi)
                                logger.info(len(ref_cde_client_edi))
                                logger.info("ref_cde_client_final_edi RFF+UC")
                                logger.info(ref_cde_client_final_edi)
                                logger.info(len(ref_cde_client_final_edi))
                                logger.info("no_contrat RFF+CT")
                                logger.info(no_contrat)
                                logger.info(len(no_contrat))
                                '''
                                if ref2_div or ref_cde_client_edi or ref_cde_client_final_edi or no_contrat:   
                                    if len(ref2_div)>=1 or len(ref_cde_client_edi)>=1 or len(ref_cde_client_final_edi)>=1 or len(no_contrat)>=1:    
                                        sale.picking_policy = 'one'

                            #
                            # On controle la validation automatique des commandes si on est sur un devis.
                            #
                            if sale.state in ('draft','sent'):
                                if sale.commande_edi: 
                                    valid_auto = sale.recherche_validation_automatique_commande(sale) 
                                    if valid_auto:
                                        res = sale.action_confirm() 

                            #
                            # On envoie un mail sur la commande créée et on met à jour le suivi EDI
                            #             
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                            corps = "La commande {} pour le client {} a été intégrée avec succès. <br/><br>".format(sale.name,sale.partner_id.name) 
                            corps+= "Le numéro de commande EDI est {}. <br/><br>".format(sale.no_cde_client)  
                            corps+= "La pièce est en devis dans votre ERP. <br/><br>"                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)

                            code_erreur = self.env['erreur.edi'].search([('name','=', '0500')], limit=1) 

                            message = "La commande {} pour le client {} a été intégrée avec succès. ".format(sale.name,sale.partner_id.name) 
                            message+= "Le numéro de commande EDI est {}.".format(sale.no_cde_client)  
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                    else:
                        sale = False        
                else:
                    sale = False        
        
        return sale        

    #########################################################################################
    #                                                                                       #
    #           Création adresse Livré à & client final  PAR+UC - PAR+UD - PAR+DP           #
    #                                                                                       #
    #########################################################################################
    def creation_adresse_client_final(self,values_adresse):
        partner_new_obj = self.env['res.partner']
        values_partner = {}
        partner_new = False
        if values_adresse:
            type_adr            = values_adresse['type_adresse']
            partner_id          = values_adresse['partner_id']
            nom                 = values_adresse['nom']
            rue1                = values_adresse['rue1']
            rue2                = values_adresse['rue2']
            cp                  = values_adresse['cp']
            ville               = values_adresse['ville']
            pays                = values_adresse['pays']
            email               = values_adresse['email']
            tel                 = values_adresse['tel']
            
            if nom:
                nom = nom.strip()
            if rue1:
                rue1 = rue1.strip()
            if rue2:
                rue2 = rue2.strip()
            if cp:
                cp = cp.strip()
            if ville:
                ville = ville.strip() 
            if email:
                email = email.strip() 
            if tel:
                tel = tel.strip()            

            parent_id = self.recherche_partenaire(partner_id)
            if pays:
                pays_id = self.recherche_pays(pays.strip())  
            else:
                pays_id = False         

            values_partner = {
                'name' : nom,
                'parent_id' : partner_id,
                'street' : rue1,
                'street2' : rue2,
                'zip': cp,
                'city': ville,
                'country_id' : pays_id,
                'email' : email,
                'phone' : tel,
                'type' : type_adr,
                'client_web': True,
            }

            partner_new = partner_new_obj.create(values_partner)

            if partner_new:
                return partner_new
            else:
                return False    
    
    #########################################################################################
    #                                                                                       #
    #                      Controle existence commande pour le partner                      #
    #                                                                                       #
    #########################################################################################
    def controle_commande_existante(self,values_ent,values_param):
        sale_obj = self.env['sale.order']
        partner_obj = self.env['res.partner']
        commande_existante = False
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company 

        partner_id = values_ent['partner_id']
        ref_cde = values_ent['client_order_ref'].strip()

        if values_param:
            for values_par in values_param: 
                type_intervention = values_par['type_interv_id']
                if type_intervention.name == 'BY':
                    ccli_acheteur = values_par['code_interv_id']
                    partner_acheteur = self.recherche_partner(ccli_acheteur)
                    if partner_acheteur:
                        partner_id = partner_acheteur

                if type_intervention.name == 'OB':
                    ccli_commande_par = values_par['code_interv_id']
                    partner_commande_par = self.recherche_partner(ccli_commande_par)
                    if partner_commande_par:
                        partner_id = partner_commande_par

        cde_vte = sale_obj.search([('partner_id','=', partner_id),('client_order_ref','=',ref_cde)],limit=1)
        
        if cde_vte:
            commande_existante = True
            client = partner_obj.search([('id','=', partner_id)],limit=1)
            #
            # Erreur sur commande déjà existante dans la base de données Odoo
            #
            sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
            corps = "La commande avec la référence {} est déjà existante pour le client {}. <br/><br>".format(ref_cde, client.name) 
            corps+= "La commande n'est pas récréée. <br/><br>"                         
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
            if not flux:
                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
            if flux.envoi_auto_mail:   
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.edi_generation_mail(destinataire, sujet, corps)

            code_erreur = self.env['erreur.edi'].search([('name','=', '0501')], limit=1) 

            message = "La commande avec la référence {} est déjà existante pour le client {}. ".format(ref_cde, client.name)
            message+= "La commande n'est pas récréée. "   
            self.edi_generation_erreur(code_erreur, flux, sujet, message)

        return commande_existante

    #########################################################################################
    #                                                                                       #
    #                      Controle gestion des commandes EDI du client                     #
    #                                                                                       #
    #########################################################################################
    def controle_gestion_commande_edi_partner(self,values_ent):
        partner_obj = self.env['res.partner']
        client_edi = False
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company 

        partner_id = values_ent['partner_id']
        ref_cde = values_ent['client_order_ref'].strip()

        client = partner_obj.search([('id','=', partner_id)],limit=1)
        if client:
            if client.client_edi:
                if client.edi_order:
                    client_edi = True
                else:
                    #
                    # Le client n'est pas en gestion EDI
                    #
                    sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                    corps = "La gestion des commandes EDI n'est pas autorisée pour le client {}. <br/><br>".format(client.name) 
                    corps+= "La commande {} n'est pas créée. <br/><br>".format(ref_cde)                         
                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                    flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                    if not flux:
                        flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                    if flux.envoi_auto_mail:   
                        destinataire = company_id.gestion_user_id.email
                        if destinataire:
                            self.edi_generation_mail(destinataire, sujet, corps)

                    code_erreur = self.env['erreur.edi'].search([('name','=', '0401')], limit=1) 

                    message = "La gestion des commandes EDI n'est pas autorisée pour le client {}. ".format(client.name) 
                    message+= "La commande {} n'est pas créée. ".format(ref_cde)    
                    self.edi_generation_erreur(code_erreur, flux, sujet, message)   
            else:    
                #
                # Le client n'est pas en gestion EDI
                #
                sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                corps = "Le client {} n'est pas géré en EDI. <br/><br>".format(client.name) 
                corps+= "La commande {} n'est pas créée. <br/><br>".format(ref_cde)                         
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
               
                flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                if not flux:
                    flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                if flux.envoi_auto_mail:   
                    destinataire = company_id.gestion_user_id.email
                    if destinataire:
                        self.edi_generation_mail(destinataire, sujet, corps)

                code_erreur = self.env['erreur.edi'].search([('name','=', '0400')], limit=1) 

                message = "Le client {} n'est pas géré en EDI. ".format(client.name) 
                message+= "La commande {} n'est pas créée. ".format(ref_cde)    
                self.edi_generation_erreur(code_erreur, flux, sujet, message)

        return client_edi

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
            rep_depart = param.rep_import_interne_edi.strip()
            fichier = filename.strip()
            fichier_a_deplacer = rep_depart + '/' + fichier
            if trait_ok:
                #
                # On transfère le fichier dans le répertoire de stockage ok
                #
                rep_destination = rep_depart + param.rep_sauvegarde_fichier_traite.strip()
            else:
                #
                # On transfère le fichier dans le répertoire de stockage des fichiers en échec
                #
                rep_destination = rep_depart + param.rep_sauvegarde_fichier_erreur.strip()

            ordre_a_executer = 'mv %s %s '%(fichier_a_deplacer, rep_destination)
            exec = os.system(ordre_a_executer)

            copy_ok = True   
        else:
            copy_ok = False    

    #########################################################################################
    #                                                                                       #
    #             On déplace le fichier traité dans les répertoires de stockage             #
    #                                                                                       #
    #########################################################################################
    def delete_fichier_traite(self,filename):
        company_id =  self.env.company 
        edi_obj = self.env['parametre.edi']
        param = edi_obj.search([('id', '=', company_id.param_edi_id.id)])
        if len(param)>0:
            rep_depart = param.rep_import_interne_edi.strip()
            fichier = filename.strip()
            fichier_a_deplacer = rep_depart + '/' + fichier
            
            ordre_a_executer = 'del %s '%(fichier_a_deplacer)
            exec = os.system(ordre_a_executer)

            delete_ok = True   
        else:
            delete_ok = False            


#########################################
#                                       #
#              Flux ORDCHG              #
#                                       #
#########################################

    # ICI
    ########################################################################################################
    #                                                                                                      #
    #      On lit le fichier et on génère une liste de données pour les changements de commandes TX2       #
    #                                                                                                      #
    ########################################################################################################    
    def edi_import_tx2_import_ordchg(self, file_bytes, file_name):
        company_id =  self.env.company 
        sale_obj = self.env['sale.order']     
        nb_lig = 0
        res = []
        res_ent = []
        res_par = []
        res_com = []
        res_lig = []
        creat_ligne_sans_erreur = False
        au_moins_une_ligne = False

        file_str = file_bytes.decode(self.file_encoding)

        today = fields.Date.to_string(datetime.now())

        self.type_fichier = file_name[0:6]

        if self.type_fichier not in ('ORDCHG'):
            sujet = str(self.env.company.name) + ' - Gestion EDI - Changement sur commandes client du ' + str(today) 
            corps = "Le type de fichier est incorrect. Il doit être de type 'ORDCHG'. <br/><br>" 
            corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
            if not flux:
               flux = self.env['flux.edi'].search([('name','=', 'ORDCHG')], limit=1) 
            if flux.envoi_auto_mail:   
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.edi_generation_mail(destinataire, sujet, corps)

            code_erreur = self.env['erreur.edi'].search([('name','=', '9003')], limit=1) 
            
            message = "Le type de fichier est incorrect. Il doit être de type 'ORDCHG'. "
            message+= "Le fichier {} a été rejeté. ".format(file_name)  
            self.edi_generation_erreur(code_erreur, flux, sujet, message)   
            return res    
        
        for l in file_str.split('\n'):
            nb_lig += 1
            if len(l) < 4 :
                continue
            if l[0] != '':
                creat_cde = False
                type_ligne  = l[0:3]

                if type_ligne not in ('ENT','COM','PAR','LIG'):
                    #
                    # Erreur sur type de ligne
                    #
                    sujet = str(self.env.company.name) + ' - Gestion EDI - Changement sur commandes client du ' + str(today) 
                    corps = "Le type de ligne est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                    corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                    flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                    if not flux:
                        flux = self.env['flux.edi'].search([('name','=', 'ORDCHG')], limit=1) 
                    '''
                    if flux.envoi_auto_mail:   
                        destinataire = company_id.gestion_user_id.email
                        if destinataire:
                            self.edi_generation_mail(destinataire, sujet, corps)
                    '''        
                    code_erreur = self.env['erreur.edi'].search([('name','=', '9004')], limit=1) 

                    message = "Le type de ligne est incorrect à la ligne {}.".format(nb_lig) 
                    message+= "Le fichier {} a été rejeté. ".format(file_name) 
                    self.edi_generation_erreur(code_erreur, flux, sujet, message)
                    break 
                if type_ligne == 'ENT':
                    #
                    # Si on a déjà une entête, on intégre la commande dans les données à intégrer si on a au moins une ligne de commande
                    #   
                    if len(res_ent)>=1 and creat_ligne_sans_erreur and au_moins_une_ligne:
                       
                        for entete in res_ent:
                            res.append(entete)
                        for param in res_par:
                            res.append(param)
                        for comment in res_com:
                            res.append(comment)    
                        for ligne in res_lig:
                            res.append(ligne) 

                        au_moins_une_ligne = False    

                        # 
                        # On réinitialise les tables
                        #
                        res_ent = []        
                        res_par = [] 
                        res_com = [] 
                        res_lig = []

                    creat_ligne_sans_erreur = True 

                    # 
                    # Ligne entête
                    #
                    if len(l) < 1096:
                        #
                        # Erreur sur longueur d'enregistrement
                        #
                        sujet = str(self.env.company.name) + ' - Gestion EDI - Changement sur commandes client du ' + str(today) 
                        corps = "La longueur de l'enregistrement de l'entête est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                        corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
                        corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                        
                        flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                        if not flux:
                            flux = self.env['flux.edi'].search([('name','=', 'ORDCHG')], limit=1) 
                        '''
                        if flux.envoi_auto_mail:   
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.edi_generation_mail(destinataire, sujet, corps)
                        '''
                        code_erreur = self.env['erreur.edi'].search([('name','=', '9001')], limit=1) 

                        message = "La longueur de l'enregistrement de l'entête est incorrect à la ligne {}. ".format(nb_lig)
                        message+= "Le fichier {} a été rejeté. ".format(file_name)  
                        self.edi_generation_erreur(code_erreur, flux, sujet, message)
                        break
                    else:  
                        client_ok = True  
                        ccli_emet           = l[3:38]
                        ccli_dest           = l[38:73]
                        no_cde              = l[73:108]
                        type_cde            = l[108:111]
                        code_function       = l[111:114]
                        date_cde            = l[114:122]
                        heure_cde           = l[122:126]
                        code_payment_term   = l[126:129]
                        code_moyen_garantie = l[129:132]
                        code_method_payment = l[132:135]
                        code_canal_payment  = l[135:138]
                        code_legal_type     = l[138:141]
                        code_special_terms  = l[141:144]
                        date_liv            = l[144:152]
                        heure_liv           = l[152:156]
                        date_enlev          = l[156:164]
                        heure_enlev         = l[164:168]
                        no_contrat          = l[168:203]
                        ref_cde_client      = l[203:238]
                        no_cde_rempl        = l[238:273]
                        no_ope_promo        = l[273:308]
                        devise              = l[308:311]
                        comment_cde         = l[311:661]
                        comment_speciaux    = l[661:1011]
                        qualifiant_code_ref = l[1011:1014]
                        identifiant_ref     = l[1015:1084]
                        date_ref            = l[1084:1092]
                        heure_ref           = l[1092:1096]
                       
                        no_cde = no_cde.strip()
                        ctrl_emet = self.controle_partenaire(ccli_emet.strip())
                        if ctrl_emet:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                            corps = "Le GLN du partenaire {} est inconnu à la ligne {}. <br/><br>".format(ccli_emet,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            
                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            '''                          
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)
                            '''
                            code_erreur = self.env['erreur.edi'].search([('name','=', '0001')], limit=1) 

                            message = "Le GLN du partenaire {} est inconnu à la ligne {}. ".format(ccli_emet,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            client_ok = False
                        
                        ctrl_dest = self.controle_partenaire(ccli_dest.strip())
                        if ctrl_dest:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                            corps = "Le GLN du partenaire {} est inconnu à la ligne {}. <br/><br>".format(ccli_dest,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            '''
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)
                            '''
                            code_erreur = self.env['erreur.edi'].search([('name','=', '0001')], limit=1) 

                            message = "Le GLN du partenaire {} est inconnu à la ligne {}. ".format(ccli_dest,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            client_ok = False
                        
                        if client_ok:
                            creat_cde = True
                        else:
                            creat_cde = False    

                        ctrl_type_cde = self.controle_type_commande(type_cde,'ORDCHG')    
                        if ctrl_type_cde:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                            corps = "Le type de commande {} est inconnu à la ligne {}. <br/><br>".format(type_cde,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            '''
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)
                            '''
                            code_erreur = self.env['erreur.edi'].search([('name','=', '0005')], limit=1) 

                            message = "Le type de commande {} est inconnu à la ligne {}. ".format(type_cde,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            creat_cde = False
                        else:
                            creat_cde = True 

                        ctrl_code_function = self.controle_function_commande(code_function)    
                        if ctrl_code_function:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                            corps = "La fonction de la commande {} est inconnue à la ligne {}. <br/><br>".format(code_function,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            '''
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)
                            '''
                            code_erreur = self.env['erreur.edi'].search([('name','=', '0006')], limit=1) 

                            message = "La fonction de la commande {} est inconnue à la ligne {}. ".format(code_function,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            creat_cde = False
                        else:
                            creat_cde = True 

                        if creat_cde:
                            vals_ent = {
                                'type': type_ligne,
                                'no_client_emet': ccli_emet,
                                'no_client_dest': ccli_dest,
                                'no_cde': no_cde,
                                'type_cde': type_cde,
                                'code_function': code_function,
                                'date_cde': date_cde,                                                    
                                'heure_cde': heure_cde,
                                'date_liv': date_liv,                                                    
                                'heure_liv': heure_liv,
                                'date_enlev': date_enlev,                                                    
                                'heure_enlev': heure_enlev,
                                'no_contrat': no_contrat,
                                'ref_cde_client': ref_cde_client,
                                'no_cde_rempl': no_cde_rempl,
                                'no_ope_promo': no_ope_promo, 
                                'comment_cde': comment_cde,
                                'comment_speciaux': comment_speciaux, 
                                'line': nb_lig,
                            }               
                            res_ent.append(vals_ent)

                if type_ligne == 'PAR': #and creat_cde:
                    # 
                    # Ligne parametre
                    #                  
                    if not client_ok:
                        continue
                    if len(l) < 506:
                        #
                        # Erreur sur longueur d'enregistrement
                        #
                        sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                        corps = "La longueur de l'enregistrement paramêtre est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                        corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
                        corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                        flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                        if not flux:
                            flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                        '''
                        if flux.envoi_auto_mail:   
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.edi_generation_mail(destinataire, sujet, corps)
                        '''
                        code_erreur = self.env['erreur.edi'].search([('name','=', '9001')], limit=1) 

                        message = "La longueur de l'enregistrement paramêtre est incorrect à la ligne {}. ".format(nb_lig) 
                        message+= "Le fichier {} a été rejeté. ".format(file_name)  
                        self.edi_generation_erreur(code_erreur, flux, sujet, message)
                        client_ok = False
                        break
                    else:
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
                        type_interv         = l[3:6]
                        code_interv         = l[6:26]
                        ident_interv        = l[26:29]
                        nom_interv          = l[29:99]
                        adr1_interv         = l[99:134]
                        adr2_interv         = l[134:169]
                        adr3_interv         = l[169:204]
                        cpos_interv         = l[204:213]
                        vil_interv          = l[213:248]
                        pays_interv         = l[248:250]
                        ident_compl1        = l[250:285]
                        type_ident1         = l[285:288]
                        ident_compl2        = l[288:323]
                        type_ident2         = l[323:326]
                        ident_compl3        = l[326:361]
                        type_ident3         = l[361:364]
                        ident_compl4        = l[364:399]
                        type_ident4         = l[399:402]
                        nom_contact         = l[402:437]
                        tel_contact         = l[437:472]
                        mail_contact        = l[472:507]   

                        type_interv = type_interv.strip()
                        code_interv = code_interv.strip()
                        ident_interv = ident_interv.strip()                        

                        ctrl_type_interv = self.controle_type_intervenant(type_interv)    
                        if ctrl_type_interv:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                            corps = "Le type d'intervenant qualifiant de la commande {} est inconnu à la ligne {}. <br/><br>".format(type_interv,nb_lig) 
                            corps+= "La pièce {} a été rejetée. ".format(no_cde) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            '''
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)
                            '''
                            code_erreur = self.env['erreur.edi'].search([('name','=', '0009')], limit=1) 

                            message = "Le type d'intervenant qualifiant de la commande {} est inconnu à la ligne {}. ".format(type_interv,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            client_ok = False
                            continue                         
                        #NAD + UC        
                        if type_interv == company_id.par_uc_id.name:
                            if not code_interv:
                                # 
                                # On doit créer une adresse (autres adresses) liés avec le PAR+BY
                                # 
                                ctrl_code_interv = False
                            else:
                                ctrl_code_interv = self.controle_partenaire(code_interv) 
                        else:                
                            ctrl_code_interv = self.controle_partenaire(code_interv)    
                        #NAD + UD
                        if type_interv == company_id.par_ud_id.name:
                            if not code_interv:
                                # 
                                # On doit créer une adresse (autres adresses) liés avec le PAR+BY
                                # 
                                ctrl_code_interv = False
                            else:
                                ctrl_code_interv = self.controle_partenaire(code_interv) 
                        else:                
                            ctrl_code_interv = self.controle_partenaire(code_interv)
                        #NAD + DP
                        if type_interv == company_id.par_dp_id.name:
                            if not code_interv:
                                # 
                                # On doit créer une adresse (autres adresses) liés avec le PAR+BY
                                # 
                                ctrl_code_interv = False
                            else:
                                ctrl_code_interv = self.controle_partenaire(code_interv) 
                        else:                
                            ctrl_code_interv = self.controle_partenaire(code_interv)        
                        if ctrl_code_interv:
                            segment_par = 'PAR+'+type_interv
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                            corps = "Le code identifiant {} de l'intervenant de la commande {} est inconnu à la ligne {}. <br/><br>".format(segment_par,code_interv,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            '''
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)
                            '''
                            code_erreur = self.env['erreur.edi'].search([('name','=', '0001')], limit=1) 

                            message = "Le code identifiant {} de l'intervenant de la commande {} est inconnu à la ligne {}.".format(segment_par,code_interv,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            client_ok = False
                            continue                         
                        
                        vals_par = {
                            'type': type_ligne,
                            'type_interv': type_interv,
                            'code_interv': code_interv,
                            'ident_interv': ident_interv,
                            'nom_interv': nom_interv,
                            'adr1_interv': adr1_interv,
                            'adr2_interv': adr2_interv,                                                    
                            'adr3_interv': adr3_interv,
                            'cpos_interv': cpos_interv,                                                    
                            'vil_interv': vil_interv,
                            'pays_interv': pays_interv,                                                    
                            'ident_compl1': ident_compl1,
                            'type_ident1': type_ident1,
                            'ident_compl2': ident_compl2,
                            'type_ident2': type_ident2,
                            'ident_compl3': ident_compl3,
                            'type_ident3': type_ident3,
                            'ident_compl4': ident_compl4,
                            'type_ident4': type_ident4,
                            'nom_contact': nom_contact,
                            'tel_contact': tel_contact,
                            'mail_contact': mail_contact,                             
                            'line': nb_lig,
                            'no_cde': no_cde,
                        }               
                        res_par.append(vals_par) 

                if type_ligne == 'COM':
                    # 
                    # Ligne commentaire
                    #
                    if not client_ok:
                        continue
                    if len(l) < 353:
                        #
                        # Erreur sur longueur d'enregistrement
                        #
                        sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                        corps = "La longueur de l'enregistrement commentaire est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                        corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
                        corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                        flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                        if not flux:
                            flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                        '''
                        if flux.envoi_auto_mail:   
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.edi_generation_mail(destinataire, sujet, corps)
                        '''
                        code_erreur = self.env['erreur.edi'].search([('name','=', '9001')], limit=1) 

                        message = "La longueur de l'enregistrement commentaire est incorrect à la ligne {}.".format(nb_lig) 
                        message+= "Le fichier {} a été rejeté. ".format(file_name) 
                        self.edi_generation_erreur(code_erreur, flux, sujet, message)
                        break
                    else:
                        comm1               = l[3:73]
                        comm2               = l[73:143]
                        comm3               = l[143:213]
                        comm4               = l[213:283]
                        comm5               = l[283:353]       

                        vals_com = {
                            'type': type_ligne,
                            'comm1': comm1,
                            'comm2': comm2,
                            'comm3': comm3,
                            'comm4': comm4,
                            'comm5': comm5,                                                    
                            'line': nb_lig,
                        }               
                        res_com.append(vals_com) 

                '''
                if type_ligne == 'LIG':
                    # 
                    # Ligne Articles
                    #
                    if not client_ok:
                        continue

                    if len(l) < 915:
                        #
                        # Erreur sur longueur d'enregistrement
                        #
                        sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                        corps = "La longueur de l'enregistrement commentaire est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                        corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
                        corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                        flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                        if not flux:
                            flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                        
                        code_erreur = self.env['erreur.edi'].search([('name','=', '9001')], limit=1) 

                        message = "La longueur de l'enregistrement de la ligne est incorrect à la ligne {}.".format(nb_lig) 
                        message+= "Le fichier {} a été rejeté. ".format(file_name)
                        self.edi_generation_erreur(code_erreur, flux, sujet, message)
                        break
                    else:
                        creat_lig = True
                        no_ligne            = l[3:9]
                        ean                 = l[9:44]
                        code_art_vendeur    = l[44:79]
                        code_art_acheteur   = l[79:114]
                        qte_cde             = l[114:129]
                        unite_cde           = l[129:132]
                        qte_pcb             = l[132:147]
                        unite_pcb           = l[147:150]
                        qte_gratuit         = l[150:165]
                        unite_gratuit       = l[165:168]
                        desc_art            = l[168:308]
                        pub                 = l[308:317]
                        pun                 = l[317:326]
                        pvc                 = l[326:335]
                        mt_net_ligne        = l[335:353]
                        nb_ul               = l[353:361]
                        type_emballage      = l[361:368]
                        ean_ul              = l[368:382]
                        date_liv            = l[382:390]
                        heure_liv           = l[390:394]
                        no_cde_magasin      = l[394:429]
                        gln_magasin         = l[429:442]
                        comment             = l[442:792]
                        ref_cde_cli_final   = l[792:827]
                        no_cde_remplace     = l[827:862]
                        no_ope_promo        = l[862:897]
                        no_lig_erp_cli      = l[897:903]
                        modif_type_reponse  = l[903:915]
               
                        ctrl_ean_article = self.controle_ean_article(ean.strip())    
                        if ctrl_ean_article:
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                            corps = "L'article de la commande {} est inconnu à la ligne {}. <br/><br>".format(ean,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                            
                            code_erreur = self.env['erreur.edi'].search([('name','=', '0010')], limit=1) 

                            message = "L'article de la commande {} est inconnu à la ligne {}.".format(ean,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde)   
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                            creat_lig = False
                            creat_ligne_sans_erreur = False
                            continue                        

                        unite_cde = unite_cde.strip()
                        if unite_cde:
                            ctrl_unite_cde = self.controle_unite(unite_cde)    
                            if ctrl_unite_cde:
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                                corps = "L'unité de la quantité commandée de la commande {} est inconnu à la ligne {}. <br/><br>".format(unite_cde,nb_lig) 
                                corps+= "La pièce {} a été rejetée . <br/><br>".format(no_cde)                         
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                if not flux:
                                    flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                
                                code_erreur = self.env['erreur.edi'].search([('name','=', '0011')], limit=1) 

                                message = "L'unité de la quantité commandée de la commande {} est inconnu à la ligne {}.".format(unite_cde,nb_lig)
                                message+= "La pièce {} a été rejetée . ".format(no_cde)  
                                self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                creat_lig = False
                                creat_ligne_sans_erreur = False
                                continue                           

                        unite_pcb = unite_pcb.strip()
                        if unite_pcb:
                            ctrl_unite_pcb = self.controle_unite(unite_pcb)    
                            if ctrl_unite_pcb:
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                                corps = "L'unité de pcb de l'article de la commande {} est inconnu à la ligne {}. <br/><br>".format(unite_pcb,nb_lig) 
                                corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                if not flux:
                                    flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                
                                code_erreur = self.env['erreur.edi'].search([('name','=', '0011')], limit=1) 

                                message = "L'unité de pcb de l'article de la commande {} est inconnu à la ligne {}.".format(unite_pcb,nb_lig) 
                                message+= "La pièce {} a été rejetée. ".format(no_cde)  
                                self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                creat_lig = False
                                creat_ligne_sans_erreur = False
                                continue  

                        unite_gratuit = unite_gratuit.strip()
                        if unite_gratuit:
                            ctrl_unite_gratuit = self.controle_unite(unite_gratuit)    
                            if ctrl_unite_gratuit:
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                                corps = "L'unité de la quantité gratuite de la commande {} est inconnu à la ligne {}. <br/><br>".format(unite_gratuit,nb_lig) 
                                corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                         
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                if not flux:
                                    flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                
                                code_erreur = self.env['erreur.edi'].search([('name','=', '0011')], limit=1) 

                                messacommentge = "L'unité de la quantité gratuite de la commande {} est inconnu à la ligne {}.".format(unite_gratuit,nb_lig)
                                message+= "La pièce {} a été rejetée. ".format(no_cde)  
                                self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                creat_lig = False
                                creat_ligne_sans_erreur = False
                                continue

                        gln_magasin = gln_magasin.strip()
                        if gln_magasin:
                            ctrl_gln_magasin = self.controle_partenaire(gln_magasin)    
                            if ctrl_gln_magasin:
                                sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                                corps = "Le GLN magasin {} de la commande {} est inconnu à la ligne {}. <br/><br>".format(gln_magasin,no_cde,nb_lig) 
                                corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde)                       
                                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                if not flux:
                                    flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                
                                code_erreur = self.env['erreur.edi'].search([('name','=', '0001')], limit=1) 

                                message = "Le GLN magasin {} de la commande {} est inconnu à la ligne {}.".format(gln_magasin,no_cde,nb_lig)
                                message+= "La pièce {} a été rejetée. ".format(no_cde)  
                                self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                creat_lig = False
                                creat_ligne_sans_erreur = False  
                                continue                                

                        if creat_lig:                            
                            vals_lig = {
                                'type': type_ligne,
                                'no_ligne': no_ligne,
                                'ean': ean,
                                'code_art_vendeur': code_art_vendeur,
                                'code_art_acheteur': code_art_acheteur,
                                'qte_cde': qte_cde,
                                'unite_cde': unite_cde,   
                                'qte_pcb': qte_pcb,
                                'unite_pcb': unite_pcb,                                                  
                                'qte_gratuit': qte_gratuit,
                                'unite_gratuit': unite_gratuit,
                                'desc_art': desc_art,
                                'pub': pub,
                                'pun': pun,
                                'pvc': pvc,
                                'mt_net_ligne': mt_net_ligne,
                                'nb_ul': nb_ul,
                                'type_emballage': type_emballage,
                                'ean_ul': ean_ul,
                                'date_liv': date_liv,                                                    
                                'heure_liv': heure_liv,
                                'no_cde_magasin': no_cde_magasin,                                                    
                                'gln_magasin': gln_magasin,
                                'comment': comment,
                                'ref_cde_cli_final': ref_cde_cli_final,
                                'no_cde_remplace': no_cde_remplace,
                                'no_ope_promo': no_ope_promo, 
                                'no_lig_erp_cli': no_lig_erp_cli,
                                'modif_type_reponse' : modif_type_reponse,
                                'line': nb_lig,
                            }  
                            au_moins_une_ligne = True             
                            res_lig.append(vals_lig)  
                '''
        
        #
        # on doit intégrer la dernière commande si on en a une
        #       
        if len(res_ent)>=1 and creat_ligne_sans_erreur:  #and au_moins_une_ligne:   Pas de ligne dans ce flux
            for entete in res_ent:
                res.append(entete)
            for param in res_par:
                res.append(param)
            for comment in res_com:
                res.append(comment)    
            for ligne in res_lig:
                res.append(ligne)     
            res_ent = []        
            res_par = [] 
            res_com = [] 
            res_lig = []

        #logger.info("=== res ======================================================================================")
        #logger.info(res)  
        #logger.info("==============================================================================================")                       

        #
        # On va reparcourir les éléments stockés pour envoyer les mails au destinataire de la fiche société.
        #
        envoi = False
        new_piece = False
        values_entete = []
        values_param = []
        values_comment = []
        values_lignes = []
        premier_passage = True
        piece_a_creer = False
        for lignes in res:
            type_ligne = lignes['type']
            if type_ligne == 'ENT':
                #
                # Entête de commande
                #
                if not new_piece:
                    values_param = []
                    values_comment = []
                    values_lignes = []                   
                    new_piece = True
                    if premier_passage:
                        piece_a_creer = lignes['no_cde']
                        premier_passage = False

                no_cde = lignes['no_cde']
                if new_piece and no_cde != piece_a_creer:
                    #
                    # On génére l'envoi du mail de la commande avec les données connues
                    # 
                    envoi = self.envoi_mail_changement_ordchg(values_entete,values_param,values_comment,values_lignes)
                    values_entete = []
                    values_param = []
                    values_comment = []
                    values_lignes = []
                    piece_a_creer = lignes['no_cde']
                    new_piece = True                        

                ccli_emet = lignes['no_client_emet']
                ccli_dest = lignes['no_client_dest']
                no_cde = lignes['no_cde']
                type_cde = lignes['type_cde']
                code_function = lignes['code_function']
                date_cde = lignes['date_cde']                                                    
                heure_cde = lignes['heure_cde']
                date_liv = lignes['date_liv']                                                   
                heure_liv = lignes['heure_liv']
                date_enlev = lignes['date_enlev']                                                   
                heure_enlev = lignes['heure_enlev']
                no_contrat = lignes['no_contrat']
                ref_cde_client = lignes['ref_cde_client']
                no_cde_rempl = lignes['no_cde_rempl']
                no_ope_promo = lignes['no_ope_promo']
                comment_cde = lignes['comment_cde']
                comment_speciaux = lignes['comment_speciaux']
                nb_lig = lignes['line']
                edi_emet = lignes['no_client_emet']
                edi_dest = lignes['no_client_dest']

                ccli_dest = ccli_dest.strip()
                partner_id = self.recherche_partenaire(ccli_dest)
                ccli_emet = ccli_emet.strip()
                partner_emet_id = self.recherche_partenaire(ccli_emet)
                type_cde = type_cde.strip()
                type_cde_id = self.recherche_type_commande(type_cde)
                code_function = code_function.strip()
                code_function_id = self.recherche_function_commande(code_function)

                date_order = self.conversion_en_datetime(date_cde,heure_cde)
                date_expected = self.conversion_en_datetime(date_liv,heure_liv)
                if date_enlev.strip():
                    date_enlevement = self.conversion_en_datetime(date_enlev,heure_enlev)
                else:
                    date_enlevement = False   

                if len(company_id.param_edi_id.name)>3:
                    type_param_edi = company_id.param_edi_id.name[:3]
                else:   
                    type_param_edi = company_id.param_edi_id.name

                if type_param_edi == "TX2":               
                    if type_cde == '230' and code_function == '1':
                        #
                        # On créé la commande
                        #
                        ref_cde_client = ref_cde_client.strip()
                        #if not ref_cde_client:
                        #    ref_cde_client = no_cde.strip()
                        
                        values_ent = {
                            'partner_id': partner_emet_id,
                            'commande_edi': True,
                            'partner_emet_id': partner_emet_id,
                            'date_order': date_order,
                            'commitment_date': date_order,
                            'date_devis_edi': date_order,
                            'expected_date': date_expected,
                            'date_enlev': date_enlevement,
                            'client_order_ref': ref_cde_client,
                            'no_cde_client': no_cde.strip(),
                            'no_contrat': no_contrat,
                            'no_cde_rempl': no_cde_rempl,
                            'no_ope_promo': no_ope_promo,
                            'code_function_id': code_function_id.id,
                            'partner_shipping_id': partner_emet_id,
                            'partner_invoice_id': partner_emet_id,
                            'partner_vendeur_id': partner_emet_id,
                            'partner_final_id': partner_emet_id,
                            'edi_emetteur': edi_emet,
                            'edi_destinataire': edi_dest,
                        }
                        values_entete.append(values_ent) 
                else: 
                    # On créé la commande
                    values_ent = {
                        'partner_id': partner_emet_id,
                        'commande_edi': True,
                        'partner_emet_id': partner_emet_id,
                        'date_order': date_order,
                        'commitment_date': date_order,
                        'date_devis_edi': date_order,
                        'expected_date': date_expected,
                        'date_enlev': date_enlevement,
                        'client_order_ref': ref_cde_client,
                        'no_cde_client': no_cde.strip(),                        
                        'no_contrat': no_contrat,
                        'no_cde_rempl': no_cde_rempl,
                        'no_ope_promo': no_ope_promo,
                        'code_function_id': code_function_id.id,
                        'partner_shipping_id': partner_emet_id,
                        'partner_invoice_id': partner_emet_id,
                        'partner_vendeur_id': partner_emet_id,
                        'partner_final_id': partner_emet_id,
                        'edi_emetteur': edi_emet,
                        'edi_destinataire': edi_dest,
                    }
                    values_entete.append(values_ent)  

            if type_ligne == 'PAR':
                #
                # Paramêtre de commande
                #
                type_interv = lignes['type_interv']
                code_interv = lignes['code_interv']
                ident_interv = lignes['ident_interv']
                nom_interv = lignes['nom_interv']
                adr1_interv = lignes['adr1_interv']
                adr2_interv = lignes['adr2_interv']
                adr3_interv = lignes['adr3_interv']
                cpos_interv = lignes['cpos_interv']
                vil_interv = lignes['vil_interv']
                pays_interv = lignes['pays_interv']
                ident_compl1 = lignes['ident_compl1']
                type_ident1 = lignes['type_ident1']
                ident_compl2 = lignes['ident_compl2']
                type_ident2 = lignes['type_ident2']
                ident_compl3 = lignes['ident_compl3']
                type_ident3 = lignes['type_ident3']
                ident_compl4 = lignes['ident_compl4']
                type_ident4 = lignes['type_ident4']
                nom_contact = lignes['nom_contact']
                tel_contact = lignes['tel_contact']
                mail_contact = lignes['mail_contact']
                nb_lig_par = lignes['line']
                no_cde_par = lignes['no_cde']

                type_interv = type_interv.strip()
                type_interv_id = self.recherche_type_intervenant(type_interv)
                code_interv = code_interv.strip()
                code_interv_id = self.recherche_partenaire(code_interv)  
                ident_interv = ident_interv.strip() 
                ident_interv_id = self.recherche_partenaire(ident_interv)   

                values_par = {
                    'type_interv_id': type_interv_id,
                    'code_interv_id': code_interv_id,
                    'ident_interv_id': ident_interv_id,
                    'nom_interv': nom_interv,
                    'adr1_interv': adr1_interv,
                    'adr2_interv': adr2_interv,
                    'adr3_interv': adr3_interv,
                    'cpos_interv': cpos_interv,
                    'vil_interv': vil_interv,
                    'pays_interv': pays_interv,
                    'ident_compl1': ident_compl1,
                    'type_ident1': type_ident1,
                    'ident_compl2': ident_compl2,
                    'type_ident2': type_ident2,
                    'ident_compl3': ident_compl3,
                    'type_ident3': type_ident3,
                    'ident_compl4': ident_compl4,
                    'type_ident4': type_ident4,
                    'nom_contact': nom_contact,
                    'tel_contact': tel_contact,
                    'mail_contact': mail_contact,
                    'nad_by_id': partner_emet_id,
                    'no_lig': nb_lig_par,
                    'no_cde': no_cde_par,
                    }   
                values_param.append(values_par)    

            if type_ligne == 'COM':
                #
                # Commentaire de commande
                #
                type  = lignes['type']
                comm1 = lignes['comm1']
                comm2 = lignes['comm2']
                comm3 = lignes['comm3']
                comm4 = lignes['comm4']
                comm5 = lignes['comm5']
                commentaire = comm1 + comm2 + comm3 + comm4 + comm5
                values_com = {
                    'type_comm': type,
                    'comment': commentaire,
                    }   
                values_comment.append(values_com)    

            '''
            if type_ligne == 'LIG':
                #
                # Ligne de commande
                #  
                no_ligne = lignes['no_ligne']
                ean = lignes['ean']
                code_art_vendeur = lignes['code_art_vendeur']
                code_art_acheteur = lignes['code_art_acheteur']
                qte_cde = self.conversion_en_flaot(lignes['qte_cde'])   
                unite_cde = lignes['unite_cde']
                qte_pcb = self.conversion_en_flaot(lignes['qte_pcb'])
                unite_pcb = lignes['unite_pcb']
                qte_gratuit = self.conversion_en_flaot(lignes['qte_gratuit'])
                unite_gratuit = lignes['unite_gratuit']
                desc_art = lignes['desc_art']
                pub = self.conversion_en_flaot(lignes['pub'])              
                pun = self.conversion_en_flaot(lignes['pun'])
                pvc = self.conversion_en_flaot(lignes['pvc'])
                mt_net_ligne = self.conversion_en_flaot(lignes['mt_net_ligne'])
                nb_ul = self.conversion_en_flaot(lignes['nb_ul'])
                type_emballage = lignes['type_emballage']
                ean_ul = lignes['ean_ul']
                date_liv = lignes['date_liv']
                heure_liv = lignes['heure_liv']
                no_cde_magasin = lignes['no_cde_magasin']
                gln_magasin = lignes['gln_magasin']
                comment = lignes['comment']
                ref_cde_cli_final = lignes['ref_cde_cli_final']
                no_cde_remplace = lignes['no_cde_remplace']
                no_ope_promo = lignes['no_ope_promo']
                no_lig_erp_cli = lignes['no_lig_erp_cli']
                modif_type_reponse = lignes['modif_type_reponse']               
                
                ean = ean.strip() 
                ean_id = self.recherche_ean_article(ean)
                unite_cde = unite_cde.strip() 
                unite_cde_id = self.recherche_unite(unite_cde,ean_id)
                unite_pcb = unite_pcb.strip() 
                unite_pcb_id = self.recherche_unite(unite_pcb,ean_id)
                unite_gratuit = unite_gratuit.strip() 
                unite_gratuit_id = self.recherche_unite(unite_gratuit,ean_id)
                ean_ul = ean_ul.strip() 
                ean_ul_id = self.recherche_ean_article(ean_ul)

                if date_liv.strip():
                    date_liv_edi = self.conversion_en_datetime(date_liv,heure_liv)
                else:
                    date_liv_edi = False    
                desc_art = desc_art.strip()
                values_lig = {
                    'product_id': ean_id,
                    'lig_commande_edi': True,
                    'code_art_vendeur': code_art_vendeur,
                    'code_art_acheteur': code_art_acheteur,
                    'product_uom_qty' : qte_cde, 
                    'product_uom': unite_cde_id, 
                    'qte_pcb': qte_pcb,
                    'unite_pcb': unite_pcb_id,
                    'qte_gratuit': qte_gratuit,
                    'unite_gratuit': unite_gratuit_id,
                    'name': desc_art,
                    'pub_edi': pub,
                    'pun_edi': pun,
                    'pvc_edi': pvc,
                    'mt_net_ligne_edi': mt_net_ligne,
                    'nb_ul_edi': nb_ul,
                    'type_emballage': type_emballage,
                    'ean_ul_edi': ean_ul_id,
                    'date_liv_edi': date_liv_edi,
                    'no_cde_magasin': no_cde_magasin,
                    'gln_magasin': gln_magasin,
                    'comment_edi': comment,
                    'ref_cde_cli_final': ref_cde_cli_final,
                    'no_cde_remplace': no_cde_remplace,
                    'no_ope_promo': no_ope_promo,
                    'no_lig_erp_cli': no_lig_erp_cli,
                    'modif_type_reponse_edi': modif_type_reponse, 
                    'no_ligne_edi': no_ligne,            
                }

                values_lignes.append(values_lig)
                '''

        if new_piece:
            #
            # On génére la commande avec les données connues
            # 
            envoi = self.envoi_mail_changement_ordchg(values_entete,values_param,values_comment,values_lignes)
                   
        # 
        # Le traitement est terminé, on ne retourne rien
        # 
        return False  

    #########################################################################################
    #                                                                                       #
    #                            Envoi mail destinataire du changement                      #
    #                                                                                       #
    #########################################################################################
    def envoi_mail_changement_ordchg(self,values_entete,values_param,values_comment,values_lignes):
        sale_obj = self.env['sale.order']
        sale_line_obj = self.env['sale.order.line']
        sale = False
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company      

        commentaire_changement = ''
        if values_entete:
            for values_ent in values_entete:
                controle_cde = self.controle_commande_presente_dans_odoo(values_ent, values_param)
                if controle_cde:
                    controle_client_edi = self.controle_gestion_ordchg_edi_partner(values_ent)
                    if controle_client_edi:
                        if values_comment:
                            commentaire = ''
                            for values_com in values_comment:
                                commentaire_changement += values_com['comment'] 
                                commentaire_changement += ' '
                                values_ent.update({
                                    'comment_edi': commentaire_changement,
                                    })
                                
                        #
                        # On prend en compte les partenaires des segments PARAM
                        #  
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
                        partner_acheteur = False
                        if values_param:
                           for values_par in values_param: 
                                type_intervention = values_par['type_interv_id']
                                if type_intervention.name == company_id.par_by_id.name:
                                    ccli_acheteur = values_par['code_interv_id']
                                    partner_acheteur = self.recherche_partner(ccli_acheteur)
                                    if partner_acheteur:
                                        values_ent.update({
                                            'partner_id': partner_acheteur,
                                            'partner_acheteur_id': partner_acheteur,
                                            }) 

                                if type_intervention.name == 'DP':
                                    ccli_livre_a = values_par['code_interv_id']
                                    partner_livre_a = self.recherche_partner(ccli_livre_a)
                                    if partner_livre_a:
                                        values_ent.update({
                                            'partner_shipping_id': partner_livre_a,
                                            'partner_livre_a_id': partner_livre_a,
                                            })  
                                if type_intervention.name == 'IV':
                                    ccli_facture_a = values_par['code_interv_id']
                                    partner_facture_a = self.recherche_partner(ccli_facture_a)
                                    if partner_facture_a:
                                        values_ent.update({
                                            'partner_invoice_id': partner_facture_a,
                                            'partner_facture_a_id': partner_facture_a,
                                            })   
                                if type_intervention.name == 'SU':
                                    ccli_vendeur = values_par['code_interv_id']
                                    partner_vendeur = self.recherche_partner(ccli_vendeur)
                                    if partner_vendeur:
                                        values_ent.update({
                                            'partner_vendeur_id': partner_vendeur,
                                            })

                                if type_intervention.name == 'OB':
                                    ccli_commande_par = values_par['code_interv_id']
                                    partner_commande_par = self.recherche_partner(ccli_commande_par)
                                    if partner_commande_par:
                                        values_ent.update({
                                            'partner_id': partner_commande_par,
                                            'partner_commande_par_id': partner_commande_par,
                                            }) 
                                if type_intervention.name == 'PR':
                                    ccli_paye_par = values_par['code_interv_id']
                                    partner_paye_par = self.recherche_partner(ccli_paye_par)
                                    if partner_paye_par:
                                        values_ent.update({
                                            'partner_paye_par_id': partner_paye_par,
                                            })  

                                if type_intervention.name == company_id.par_uc_id.name:
                                    ccli_final = values_par['code_interv_id']
                                    if ccli_final:
                                        ccli_final = ccli_final.strip()
                                        partner_final = self.recherche_partner(ccli_final)
                                        if partner_final:
                                            values_ent.update({
                                                'partner_final_id': partner_final,
                                                })
                                    else:
                                        #
                                        # Pas de GLN dans le PAR+UC, on créé une adresse client liés au NAD+BY
                                        #    
                                        nad_by_id = values_par['nad_by_id']
                                        nom_interv = values_par['nom_interv']
                                        adr1_interv = values_par['adr1_interv']
                                        adr2_interv = values_par['adr2_interv']
                                        cpos_interv = values_par['cpos_interv']
                                        vil_interv = values_par['vil_interv']
                                        pays_interv = values_par['pays_interv']
                                        tel_contact = values_par['tel_contact']
                                        mail_contact = values_par['mail_contact']
                                        no_lig_par = values_par['no_lig']
                                        no_cde_par = values_par['no_cde']

                                        values_adresse_uc = {
                                                'type_adresse' : 'other',
                                                'partner_id' : partner_acheteur,
                                                'nom' : nom_interv,                
                                                'rue1' : adr1_interv,               
                                                'rue2' : adr2_interv,               
                                                'cp' : cpos_interv,                 
                                                'ville' : vil_interv,             
                                                'pays' : pays_interv,                
                                                'email' : mail_contact,              
                                                'tel' : tel_contact,       
                                            }

                                        new_partner_ok = self.creation_adresse_client_final(values_adresse_uc)
                                        if not new_partner_ok:
                                            sujet = str(self.env.company.name) + ' - Gestion EDI - Changement sur commandes client du ' + str(today) 
                                            corps = "Erreur lors de la création de l'adresse du client final de la ligne {}. <br/><br>".format(nb_lig_par) 
                                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde_par)                         
                                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                                            if not flux:
                                                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1) 
                                            if flux.envoi_auto_mail:   
                                                destinataire = company_id.gestion_user_id.email
                                                if destinataire:
                                                    self.edi_generation_mail(destinataire, sujet, corps)

                                            code_erreur = self.env['erreur.edi'].search([('name','=', '0013')], limit=1) 

                                            message = "Erreur lors de la création de l'adresse du client final de la ligne {}. ".format(nb_lig_par) 
                                            message+= "La pièce {} a été rejetée.".format(no_cde_par)  
                                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                                        else:
                                            values_ent.update({
                                                'partner_final_id': new_partner_ok.id,
                                                })                                   

                        #
                        # On envoie un mail sur la commande créée et on met à jour le suivi EDI
                        #  
                        
                        ref_cde = values_ent['client_order_ref'].strip()
                       
                        cde_vte = sale_obj.search([('partner_id','=', partner_acheteur),('client_order_ref','=',ref_cde)],limit=1)
                        if cde_vte:                                    
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Changement sur commandes client du ' + str(today) 
                            corps = "La commande {} pour le client {} a été modifiée. <br/><br>".format(cde_vte.name,cde_vte.partner_id.name) 
                            corps+= "Le numéro de commande EDI est {}. <br/><br>".format(cde_vte.client_order_ref)  
                            corps+= "La raison du changement est : <br> {}. <br/><br>".format(commentaire_changement)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                            if not flux:
                                flux = self.env['flux.edi'].search([('name','=', 'ORDCHG')], limit=1) 
                            if flux.envoi_auto_mail:   
                                destinataire = company_id.email_ordchg
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)

                            code_erreur = self.env['erreur.edi'].search([('name','=', '0900')], limit=1) 

                            message = "La commande {} pour le client {} a été modifiée. ".format(cde_vte.name,cde_vte.partner_id.name) 
                            message+= "Le numéro de commande EDI est {}.".format(cde_vte.client_order_ref)
                            message+= "La raison du changement est {}.".format(commentaire_changement)   
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)
                           
        return True       

    #########################################################################################
    #                                                                                       #
    #                      Controle existence commande pour le partner                      #
    #                                                                                       #
    #########################################################################################
    def controle_commande_presente_dans_odoo(self,values_ent,values_param):
        sale_obj = self.env['sale.order']
        partner_obj = self.env['res.partner']
        commande_existante = False
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company 

        partner_id = values_ent['partner_id']
        ref_cde = values_ent['client_order_ref'].strip()

        if values_param:
            for values_par in values_param: 
                type_intervention = values_par['type_interv_id']
                if type_intervention.name == 'BY':
                    ccli_acheteur = values_par['code_interv_id']
                    partner_acheteur = self.recherche_partner(ccli_acheteur)
                    if partner_acheteur:
                        partner_id = partner_acheteur

        cde_vte = sale_obj.search([('partner_id','=', partner_id),('client_order_ref','=',ref_cde)],limit=1)
        if cde_vte:
            commande_existante = True
        else:
            commande_existante = False    
            client = partner_obj.search([('id','=', partner_id)],limit=1)
            #
            # Erreur sur commande inexistante dans la base de données Odoo
            #
            sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
            corps = "La commande avec la référence {} n'existe pas pour le client {}. <br/><br>".format(ref_cde, client.name) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

            flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
            if not flux:
                flux = self.env['flux.edi'].search([('name','=', 'ORDCHG')], limit=1) 
            if flux.envoi_auto_mail:   
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.edi_generation_mail(destinataire, sujet, corps)

            code_erreur = self.env['erreur.edi'].search([('name','=', '0901')], limit=1) 

            message = "La commande avec la référence {} n'existe pas pour le client {}. ".format(ref_cde, client.name)
            self.edi_generation_erreur(code_erreur, flux, sujet, message)

        return commande_existante

    #########################################################################################
    #                                                                                       #
    #              Controle gestion des changement de commandes EDI du client               #
    #                                                                                       #
    #########################################################################################
    def controle_gestion_ordchg_edi_partner(self,values_ent):
        partner_obj = self.env['res.partner']
        client_edi = False
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company 

        partner_id = values_ent['partner_id']
        ref_cde = values_ent['client_order_ref'].strip()

        client = partner_obj.search([('id','=', partner_id)],limit=1)

        if client:
            if client.client_edi:
                if client.edi_order:
                    client_edi = True
                else:
                    #
                    # Le client n'est pas en gestion EDI
                    #
                    sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                    corps = "La gestion des changements de commandes EDI n'est pas autorisée pour le client {}. <br/><br>".format(client.name) 
                    corps+= "La commande {} n'est pas créée. <br/><br>".format(ref_cde)                         
                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                    flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                    if not flux:
                        flux = self.env['flux.edi'].search([('name','=', 'ORDCHG')], limit=1) 
                    if flux.envoi_auto_mail:   
                        destinataire = company_id.gestion_user_id.email
                        if destinataire:
                            self.edi_generation_mail(destinataire, sujet, corps)

                    code_erreur = self.env['erreur.edi'].search([('name','=', '0902')], limit=1) 

                    message = "La gestion des changement de commandes EDI n'est pas autorisée pour le client {}. ".format(client.name) 
                    message+= "La commande {} n'est pas créée. ".format(ref_cde)    
                    self.edi_generation_erreur(code_erreur, flux, sujet, message)   
            else:    
                #
                # Le client n'est pas en gestion EDI
                #
                sujet = str(self.env.company.name) + ' - Gestion EDI - Changement de commandes client du ' + str(today) 
                corps = "Le client {} n'est pas géré en EDI. <br/><br>".format(client.name) 
                corps+= "La commande {} n'est pas créée. <br/><br>".format(ref_cde)                         
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
               
                flux = self.env['flux.edi'].search([('name','=', self.type_fichier)], limit=1)
                if not flux:
                    flux = self.env['flux.edi'].search([('name','=', 'ORDCHG')], limit=1) 
                if flux.envoi_auto_mail:   
                    destinataire = company_id.gestion_user_id.email
                    if destinataire:
                        self.edi_generation_mail(destinataire, sujet, corps)

                code_erreur = self.env['erreur.edi'].search([('name','=', '0400')], limit=1) 

                message = "Le client {} n'est pas géré en EDI. ".format(client.name) 
                message+= "La commande {} n'est pas créée. ".format(ref_cde)    
                self.edi_generation_erreur(code_erreur, flux, sujet, message)

        return client_edi        