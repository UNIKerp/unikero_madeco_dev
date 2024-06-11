# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime, timedelta
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

class CommandePrestaImport(models.TransientModel):
    _name = "commande.presta.import"
    _description = "Import des commandes PrestaShop"
    
    file_to_import = fields.Binary(
        string='Fichier à importer', required=True,
        help="Fichier contenant les commandes PrestaShop à importer.")
    filename = fields.Char()
    file_format = fields.Selection([
        ('presta_csv', 'PrestaShop'),
        ], string='Format du fichier', required=True, default="presta_csv")
    file_encoding = fields.Selection([
        ('ascii', 'ASCII'),
        ('latin1', 'ISO 8859-15 (alias Latin1)'),
        ('utf-8', 'UTF-8'),
        ], string='Type Encodage du fichier', default='latin1')
    presta_txt_field_separator = fields.Selection([('aucun','pas de séparateur'),
        ('pipe', '| (pipe)'),
        ('tab', 'Tabulation'),
        (';','Point-Virgule'),
        (',','Virgule')
        ], string='Séparateur de champ', default=';')
    import_auto = fields.Boolean("Import automatique par FTP", default=True, required=True)
    type_fichier = fields.Char("Type de fichier import", required=False)
    ext_fichier = fields.Char("Extension de fichier import", required=False)   
   
    #########################################################################################
    #                                                                                       #
    #                                   Traitement du fichier                               #
    #                                                                                       #
    #########################################################################################     
    def file2import_presta(self, fileobj, file_bytes, fichier_import):
        file_format = self.file_format
        if file_format == 'presta_csv':
            return self.presta_import_cde_prestashop(file_bytes,fichier_import)
        else:
            raise UserError(_("Vous devvez sélectionner un fichier au format PrestaShop."))

    #########################################################################################
    #                                                                                       #
    #                   Import des commandes PrestaShop autoamtique                         #
    #                                                                                       #
    #########################################################################################                  
    @api.model
    def import_cde_presta_automatique(self):
        wizard_values = {
            'import_auto': True,
            'file_format': 'presta_csv',
            'presta_txt_field_separator': ';'
        }
        wizard = self.create(wizard_values)        

        logger.info("===============================================")
        logger.info("    Début intégration automatique PrestaShop   ")
        logger.info("===============================================")           
        wizard.run_import_cde_presta()
        logger.info("===============================================")
        logger.info("     Fin intégration automatique PrestaShop    ")
        logger.info("===============================================")

    #########################################################################################
    #                                                                                       #
    #                           Bouton import des commandes PrestaShop                      #
    #                                                                                       #
    #########################################################################################                  
    def run_import_cde_presta(self):
        self.ensure_one()

        logger.info("_________________")
        logger.info(self.import_auto)   
        logger.info(self.file_format) 
        logger.info(self.presta_txt_field_separator)     
        logger.info("_________________")

        company_id =  self.env.company 

        logger.info("_________________")
        logger.info(company_id.name)
        logger.info(company_id.param_presta_id.id)
        logger.info(company_id.param_presta_id.name)
        logger.info("_________________")
        
        today = fields.Date.to_string(datetime.now()) 
        logger.info("*****************************************************")
        logger.info("*  lancement de l'import des commandes PrestaShop   *")
        logger.info(self.env.company.name)
        logger.info("*****************************************************")

        sujet = str(self.env.company.name) + ' - Lancement Intégration Commandes PrestaShop : ' + str(today)        
        code_erreur = self.env['erreur.presta'].search([('name','=', '9000')], limit=1) 
        message = "Le traitement de l'intégration des commandes PrestaShop a été lancé sur la société {} . ".format(str(self.env.company.name) )  
        self.presta_generation_erreur(code_erreur, sujet, message)    

        if self.import_auto:
            param = self.env['parametre.presta'].search([('id', '=', company_id.param_presta_id.id)])

            #logger.info(param)

            if len(param)>0:  
                if param.type_connexion == 'ftp':
                    #
                    # Connexion FTP 
                    #  
                    ftp_user = param.compte_ftp_presta.strip()
                    ftp_password = param.mdp_presta.strip()
                    adresse_ftp = param.adresse_ftp.strip()
                    ftp_port = param.port_ftp
                    rep_recup_ftp = param.repertoire_recup_cde_presta.strip()
                                            
                    rep_import = param.rep_import_interne_presta.strip()
                    if not rep_import:
                        rep_import = '/tmp'
                    
                    fich_path = rep_import
                    fichier_import = '*.csv'
                    
                    fich_presta = fich_path + '/%s' % fichier_import

                    ftp = ftplib.FTP() 
                    ftp.connect(adresse_ftp, ftp_port, 30*5) 
                    ftp.login(ftp_user, ftp_password)             
                    passif=True
                    ftp.set_pasv(passif)
                    ftp.cwd(rep_recup_ftp)
                    fich_copie = os.path.basename(fich_presta)
                                
                    filenames = ftp.nlst()

                    logger.info("liste des fichiers PrestaShop")
                    logger.info(filenames)
                    logger.info(rep_recup_ftp)
                    logger.info(fich_presta)

                    for filename in filenames:                        
                        lg_fichier = len(filename)

                        if lg_fichier <= 4:
                            continue    
                        ext_fichier = filename[lg_fichier-3:lg_fichier]

                        if ext_fichier != 'csv':
                            continue
                        else:  
                            fileobj = TemporaryFile('wb+')
                            fich_integ_presta = fich_path + '/%s' % filename
                            fichier_import = filename
                                
                            fich_copie = os.path.basename(fich_integ_presta)

                            fichier_cde_presta = open(fich_integ_presta, "wb")     

                            with fichier_cde_presta as f:
                                ftp.retrbinary('RETR ' + fichier_import, f.write)                
                            fichier_donnees_presta = os.path.basename(fich_integ_presta)    
                            with open(fich_integ_presta, "rb") as fileread:
                                byte_data = fileread.read()
                            file_bytes = byte_data
                            fileobj.write(file_bytes)
                            fileobj.seek(0)  # We must start reading from the beginning !

                            logger.info("_______________ Import FTP ______________________")
                            #logger.info(fileobj.filename)
                            logger.info(file_bytes)
                            logger.info(fichier_import)

                            lignes = self.file2import_presta(fileobj, file_bytes, fichier_import)
                            fileobj.close()

                            logger.info("_________________________________________________")
                            logger.info(lignes)
                            logger.info("_________________________________________________")
                            
                            if lignes:
                                moves = self.create_commande_presta_from_import_presta(lignes)
                            else:
                                moves = False    

                            
                            logger.info("_________________________________________________")
                            logger.info("On met à jour la base de données")
                            logger.info("_________________________________________________")
                            self.env.cr.commit()
                            #
                            # On supprime le fichier sur le serveur FTP
                            #
                            ftp.delete(filename)

                            logger.info("_________________________________________________")
                            logger.info("On supprime le fichier sur le serveur FTP")
                            logger.info(filename)
                            logger.info("_________________________________________________")                            

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
                    sftp_user = param.compte_ftp_presta.strip()
                    sftp_password = param.mdp_presta.strip()
                    sftp_url = param.adresse_ftp.strip()
                    sftp_port = param.port_ftp
                    rep_recup_sftp = param.repertoire_recup_cde_presta.strip()
                                            
                    rep_import = param.rep_import_interne_presta.strip()
                    if not rep_import:
                        rep_import = '/tmp'
                    
                    fich_path = rep_import
                    fichier_import = '*.csv'
                    
                    fich_presta = fich_path + '/%s' % fichier_import

                    with pysftp.Connection(host=sftp_url,username=sftp_user,password=sftp_password,port=int(sftp_port),cnopts=cnopts) as sftp:
                        # on ouvre le dossier images
                        sftp.chdir(rep_recup_sftp)
                        # liste des fichiers 
                        filenames = sftp.listdir()
                        for filename in filenames:                               

                            fileobj = TemporaryFile('wb+')
                            fich_integ_presta = fich_path + '/%s' % filename
                            fichier_import = filename

                            fich_copie = os.path.basename(fich_integ_presta)  

                            fichier_import = os.path.basename(fich_integ_presta) 

                            sftp.get(fichier_import,fich_integ_presta)

                            with open(fich_integ_presta, "rb") as f:
                                byte_data = f.read()

                            file_bytes = byte_data
                            fileobj.write(file_bytes)

                            fileobj.seek(0)  # We must start reading from the beginning !

                            logger.info("_______________ Import SFTP _____________________")
                            #logger.info(fileobj.filename)
                            logger.info(file_bytes)
                            logger.info(fichier_import)

                            lignes = self.file2import_presta(fileobj, file_bytes, fichier_import)
                            fileobj.close()  

                            logger.info("_________________________________________________")
                            logger.info(lignes)
                            logger.info("_________________________________________________")
                            
                            if lignes:
                                moves = self.create_commande_presta_from_import_presta(lignes)
                            else:
                                moves = False  

                            logger.info("_________________________________________________")
                            logger.info("On met à jour la base de données")
                            logger.info("_________________________________________________")
                            self.env.cr.commit()   

                            #
                            # On supprime le fichier sur le serveur SFTP
                            #
                            sftp.delete(filename)

                            logger.info("_________________________________________________")
                            logger.info("On supprime le fichier sur le serveur SFTP")
                            logger.info(filename)
                            logger.info("_________________________________________________")


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

                        sftp.quit()                
        else:
            fileobj = TemporaryFile('wb+')

            file_bytes = base64.b64decode(self.file_to_import)
            fileobj.write(file_bytes)
            fileobj.seek(0)  # We must start reading from the beginning !
            lignes = self.file2import_presta(fileobj, file_bytes, self.filename)
            fileobj.close()
            if lignes:
                moves = self.create_commande_presta_from_import_presta(lignes)
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

        logger.info("*****************************************************")
        logger.info("*     Fin de l'import des commandes PrestaShop      *")
        logger.info(self.env.company.name)
        logger.info("*****************************************************")

        sujet = str(self.env.company.name) + " - Fin de l'intégration Commandes PrestaShop : " + str(today)        
        code_erreur = self.env['erreur.presta'].search([('name','=', '9000')], limit=1) 
        message = "Le traitement de l'intégration des commandes PrestaShop est terminé sur la société {} . ".format(str(self.env.company.name) )  
        self.presta_generation_erreur(code_erreur, sujet, message)                      
            
    #########################################################################################
    #                                                                                       #
    #      On lit le fichier et on génère une liste de données pour les commandes TX2       #
    #                                                                                       #
    #########################################################################################    
    def presta_import_cde_prestashop(self, file_bytes, file_name):
        company_id =  self.env.company 
        nb_lig = 0
        res = []
        file_str = file_bytes.decode(self.file_encoding)
        today = fields.Date.to_string(datetime.now())

        self.type_fichier = file_name[0:10]

        lg_fichier = len(file_name)

        self.ext_fichier = file_name[lg_fichier-3:lg_fichier]

        if self.type_fichier not in ('import_web') and self.ext_fichier not in ('csv'):
            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
            corps = "Le type de fichier est incorrect. Il doit être de type 'csv'. <br/><br>" 
            corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.presta_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.presta'].search([('name','=', '9003')], limit=1) 
            message = "Le type de fichier est incorrect. Il doit être de type 'csv'. "
            message+= "Le fichier {} a été rejeté. ".format(file_name)  
            self.presta_generation_erreur(code_erreur, sujet, message)   
            return res  

        for l in file_str.split('\n'):
            l = l.replace('"', '')    
            nb_lig += 1
            if len(l) < 4 :
                continue
            
            if l[0:13] == 'Date commande':
                continue 

            if l[0] != '':
                creat_cde = False

                lgueur = len(l)
                cpt = 0
                debut = 0
                nb_champ = 0
                debut = 0
                tab_champ = {}

                while cpt < lgueur:
                    if l[cpt] == self.presta_txt_field_separator: 
                        nb_champ += 1
                        nom_champ = "champ" + str(nb_champ)
                        valeur_champ = l[debut:cpt]

                        debut = cpt+1
                        tab_champ[nom_champ]= valeur_champ                        

                    cpt+=1    

                #
                # On récupère la valeur du dernier champ qui n'a pas de séparateur de fin
                #
                if debut > 0:
                    nb_champ += 1
                    nom_champ = "champ" + str(nb_champ) 
                    valeur_champ = l[debut:]
                    tab_champ[nom_champ]= valeur_champ 

                #logger.info("====== nb champ =====")
                #logger.info(nb_champ)
                #logger.info("=====================")    

                if nb_champ != 29:
                    #
                    # Erreur sur l'enregistrement
                    #
                    sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                    corps = "La structure de l'enregistrement est incorrect à la ligne {}. <br/><br>".format(nb_lig) 
                    corps+= "Le fichier {} a été rejeté. <br/><br>".format(file_name)                         
                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                    destinataire = company_id.gestion_user_id.email
                    if destinataire:
                        self.presta_generation_mail(destinataire, sujet, corps)
                    code_erreur = self.env['erreur.presta'].search([('name','=', '9001')], limit=1) 
                    message = "La structure de l'enregistrement est incorrect à la ligne {}. ".format(nb_lig)
                    message+= "Le fichier {} a été rejeté. ".format(file_name)  
                    self.presta_generation_erreur(code_erreur, sujet, message)
                    res = []
                    return res
                    #break
                else:
                    if tab_champ: 
                        date_commande_web       = tab_champ['champ1'] 
                        plateforme_web          = tab_champ['champ2']
                        id_prestashop_livr      = tab_champ['champ3']
                        nom_livr                = tab_champ['champ4']
                        rue1_livr               = tab_champ['champ5']
                        rue2_livr               = tab_champ['champ6']
                        cp_livr                 = tab_champ['champ7']
                        ville_livr              = tab_champ['champ8']
                        pay_livr                = tab_champ['champ9']
                        email_livr              = tab_champ['champ10']
                        tel_livr                = tab_champ['champ11']
                        id_prestashop_fact      = tab_champ['champ12']
                        nom_fact                = tab_champ['champ13']
                        rue1_fact               = tab_champ['champ14']
                        rue2_fact               = tab_champ['champ15']
                        cp_fact                 = tab_champ['champ16']
                        ville_fact              = tab_champ['champ17']
                        pay_fact                = tab_champ['champ18']
                        email_fact              = tab_champ['champ19']
                        tel_fact                = tab_champ['champ20']
                        no_cde_presta           = tab_champ['champ21']
                        ref_article             = tab_champ['champ22']
                        designation             = tab_champ['champ23']
                        quantite                = tab_champ['champ24']
                        pu_net                  = tab_champ['champ25']
                        mode_payment            = tab_champ['champ26']
                        mtt_paye                = tab_champ['champ27']
                        mode_transport          = tab_champ['champ28']
                        info_livraison          = tab_champ['champ29']

                        plateforme_ok = True
                        ctrl_plateforme = self.controle_plateforme(plateforme_web.strip())
                        if ctrl_plateforme:
                            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                            corps = "La plateforme WEB {} est inconnue à la ligne {}. <br/><br>".format(plateforme_web,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde_presta)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.presta_generation_mail(destinataire, sujet, corps)
                            code_erreur = self.env['erreur.presta'].search([('name','=', '0001')], limit=1) 
                            message = "{} - La plateforme WEB {} est inconnue à la ligne {}. ".format(self.env.company.name,plateforme_web,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde_presta) 
                            self.presta_generation_erreur(code_erreur, sujet, message)
                            plateforme_ok = False
                            continue 

                        ctrl_pays_livr = self.controle_pays(pay_livr.strip())
                        if ctrl_pays_livr:
                            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                            corps = "Le pays de livraison {} est inconnu à la ligne {}. <br/><br>".format(pay_livr,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde_presta)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.presta_generation_mail(destinataire, sujet, corps)
                            code_erreur = self.env['erreur.presta'].search([('name','=', '0009')], limit=1) 
                            message = "{} - Le pays de livraison {} est inconnu à la ligne {}. ".format(self.env.company.name,pay_livr,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde_presta) 
                            self.presta_generation_erreur(code_erreur, sujet, message)
                            plateforme_ok = False 
                            continue 

                        ctrl_pays_fact = self.controle_pays(pay_fact.strip())
                        if ctrl_pays_fact:
                            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                            corps = "{} - Le pays de facturation {} est inconnu à la ligne {}. <br/><br>".format(pay_fact,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde_presta)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.presta_generation_mail(destinataire, sujet, corps)
                            code_erreur = self.env['erreur.presta'].search([('name','=', '0009')], limit=1) 
                            message = "{} - Le pays de facturation {} est inconnu à la ligne {}. ".format(self.env.company.name,pay_fact,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde_presta) 
                            self.presta_generation_erreur(code_erreur, sujet, message)
                            plateforme_ok = False
                            continue 


                        ctrl_paiement = self.controle_paiement(mode_payment.strip(),self.env.company.id)    
                        if ctrl_paiement:
                            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                            corps = "Le mode de paiement de la commande {} est inconnue à la ligne {}. <br/><br>".format(mode_payment,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde_presta)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.presta_generation_mail(destinataire, sujet, corps)
                            code_erreur = self.env['erreur.presta'].search([('name','=', '0007')], limit=1) 
                            message = "{} - Le mode de paiement de la commande {} est inconnue à la ligne {}. ".format(self.env.company.name,mode_payment,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde_presta) 
                            self.presta_generation_erreur(code_erreur, sujet, message)
                            plateforme_ok = False
                            continue

                        #mode_transport = self.recadrage_mode_transport_web(mode_transport.strip())         
                        ctrl_mode_transport = self.controle_mode_transport(mode_transport.strip(),self.env.company.id)   
                        if ctrl_mode_transport:
                            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                            corps = "Le mode de transport de la commande {} est inconnu à la ligne {}. <br/><br>".format(mode_transport,nb_lig) 
                            corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde_presta)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.presta_generation_mail(destinataire, sujet, corps)
                            code_erreur = self.env['erreur.presta'].search([('name','=', '0008')], limit=1) 
                            message = "{} - Le mode de transport de la commande {} est inconnu à la ligne {}. ".format(self.env.company.name,mode_transport,nb_lig) 
                            message+= "La pièce {} a été rejetée. ".format(no_cde_presta) 
                            self.presta_generation_erreur(code_erreur, sujet, message)
                            plateforme_ok = False
                            continue

                        ctrl_ean_article = self.controle_ref_article(ref_article.strip())    
                        if ctrl_ean_article:
                            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                            corps = "L'article de la commande {} est inconnu à la ligne {}. <br/><br>".format(ref_article,nb_lig) 
                            corps+= "La ligne {} a été rejetée de la commande {}. <br/><br>".format(nb_lig,no_cde_presta)                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.presta_generation_mail(destinataire, sujet, corps)
                            code_erreur = self.env['erreur.presta'].search([('name','=', '0010')], limit=1) 
                            message = "{} - L'article de la commande {} est inconnu à la ligne {}.".format(self.env.company.name,ref_article,nb_lig) 
                            message+= "La ligne {} a été rejetée de la commande {}. ".format(nb_lig,no_cde_presta)   
                            self.presta_generation_erreur(code_erreur, sujet, message)
                            creat_lig = False
                            #plateforme_ok = False
                            #continue
                        else:
                            creat_lig = True     

                        if plateforme_ok:
                            ctrl_id_prestashop_livr = self.controle_partenaire(plateforme_web,id_prestashop_livr)
                            if ctrl_id_prestashop_livr:
                                #
                                # On créé une adresse de livraison 
                                #
                                adresse_livr = {
                                    'type_adresse' : 'livraison',
                                    'date_commande_web': date_commande_web,
                                    'partner_id' : plateforme_web,
                                    'adresse_id' : id_prestashop_livr,
                                    'nom' : nom_livr,                
                                    'rue1' : rue1_livr,               
                                    'rue2' : rue2_livr,               
                                    'cp' : cp_livr,                 
                                    'ville' : ville_livr,             
                                    'pays' : pay_livr,                
                                    'email' : email_livr,              
                                    'tel' : tel_livr,       
                                }
                                creation_ok = self.creation_adresse_livraison_facturation(adresse_livr)
                                if not creation_ok:
                                    sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                                    corps = "Erreur lors de la création de l'adresse de livraison de la ligne {}. <br/><br>".format(ctrl_plateforme,nb_lig) 
                                    corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde_presta)                         
                                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                                    destinataire = company_id.gestion_user_id.email
                                    if destinataire:
                                        self.presta_generation_mail(destinataire, sujet, corps)
                                    code_erreur = self.env['erreur.presta'].search([('name','=', '0001')], limit=1) 
                                    message = "Erreur lors de la création de l'adresse de livraison de la ligne {}. ".format(ctrl_plateforme,nb_lig) 
                                    message+= "La pièce {} a été rejetée. ".format(no_cde_presta) 
                                    self.presta_generation_erreur(code_erreur, sujet, message)
                                    plateforme_ok = False

                        if plateforme_ok:
                            ctrl_id_prestashop_fact = self.controle_partenaire(plateforme_web,id_prestashop_fact)
                            if ctrl_id_prestashop_fact:
                                #
                                # On créé une adresse de facturation 
                                #
                                adresse_fact = {
                                    'type_adresse' : 'facturation',
                                    'partner_id' : plateforme_web,
                                    'adresse_id' : id_prestashop_fact,
                                    'nom' : nom_fact,                
                                    'rue1' : rue1_fact,               
                                    'rue2' : rue2_fact,               
                                    'cp' : cp_fact,                 
                                    'ville' : ville_fact,             
                                    'pays' : pay_fact,                
                                    'email' : email_fact,              
                                    'tel' : tel_fact,       
                                }
                                creation_ok = self.creation_adresse_livraison_facturation(adresse_fact)
                                if not creation_ok:
                                    sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                                    corps = "Erreur lors de la création de l'adresse de facturation de la ligne {}. <br/><br>".format(ctrl_plateforme,nb_lig) 
                                    corps+= "La pièce {} a été rejetée. <br/><br>".format(no_cde_presta)                         
                                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                                    destinataire = company_id.gestion_user_id.email
                                    if destinataire:
                                        self.presta_generation_mail(destinataire, sujet, corps)
                                    code_erreur = self.env['erreur.presta'].search([('name','=', '0001')], limit=1) 
                                    message = "Erreur lors de la création de l'adresse de facturation de la ligne {}. ".format(ctrl_plateforme,nb_lig) 
                                    message+= "La pièce {} a été rejetée. ".format(no_cde_presta) 
                                    self.presta_generation_erreur(code_erreur, sujet, message)
                                    plateforme_ok = False        

                        # On est arrivé ICI dans le développement   
                        if plateforme_ok:
                            vals_ent = {
                                'type': 'ENT',
                                'date_commande_web': date_commande_web,
                                'plateforme_web': plateforme_web,
                                'id_livraison' : id_prestashop_livr,
                                'id_facturation' : id_prestashop_fact,
                                'no_cde_presta': no_cde_presta,
                                'date_cde': today,                                                    
                                'date_liv': today,                                                    
                                'mode_payment': mode_payment,
                                'mtt_paye': mtt_paye,
                                'mode_transport': mode_transport, 
                                'info_livraison': info_livraison,
                                'line': nb_lig,
                            }               
                            res.append(vals_ent)
               
                            #if creat_lig:
                            vals_lig = {
                                'type': 'LIG',
                                'ref_article': ref_article,
                                'quantite': quantite,
                                'designation': designation,
                                'pu_net': pu_net,                                    
                                'line': nb_lig,
                                'lig_ok': creat_lig,
                            }   
                            res.append(vals_lig)    
                
        return res

    #########################################################################################
    #                                                                                       #
    #        A partir de la liste de données, on créé la ou les commandes client            #
    #                                                                                       #
    #########################################################################################
    def create_commande_presta_from_import_presta(self, lignes_import):
        company_id =  self.env.company 
        nb_pasmaj   = 0
        nb_maj      = 0
        nb_cree     = 0 

        sale = False
        new_piece = False
        values_entete = []
        values_lignes = []
        premier_passage = True
        piece_a_creer = False
        ligne_en_erreur = False
        
        for lignes in lignes_import:
            type_ligne = lignes['type']
            if type_ligne == 'ENT':
                #
                # Entête de commande
                #
                if not new_piece:
                    values_lignes = []                   
                    new_piece = True
                    if premier_passage:
                        piece_a_creer = lignes['no_cde_presta']
                        premier_passage = False

                no_cde_presta = lignes['no_cde_presta']
                if new_piece and no_cde_presta != piece_a_creer:
                    #
                    # On génére la commande avec les données connues
                    # 
                    if ligne_en_erreur == False:
                        sale = self.genere_commande_vente(values_entete, values_lignes)
                    values_entete = []
                    values_lignes = []
                    piece_a_creer = lignes['no_cde_presta']
                    new_piece = True   
                    ligne_en_erreur = False                     

                date_commande_web = lignes['date_commande_web']
                plateforme_web = lignes['plateforme_web']
                id_livraison = lignes['id_livraison']
                id_facturation = lignes['id_facturation']
                no_cde_presta = lignes['no_cde_presta']
                date_cde = lignes['date_cde']                                                    
                date_liv = lignes['date_liv']                                                   
                mode_payment = lignes['mode_payment']                                                   
                mtt_paye = self.conversion_en_flaot(lignes['mtt_paye'])
                mode_transport = lignes['mode_transport']
                info_livraison = lignes['info_livraison']
                nb_lig = lignes['line']                

                plateforme_web = plateforme_web.strip()
                partner_id = self.recherche_partenaire(plateforme_web)
                id_livraison = id_livraison.strip()
                partner_shipping_id = self.recherche_partenaire(id_livraison)
                id_facturation = id_facturation.strip()
                partner_invoice_id = self.recherche_partenaire(id_facturation)
                #date_order = fields.Date.to_string(datetime.now())
                date_expected = fields.Date.to_string(datetime.now())
                payment_mode_id = self.recherche_payment_mode(mode_payment,company_id.id)
                mode_transport_id = self.recherche_mode_transport(mode_transport,company_id.id)
                pricelist_id_client = self.recherche_liste_prix(partner_id)

                fiscal_position_web = self.recherche_position_fiscal_livraison(partner_shipping_id)
                
                date_order = self.transforme_date_odoo(date_commande_web)
                #
                # On créé la commande
                #
                values_ent = {
                    'partner_id': partner_id,
                    'commande_presta': True,
                    'date_order': date_order,
                    'date_devis_presta': date_order,
                    #'commitment_date': date_order,
                    'expected_date': date_expected,
                    'client_order_ref': no_cde_presta.strip(),
                    'info_liv_presta': info_livraison.strip(),
                    'partner_shipping_id': partner_shipping_id,
                    'partner_invoice_id': partner_invoice_id,
                    'mtt_paye': mtt_paye,
                    'payment_mode_id': payment_mode_id,
                    'no_cde_presta' : no_cde_presta.strip(),
                    'madeco_transport_id': mode_transport_id,
                    'pricelist_id': pricelist_id_client,
                    'fiscal_position_id': fiscal_position_web,
                    'picking_policy': 'one',
                }
                values_entete.append(values_ent) 
     
            if type_ligne == 'LIG':
                #
                # Ligne de commande
                #  
                no_ligne = lignes['line']
                ref_article = lignes['ref_article']
                qte_cde = self.conversion_en_flaot(lignes['quantite'])   
                unite_cde = 'Unité(s)'
                desc_art = lignes['designation']
                pu_net = self.conversion_en_flaot(lignes['pu_net'])

                ref_article = ref_article.strip() 
                ref_article_id = self.recherche_ref_article(ref_article)
                unite_cde = unite_cde.strip() 
                unite_cde_id = self.recherche_unite(unite_cde)

                err_ligne = lignes['lig_ok']
                if err_ligne == False:
                    ligne_en_erreur = True

                desc_art = desc_art.strip()
                if desc_art:                        
                    values_lig = {
                        'product_id': ref_article_id,
                        'lig_commande_presta': True,
                        'product_uom_qty' : qte_cde, 
                        'product_uom': unite_cde_id, 
                        'name': desc_art,
                        'price_unit' : pu_net,
                        'pun_presta': pu_net,
                        'no_ligne_presta': no_ligne,            
                    }
                else:
                    values_lig = {
                        'product_id': ref_article_id,
                        'lig_commande_presta': True,
                        'product_uom_qty' : qte_cde, 
                        'product_uom': unite_cde_id, 
                        'price_unit' : pu_net,
                        'pun_presta': pu_net,
                        'no_ligne_presta': no_ligne,             
                    }

                values_lignes.append(values_lig)

        if new_piece:
            #
            # On génére la commande avec les données connues
            # 
            if ligne_en_erreur == False:
                sale = self.genere_commande_vente(values_entete, values_lignes)
                                
        return sale

    #########################################################################################
    #                                                                                       #
    #                                   Conversion en Float                                 #
    #                                                                                       #
    #########################################################################################
    def transforme_date_odoo(self, date_a_convertir):
        jour = date_a_convertir[0:2]
        mois = date_a_convertir[3:5]
        annee = date_a_convertir[6:10]
        heure = date_a_convertir[10:]
        date = str(annee)+'-'+str(mois)+'-'+str(jour)+ heure
        return date

    #########################################################################################
    #                                                                                       #
    #                                   Conversion en Float                                 #
    #                                                                                       #
    #########################################################################################
    def conversion_en_flaot(self, chaine_a_convertir):
        nombre_str = chaine_a_convertir.strip()
        new_nombre = nombre_str.replace(',','.')
        if new_nombre:
            nombre = float(new_nombre)
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
    def presta_generation_mail(self, destinataire, sujet, corps):
        #
        # On envoie un mail au destinataire reçu
        #
        '''
        today = fields.Date.from_string(fields.Date.context_today(self))
        if len(destinataire)>0:
            mail_data = {
                        'subject': sujet,
                        'body_html': corps,
                        'email_from': self.env.user.email,
                        'email_to': destinataire,                        
                        }
            mail_id = self.env['mail.mail'].create(mail_data)
            mail_id.send()
        '''    
        
    #########################################################################################
    #                                                                                       #
    #                                     Génération erreur presta                          #
    #                                                                                       #
    #########################################################################################
    def presta_generation_erreur(self, erreur,  sujet, corps):
        #
        # On cree un enregistrement dans le suivi PrestaShop
        #
        company_id =  self.env.company 
        suivi_presta = self.env['suivi.presta']
        today = fields.Date.from_string(fields.Date.context_today(self))
        if len(sujet)>0:
            suivi_data = {
                        'company_id': company_id.id,
                        'name': sujet,
                        'libelle_mvt_presta': corps,
                        'erreur_id': erreur.id,                        
                        }

            suivi = suivi_presta.create(suivi_data)

    #########################################################################################
    #                                                                                       #
    #                               Controle Plateforme Presta                              #
    #                                                                                       #
    #########################################################################################
    def controle_plateforme(self, plateforme):
        erreur = True
        partner = self.env['res.partner'].search([('code_presta','=', plateforme)],limit=1)
        if partner:
            erreur = False
            return erreur
        else:
            partner = self.env['res.partner'].search([('name','=', plateforme)],limit=1)
            if partner:
                erreur = False
                return erreur
        return erreur   

    #########################################################################################
    #                                                                                       #
    #                               Controle Partenaire Presta                              #
    #                                                                                       #
    #########################################################################################
    def controle_partenaire(self, plateforme_web, client):
        erreur = True
        plateforme = self.env['res.partner'].search([('code_presta','=', plateforme_web)],limit=1)
        if plateforme:
            partner = self.env['res.partner'].search([('code_presta','=', client),('parent_id','=',plateforme.id)],limit=1)
            if partner:
                erreur = False
                return erreur
            else:
                erreur = True
                return erreur
        return erreur       

    #########################################################################################
    #                                                                                       #
    #                                     Controle devise                                   #
    #                                                                                       #
    #########################################################################################
    def controle_paiement(self, paiement, company_id):
        erreur = True
        paiement_vte = self.env['account.payment.mode'].with_context(lang='fr_FR').search([('name','=', paiement),('company_id','=', company_id)],limit=1)
        if paiement_vte:
            erreur = False
        return erreur 

    #########################################################################################
    #                                                                                       #
    #                                     Controle ref article                              #
    #                                                                                       #
    #########################################################################################
    def controle_ref_article(self, ean):
        erreur = True
        product_vte = self.env['product.product'].search([('barcode','=', ean)],limit=1)
        if product_vte:
            erreur = False
        else:
            templ_vte = self.env['product.template'].search([('barcode','=', ean)],limit=1)
            if templ_vte:
                erreur = False
            else:
                product_vte = self.env['product.product'].search([('default_code','=', ean)],limit=1)
                if product_vte:
                    erreur = False
                else:
                    templ_vte = self.env['product.template'].search([('default_code','=', ean)],limit=1)
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
        unite_vte = self.env['uom.uom'].with_context(lang='fr_FR').search([('unite_presta','=', unite)],limit=1)
        if unite_vte:
            erreur = False        
        return erreur   

    #########################################################################################
    #                                                                                       #
    #                               Controle Mode de transport                              #
    #                                                                                       #
    #########################################################################################
    def controle_mode_transport(self, transport, company_id):
        erreur = True
        mode_vte = self.env['madeco.transport'].with_context(lang='fr_FR').search([('name','=', transport),('company_id','=', company_id)],limit=1)
        if mode_vte:
            erreur = False         
        return erreur

    #########################################################################################
    #                                                                                       #
    #                            Recadrage Mode de transport web                            #
    #                                                                                       #
    #########################################################################################
    def recadrage_mode_transport_web(self, transport):
        if transport[0:1]=='"':
            new_transport1 = transport[1:]
        else:
            new_transport1 = transport    
        lg = len(new_transport1) 
        if new_transport1[lg-1:lg]=='"':
            new_transport = new_transport1[:lg-1] 
        else:
            new_transport = new_transport1     
        return new_transport    

    #########################################################################################
    #                                                                                       #
    #                                   Controle pays                                       #
    #                                                                                       #
    #########################################################################################
    def controle_pays(self, pays):
        erreur = True
        pays = self.env['res.country'].with_context(lang='fr_FR').search([('name','ilike', pays)],limit=1)
        if pays:
            erreur = False        
        return erreur        

    #########################################################################################
    #                                                                                       #
    #                                Recherche Partenaire Presta                            #
    #                                                                                       #
    #########################################################################################
    def recherche_partenaire(self, ccli):
        partenaire = False
        partner = self.env['res.partner'].search([('code_presta','=', ccli)],limit=1)
        if partner:
            partenaire = partner.id
            return partenaire
        else:
            partner = self.env['res.partner'].search([('name','=', ccli)],limit=1)
            if partner:
                partenaire = partner.id
            return partenaire
        return partenaire  

    #########################################################################################
    #                                                                                       #
    #                                Recherche Liste de prix Client                         #
    #                                                                                       #
    #########################################################################################
    def recherche_liste_prix(self, partner_id):
        liste_prix = False
        partner = self.env['res.partner'].search([('id','=', partner_id)],limit=1)
        if partner:
            liste_prix = partner.property_product_pricelist.id                           
            return liste_prix
        
        return liste_prix  

    #########################################################################################
    #                                                                                       #
    #                                   Recherche Partner                                   #
    #                                                                                       #
    #########################################################################################
    def recherche_partner(self, ccli):
        partenaire = False
        partner = self.env['res.partner'].search([('id','=', ccli)],limit=1)
        if partner:
            partenaire = partner.id
            return partenaire
        else:
            partner = self.env['res.partner'].search([('name','=', ccli)],limit=1)
            if partner:
                partenaire = partner.id
            return partenaire
        return partenaire  

    #########################################################################################
    #                                                                                       #
    #                                   Recherche Position fiscale                          #
    #                                                                                       #
    #########################################################################################
    def recherche_position_fiscal_livraison(self, ccli):
        company_id = self.env.company
        position_fiscal = False
        partner = self.env['res.partner'].search([('id','=', ccli)],limit=1)
        if partner:
            if partner.country_id == company_id.france_pays_id:
                position_fiscal = company_id.france_fiscal_position_id.id 
                return position_fiscal
        else:
            return position_fiscal         

    #########################################################################################
    #                                                                                       #
    #                                    Recherche devise                                   #
    #                                                                                       #
    #########################################################################################
    def recherche_devise(self, devise):
        company_id =  self.env.company 
        devise_id = company_id.currency_id.id
        devise_vte = self.env['res.currency'].search([('name','=', devise)],limit=1)
        if devise_vte:
            devise_id = devise_vte.id
        return devise_id 

    #########################################################################################
    #                                                                                       #
    #                                    Recherche pays                                     #
    #                                                                                       #
    #########################################################################################
    def recherche_pays(self, pays_search):
        pays_id = False
        pays = self.env['res.country'].with_context(lang='fr_FR').search([('name','ilike', pays_search)],limit=1)
        if pays:
            pays_id = pays.id
        return pays_id     
    
    #########################################################################################
    #                                                                                       #
    #                                    Recherche ref article                              #
    #                                                                                       #
    #########################################################################################
    def recherche_ref_article(self, ean):
        ean_id = False
        product_vte = self.env['product.product'].search([('barcode','=', ean)],limit=1)
        if product_vte:
            ean_id = product_vte.id
        else:
            templ_vte = self.env['product.template'].search([('barcode','=', ean)],limit=1)
            if templ_vte:
                ean_id = templ_vte.id
            else:
                product_vte = self.env['product.product'].search([('default_code','=', ean)],limit=1)
                if product_vte:
                    ean_id = product_vte.id
                else:
                    templ_vte = self.env['product.template'].search([('default_code','=', ean)],limit=1)
                    if templ_vte:
                        ean_id = templ_vte.id
        return ean_id

    #########################################################################################
    #                                                                                       #
    #                                  Recherche unité                                      #
    #                                                                                       #
    #########################################################################################
    def recherche_unite(self, unite):
        unite_id = False
        unite_vte = self.env['uom.uom'].with_context(lang='fr_FR').search([('name','=', unite)],limit=1)
        if unite_vte:
            unite_id = unite_vte.id                
        return unite_id 

    #########################################################################################
    #                                                                                       #
    #                               Recherche Mode de paiement                              #
    #                                                                                       #
    #########################################################################################
    def recherche_payment_mode(self, paiement, company_id):
        payment_id = False
        paiement_vte = self.env['account.payment.mode'].with_context(lang='fr_FR').search([('name','=', paiement),('company_id','=', company_id)],limit=1)
        if paiement_vte:
            payment_id = paiement_vte.id
        return payment_id    

    #########################################################################################
    #                                                                                       #
    #                               Recherche Mode de transport                             #
    #                                                                                       #
    #########################################################################################
    def recherche_mode_transport(self, transport, company_id):
        mode_transport_id = False
        mode_vte = self.env['madeco.transport'].with_context(lang='fr_FR').search([('name','=', transport),('company_id','=', company_id)],limit=1)
        if mode_vte:
            mode_transport_id = mode_vte.id        
        return mode_transport_id       

    #########################################################################################
    #                                                                                       #
    #                      Création adresse livraison ou facturation                        #
    #                                                                                       #
    #########################################################################################
    def creation_adresse_livraison_facturation(self,values_adresse):
        values_partner = {}
        partner_new = False
        if values_adresse:
            type_adresse        = values_adresse['type_adresse']
            partner_id          = values_adresse['partner_id']
            adresse_id          = values_adresse['adresse_id']
            nom                 = values_adresse['nom']
            rue1                = values_adresse['rue1']
            rue2                = values_adresse['rue2']
            cp                  = values_adresse['cp']
            ville               = values_adresse['ville']
            pays                = values_adresse['pays']
            email               = values_adresse['email']
            tel                 = values_adresse['tel']

            if type_adresse == 'livraison':
                type_adr = 'delivery'
            else:
                type_adr = 'invoice' 
            parent_id = self.recherche_partenaire(partner_id.strip())
            pays_id = self.recherche_pays(pays.strip())       

            values_partner = {
                'name' : nom,
                'parent_id' : parent_id,
                'street' : rue1,
                'street2' : rue2,
                'zip': cp,
                'city': ville,
                'country_id' : pays_id,
                'email' : email,
                'phone' : tel,
                'type' : type_adr,
                'code_presta': adresse_id,
                'client_web': True,
            }
                                   
            partner_new = self.env['res.partner'].create(values_partner)
            if partner_new:
                return True
            else:
                return False    


    #########################################################################################
    #                                                                                       #
    #                            Génération d'une commande Presta                           #
    #                                                                                       #
    #########################################################################################
    def genere_commande_vente(self,values_entete, values_lignes):
        sale = False
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company 
        cpteur = 0
        if values_entete:
            for values_ent in values_entete:
                cpteur += 1
                controle_cde = self.controle_commande_existante(values_ent,cpteur)
                if not controle_cde:
                    controle_client_presta = self.controle_gestion_commande_presta_partner(values_ent)
                    if controle_client_presta:  
                        sale = self.env['sale.order'].create(values_ent)
                        if sale:
                            if not sale.fiscal_position_id:
                                sale.onchange_partner_shipping_id()
                        
                        if sale:
                            if values_lignes:
                                for values_lig in values_lignes:
                                    values_lig.update({
                                        'order_id': sale.id,
                                        })
                                    sale_lig = self.env['sale.order.line'].create(values_lig)

                            #
                            # On envoie un mail sur la commande créée et on met à jour le suivi PrestaShop
                            #             
                            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                            corps = "La commande {} pour le client {} a été intégrée avec succès. <br/><br>".format(sale.name,sale.partner_id.name) 
                            corps+= "Le numéro de commande PrestaShop est {}. <br/><br>".format(sale.client_order_ref)  
                            corps+= "La pièce est en devis dans votre ERP. <br/><br>"                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            destinataire = company_id.gestion_user_id.email
                            if destinataire:
                                self.presta_generation_mail(destinataire, sujet, corps)
                            code_erreur = self.env['erreur.presta'].search([('name','=', '0500')], limit=1) 
                            message = "La commande {} pour le client {} a été intégrée avec succès. ".format(sale.name,sale.partner_id.name) 
                            message+= "Le numéro de commande PrestaShop est {}.".format(sale.client_order_ref)  
                            self.presta_generation_erreur(code_erreur, sujet, message)

                            #
                            # On met à jour les commandes intégrées 
                            #
                            if sale.state in ('draft','sent'):
                                affect = sale.affectation_routes_logistiques_sale_order_line(sale)

                            if not sale.route_id:
                                ent_route_id = sale.recherche_route_unique_sur_commande(sale)   
                                if ent_route_id:
                                    sale.route_id = ent_route_id 

                            #
                            # On passe la pièce en commande après avoir calculer la date de livraison
                            #
                            sale.date_livraison_calculee = apik_calendar.calcul_date_ouvree(sale.date_livraison_calculee, 0, company_id.nb_weekend_days, company_id.zone_geo)  
                            if not sale.commitment_date:
                                if sale.date_livraison_calculee and sale.date_livraison_demandee:
                                    if sale.date_livraison_calculee > sale.date_livraison_demandee:
                                        sale.commitment_date = sale.date_livraison_calculee
                                    else:
                                        sale.commitment_date = sale.date_livraison_demandee
                                else:
                                    #sale.commitment_date = sale.date_order  
                                    sale.commitment_date = apik_calendar.calcul_date_ouvree(sale.date_order, 0, company_id.nb_weekend_days, company_id.zone_geo)  
                            else:
                                sale.commitment_date = apik_calendar.calcul_date_ouvree(sale.commitment_date, 0, company_id.nb_weekend_days, company_id.zone_geo)  

                            #
                            # on regarde si un article sur mesure existe dans la commande 
                            #
                            art_sur_mesure = self.recherche_articles_sur_mesure(sale)
                            if not art_sur_mesure:
                                sale.action_confirm()
                    else:
                        sale = False        
                else:
                    sale = False        

        return sale      

    #########################################################################################
    #                                                                                       #
    #                      Controle existence commande pour le partner                      #
    #                                                                                       #
    #########################################################################################
    def recherche_articles_sur_mesure(self,sale):     
        article_sm = False
        if sale:
            for line in sale.order_line:
                if line.product_id.typologie_article == 'A3':
                    article_sm = True
                    break

        return article_sm 
        
    #########################################################################################
    #                                                                                       #
    #                      Controle existence commande pour le partner                      #
    #                                                                                       #
    #########################################################################################
    def controle_commande_existante(self,values_ent,cpteur):
        commande_existante = False
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company
        partner_id = values_ent['partner_id']
        ref_cde = values_ent['client_order_ref'].strip()        
        cde_vte = self.env['sale.order'].search([('partner_id','=', partner_id),('client_order_ref','=',ref_cde)],limit=1)
        if cde_vte:
            commande_existante = True
            if cpteur == 1:
                client = self.env['res.partner'].search([('id','=', partner_id)],limit=1)
                #
                # Erreur sur commande déjà existante dans la base de données Odoo
                #
                sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                corps = "La commande avec la référence {} est déjà existante pour la plateforme {}. <br/><br>".format(ref_cde, client.name) 
                corps+= "La commande n'est pas récréée. <br/><br>"                         
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.presta_generation_mail(destinataire, sujet, corps)
                code_erreur = self.env['erreur.presta'].search([('name','=', '0501')], limit=1) 
                message = "La commande avec la référence {} est déjà existante pour la plateforme {}. ".format(ref_cde, client.name)
                message+= "La commande n'est pas récréée. "   
                self.presta_generation_erreur(code_erreur, sujet, message)

        return commande_existante

    #########################################################################################
    #                                                                                       #
    #                      Controle gestion des commandes presta du client                  #
    #                                                                                       #
    #########################################################################################
    def controle_gestion_commande_presta_partner(self,values_ent):
        client_presta = False
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company
        partner_id = values_ent['partner_id']
        ref_cde = values_ent['client_order_ref'].strip()
        client = self.env['res.partner'].search([('id','=', partner_id)],limit=1)
        if client:
            if client.client_presta:
                client_presta = True
            else:    
                #
                # Le client n'est pas en gestion PrestaShop
                #
                sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(today) 
                corps = "Le client {} n'est pas géré en PrestaShop. <br/><br>".format(client.name) 
                corps+= "La commande {} n'est pas créée. <br/><br>".format(ref_cde)                         
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.presta_generation_mail(destinataire, sujet, corps)
                code_erreur = self.env['erreur.presta'].search([('name','=', '0400')], limit=1) 
                message = "Le client {} n'est pas géré en PrestaShop. ".format(client.name) 
                message+= "La commande {} n'est pas créée. ".format(ref_cde)    
                self.presta_generation_erreur(code_erreur, sujet, message)

        return client_presta

    #########################################################################################
    #                                                                                       #
    #             On déplace le fichier traité dans les répertoires de stockage             #
    #                                                                                       #
    #########################################################################################
    def copie_fichier_traite(self,trait_ok,filename):
        company_id =  self.env.company 
        param = self.env['parametre.presta'].search([('id', '=', company_id.param_presta_id.id)])
        if len(param)>0:
            fichier_path = '%s/' % get_module_path('apik_prestashop') 
            rep_depart = fichier_path + param.rep_import_interne_presta.strip()
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

    #########################################################################################
    #                                                                                       #
    #             On déplace le fichier traité dans les répertoires de stockage             #
    #                                                                                       #
    #########################################################################################
    def delete_fichier_traite(self,filename):
        company_id =  self.env.company 
        param = self.env['parametre.presta'].search([('id', '=', company_id.param_presta_id.id)])
        if len(param)>0:
            fichier_path = '%s/' % get_module_path('apik_prestashop') 
            rep_depart = fichier_path + param.rep_import_interne_presta.strip()
            fichier = filename.strip()
            fichier_a_deplacer = rep_depart + '/' + fichier
            
            ordre_a_executer = 'del %s '%(fichier_a_deplacer)
            #exec = os.system(ordre_a_executer)

            delete_ok = True   
        else:
            delete_ok = False            