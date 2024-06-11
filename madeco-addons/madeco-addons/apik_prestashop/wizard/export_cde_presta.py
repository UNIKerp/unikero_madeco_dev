# -*- coding: utf-8 -*-

import base64
import io
import os
import ftplib
import subprocess
import pysftp

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero, pycompat
from datetime import datetime, timedelta
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules import get_module_resource
from odoo.modules import get_module_path
from ftplib import FTP
from tempfile import TemporaryFile

import logging
logger = logging.getLogger(__name__)


class CommandePrestaExport(models.TransientModel):
    _name = "apik_prestashop.wizard_presta_cde"
    _description = "Export des commandes PrestaShop"
    
    export_date = fields.Date("Date de l'export",default=fields.Date.today)
    cdepresta_data = fields.Binary('Fichier Export')
    filename = fields.Char(string='Filename', size=256)
    export_auto = fields.Boolean("Export automatique par FTP", default=False, required=True)

    #########################################################################################
    #                                                                                       #
    #                   Import des commandes PrestaShop autoamtique                         #
    #                                                                                       #
    #########################################################################################                  
    @api.model
    def export_cde_presta_automatique(self):
        wizard_values = {
            'export_auto': True,
        }
        wizard = self.create(wizard_values)

        logger.info("==============================================")
        logger.info("     Début Export des commandes PrestaShop    ")
        logger.info("==============================================")                
        wizard.export_cde_presta()
        logger.info("==============================================")
        logger.info("      Fin Export des commandes PrestaShop     ")
        logger.info("==============================================")


    #########################################################################################
    #                                                                                       #
    #                          Bouton Export des commandes PrestaShop                       #
    #                                                                                       #
    #########################################################################################        
    def export_cde_presta(self):           
        self.ensure_one()
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company                 
        partner_obj = self.env['res.partner']
        sale_obj = self.env['sale.order']

        if self.export_auto:
            sale_ids = sale_obj.search([('state','=','sale'),('company_id','=',company_id.id),('commande_presta','=',True),('cde_presta_genere','=',True),('cde_presta_envoye','=',False)])
        else:    
            sale_ids = sale_obj.search([('id', 'in', self._context.get('active_ids', True))])
        
        nb_enreg = 1
        rows_to_write = []

        for sale in sale_ids:           
            if sale.partner_id.client_presta:
                #
                # On génére l'enregistrement Entête
                #
                enreg_ent = sale.no_cde_presta + ";" + sale.name + ";"

                if enreg_ent:
                    rows_to_write.append(enreg_ent)
                    nb_enreg = nb_enreg + 1                
            else:
                client = partner_obj.search([('id','=', sale.partner_id.id)],limit=1)
                #
                # Erreur sur envoi cde 
                #
                sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Enregistrement des commandes du ' + str(today) 
                corps = "Le client {} n'est pas en gestion PrestaShop. <br/><br>".format(client.name) 
                corps+= "La commande n'est pas enregistrée. <br/><br>"                         
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.presta_generation_mail(destinataire, sujet, corps)
                code_erreur = self.env['erreur.presta'].search([('name','=', '0400')], limit=1) 
                message = "Le client {} n'est pas en gestion PrestaShop. La commande n'est pas enregistrée. ".format(client.name) 
                self.presta_generation_erreur(code_erreur, sujet, message)

            #
            # On met à jour la commande
            #
            sale.write({'cde_presta_envoye': True, 'arc_presta_envoye': True }) 

            client = partner_obj.search([('id','=', sale.partner_id.id)],limit=1)
            #
            # Envoi ARC : Envoi généré
            #
            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Enregistrement des commandes du ' + str(today) 
            corps = "La commande {} pour le client {} a été enregistrée. <br/><br>".format(sale.name, client.name) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.presta_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.presta'].search([('name','=', '0600')], limit=1) 
            message = "La commande {} pour le client {} a été enregistrée. ".format(sale.name, client.name) 
            self.presta_generation_erreur(code_erreur, sujet, message)

        #
        # on écrit le fichier d'export
        #
        if nb_enreg >= 1:            
            date_generation = fields.Datetime.now()
            date_fic = fields.Datetime.from_string(date_generation)
            datefic = date_fic.strftime("%d%m%Y%H%M%S")

            presta_obj = self.env['parametre.presta']
            company_id =  self.env.company 
            gln_societe = company_id.partner_id.code_gln
            if company_id.param_presta_id:
                param = presta_obj.search([('id', '=', company_id.param_presta_id.id)])
                if len(param)>0:        
                    rep_export = param.rep_export_interne_presta 
                    if param.nom_fichier_arc_presta_export:
                        fichier_arc_dest = param.nom_fichier_arc_presta_export.strip()+'_%s_%s' %(gln_societe,datefic) 
                        fichier_arc = fichier_arc_dest+'.csv'                     
                    else:
                        rep_export = '/tmp'
                        fichier_arc_dest = 'ARCWEB_%s_%s' %(gln_societe,datefic)  
                        fichier_arc = fichier_arc_dest+'.csv'  
                else:
                    rep_export = '/tmp' 
                    fichier_arc_dest = 'ARCWEB_%s_%s' %(gln_societe,datefic) 
                    fichier_arc = fichier_arc_dest+'.csv'  
            else:
                rep_export = '/tmp'
                fichier_arc_dest = 'ARCWEB_%s_%s' %(gln_societe,datefic) 
                fichier_arc = fichier_arc_dest+'.csv' 

            self.filename = fichier_arc
            
            fich_path = rep_export
            fichier_genere = fich_path + '/%s' % self.filename
           
            fichier_commande_presta = open(fichier_genere, "w", encoding="latin_1")
            for rows in rows_to_write:
                retour_chariot = '\n'    #'\r\n'
                rows += retour_chariot
                fichier_commande_presta.write(str(rows))
                
            fichier_commande_presta.close()   

            fichier_genere_dest = fich_path + '/%s.csv' % fichier_arc_dest   

            #
            # On envoie le fichier généré par FTP ou SFTP
            #
            company_id =  self.env.company 
            param = presta_obj.search([('id', '=', company_id.param_presta_id.id)])
            if len(param)>0: 
                if param.type_connexion == 'ftp': 
                    #
                    # Envoi FTP
                    #  
                    ftp_user = param.compte_ftp_presta
                    ftp_password = param.mdp_presta
                    adresse_ftp = param.adresse_ftp
                    ftp_port = param.port_ftp
                    rep_envoi_ftp = param.repertoire_cde_presta_integre

                    ftp = ftplib.FTP() 
                    ftp.connect(adresse_ftp, ftp_port, 30*5) 
                    ftp.login(ftp_user, ftp_password)             
                    passif=True
                    ftp.set_pasv(passif)
                    ftp.cwd(rep_envoi_ftp)

                    fic_destination = '%s.csv' % fichier_arc_dest 

                    with open(fichier_genere_dest,'rb') as fp:
                        ftp.storbinary('STOR '+ fic_destination, fp)
                    ftp.quit()
                else: 
                    #
                    # Envoi SFTP
                    #                      
                    sftp_url = param.adresse_ftp
                    sftp_user = param.compte_ftp_presta
                    sftp_password = param.mdp_presta
                    sftp_port = param.port_ftp
                    rep_envoi_sftp = param.repertoire_cde_presta_integre
                    cnopts = pysftp.CnOpts()
                    cnopts.hostkeys = None

                    with pysftp.Connection(host=sftp_url,username=sftp_user,password=sftp_password,port=int(sftp_port),cnopts=cnopts) as sftp:
                        # on ouvre le dossier envoi
                        sftp.chdir(rep_envoi_sftp)
                        # export des fichiers
                        sftp.put(fichier_arc_dest,fichier_genere_dest)
                        with open(fichier_genere_dest,"rb") as f:
                            out = f.read()                                              

            #
            # Envoi CDE : Fichier généré
            #
            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Envoi des commandes du ' + str(today) 
            corps = "Le fichier {} des commandes client a été envoyé. <br/><br>".format(fichier_arc) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.presta_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.presta'].search([('name','=', '0601')], limit=1) 
            message = "Le fichier {} des commandes client a été envoyé.".format(fichier_arc)
            self.presta_generation_erreur(code_erreur, sujet, message)    
        else:
            raise UserError(_("Aucune commande PrestaShop à envoyer."))    

    #########################################################################################
    #                                                                                       #
    #                                    Génération mail                                    #
    #                                                                                       #
    #########################################################################################
    def presta_generation_mail(self, destinataire, sujet, corps):
        #
        # On envoie un mail au destinataire reçu
        #
        mail_obj = self.env['mail.mail']

        '''
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
        '''

    #########################################################################################
    #                                                                                       #
    #                                     Génération erreur Presta                          #
    #                                                                                       #
    #########################################################################################
    def presta_generation_erreur(self, erreur, sujet, corps):
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
    #                                                                                       #
    #                                                                                       #          
    #########################################################################################
    
    