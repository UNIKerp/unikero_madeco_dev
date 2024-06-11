# -*- coding: utf-8 -*-

#import json
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime, timedelta
from tempfile import TemporaryFile
import base64
import io

from odoo.modules import get_module_resource
from odoo.modules import get_module_path

import os
import ftplib
import subprocess

import logging
logger = logging.getLogger(__name__)


class Picking(models.Model):
    _inherit = 'stock.picking' 

    commande_presta = fields.Boolean(string="Commande WEB Prestashop", default=False, compute="_compute_commande_presta")
    livweb_genere = fields.Boolean(string="LIVWEB généré", copy=False, default=False)
    livweb_envoye = fields.Boolean(string="LIVWEB envoyé", copy=False, default=False)

    #########################################################################################
    #                                                                                       #
    #                             _compute_commande_presta                                  #
    #                                                                                       #
    #########################################################################################     
    @api.depends('origin', 'create_date', 'write_date')
    def _compute_commande_presta(self):
        for pick in self:
            if pick.origin:
                sale = self.env['sale.order'].search([('name', '=', pick.origin)],limit=1)
                if len(sale)>0:
                    if sale.commande_presta:
                        pick.commande_presta = True
                    else:
                        pick.commande_presta = False
                else:
                    pick.commande_presta = False
            else:
                pick.commande_presta = False

    #########################################################################################
    #                                                                                       #
    #                                     Export DESADV                                     #
    #                                                                                       #
    #########################################################################################     
    def button_validate(self): 
        resultat = super().button_validate()
        if resultat == True:
            for pick in self:
                if pick.state == 'done':
                    if pick.picking_type_id.livweb_edi:
                        if pick.origin:                             
                            sale = self.env['sale.order'].search([('name', '=', pick.origin)],limit=1)
                            if len(sale)>0:  
                                if sale.commande_presta:
                                    #
                                    # On génére l'envoi du LIVWEB EDI   
                                    #
                                    pick.export_livweb_picking(sale)
                                else:
                                    pick.livweb_genere = False     
                            else:    
                                pick.livweb_genere = False                                 
        return resultat

    #########################################################################################
    #                                                                                       #
    #                                     Export LIVWEB                                     #
    #                                                                                       #
    #########################################################################################      
    def export_livweb_picking(self, sale):           
        self.ensure_one()
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company           
        nb_enreg = 0
        rows_to_write = []

        for picking in self: 
            client = self.env['res.partner'].search([('id','=', sale.partner_id.id)],limit=1)                
            if sale.partner_id.client_presta:
                #
                # On génére l'enregistrement Entête
                #
                enreg_ent = sale.no_cde_presta + ";" + sale.name + ";" + picking.madeco_transport_id.name
                #enreg_ent = sale.no_cde_presta + ";" + sale.name + ";" + picking.intrastat_transport_id.name

                if enreg_ent:
                    rows_to_write.append(enreg_ent)
                    nb_enreg = nb_enreg + 1                
            else:
                #
                # Erreur sur envoi liv web 
                #
                sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Enregistrement des livraisons du ' + str(today) 
                corps = "Le client {} n'est pas en gestion PrestaShop. <br/><br>".format(client.name) 
                corps+= "La livraison n'est pas générée. <br/><br>"                         
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.presta_generation_mail(destinataire, sujet, corps)
                code_erreur = self.env['erreur.presta'].search([('name','=', '0400')], limit=1) 
                message = "Le client {} n'est pas en gestion PrestaShop. La livraison n'est pas générée. ".format(client.name) 
                self.presta_generation_erreur(code_erreur, sujet, message)
            #
            # Envoi LIV WEB : Envoi généré
            #
            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Enregistrement des livraisons du ' + str(today) 
            corps = "La livraison {} pour le client {} a été générée. <br/><br>".format(picking.name, client.name) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.presta_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.presta'].search([('name','=', '0700')], limit=1) 
            message = "La livraison {} pour le client {} a été générée. ".format(picking.name, client.name) 
            self.presta_generation_erreur(code_erreur, sujet, message)
            #
            # On met à jour le picking
            #
            picking.write({'livweb_genere':True, 'livweb_envoye':True,}) 
        #
        # on écrit le fichier d'export
        #
        if nb_enreg >= 1:    
            #logger.info("========================================================")        
            #logger.info(rows_to_write)
            #logger.info("========================================================")
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
                    if param.nom_fichier_liv_presta_export:
                        fichier_liv_dest = param.nom_fichier_liv_presta_export.strip()+'_%s_%s' %(gln_societe,datefic) 
                        fichier_liv = fichier_liv_dest+'.csv'                     
                    else:
                        rep_export = '/tmp'
                        fichier_liv_dest = 'LIVWEB_%s_%s' %(gln_societe,datefic)  
                        fichier_liv = fichier_liv_dest+'.csv'  
                else:
                    rep_export = '/tmp' 
                    fichier_liv_dest = 'LIVWEB_%s_%s' %(gln_societe,datefic) 
                    fichier_liv = fichier_liv_dest+'.csv'  
            else:
                rep_export = '/tmp'
                fichier_liv_dest = 'LIVWEB_%s_%s' %(gln_societe,datefic) 
                fichier_liv = fichier_liv_dest+'.csv' 
            
            fich_path = rep_export
            fichier_genere = fich_path + '/%s' % fichier_liv
           
            fichier_livraison_presta = open(fichier_genere, "w", encoding="latin_1")
            for rows in rows_to_write:
                retour_chariot = '\n'    #'\r\n'
                rows += retour_chariot
                fichier_livraison_presta.write(str(rows))
                
            fichier_livraison_presta.close()   

            fichier_genere_dest = fich_path + '/%s.csv' % fichier_liv_dest   

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
                    rep_envoi_ftp = param.repertoire_envoi_livraison_presta

                    ftp = ftplib.FTP() 
                    ftp.connect(adresse_ftp, ftp_port, 30*5) 
                    ftp.login(ftp_user, ftp_password)             
                    passif=True
                    ftp.set_pasv(passif)
                    ftp.cwd(rep_envoi_ftp)

                    fic_destination = '%s.csv' % fichier_liv_dest 

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
                    rep_envoi_sftp = param.repertoire_envoi_livraison_presta
                    cnopts = pysftp.CnOpts()
                    cnopts.hostkeys = None

                    with pysftp.Connection(host=sftp_url,username=sftp_user,password=sftp_password,port=int(sftp_port),cnopts=cnopts) as sftp:
                        # on ouvre le dossier envoi
                        sftp.chdir(rep_envoi_sftp)
                        # export des fichiers
                        sftp.put(fichier_liv_dest,fichier_genere_dest)
                        with open(fichier_genere_dest,"rb") as f:
                            out = f.read()                                              

            #
            # Envoi LIVWEB : Fichier généré
            #
            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Envoi des livraisons du ' + str(today) 
            corps = "Le fichier {} des livraisons client a été envoyé. <br/><br>".format(fichier_liv) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.presta_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.presta'].search([('name','=', '0701')], limit=1) 
            message = "Le fichier {} des livraisons client a été envoyé.".format(fichier_liv)
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

    
    
