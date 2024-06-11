# -*- coding: utf-8 -*-

#import json
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime, timedelta
from datetime import date
from tempfile import TemporaryFile
import base64
import io
import ftplib
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

class AccountMove(models.Model):
    _inherit = 'account.move' 

    commande_edi = fields.Boolean(string="Commande EDI", default=False, compute="_compute_commande_edi")
    invoic_edi_genere = fields.Boolean(string="INVOIC EDI généré", copy=False, default=False)
    invoic_edi_envoye = fields.Boolean(string="INVOIC EDI envoyé", copy=False, default=False)

    #########################################################################################
    #                                                                                       #
    #                                _compute_commande_edi                                  #
    #                                                                                       #
    #########################################################################################     
    @api.depends('invoice_origin', 'create_date', 'write_date')
    def _compute_commande_edi(self):
        for fact in self:
            if fact.invoice_origin:
                for origin in fact.invoice_origin.split():
                    if origin != ',': 
                        sale = self.env['sale.order'].search([('name', '=', origin)],limit=1)
                        if len(sale)>0:
                            if sale.commande_edi:
                                fact.commande_edi = True
                                break
                            else:
                                fact.commande_edi = False
                        else:
                            fact.commande_edi = False        
                    else:
                        fact.commande_edi = False
                else:
                    fact.commande_edi = False
            else:
                fact.commande_edi = False

    
    #########################################################################################
    #                                                                                       #
    #                                     Export INVOIC                                     #
    #                                                                                       #
    #########################################################################################     
    def export_invoic(self):
        export_ok = False               

    '''
    def action_post(self):
        #
        # On regarde si le client est en EDI et si la gestion des INVOIC est active
        #        
        if self.partner_id.client_edi:
            if self.commande_edi:
                if self.partner_id.edi_invoic:
                    self.invoic_edi_genere = True
                else:
                    self.invoic_edi_genere = False
                    #
                    # On envoie un mail et on met à jour le suivi EDI
                    # 
                    today = fields.Date.to_string(datetime.now())   
                    company_id =  self.env.company 
                    sujet = str(self.env.company.name) + ' - Gestion EDI - Factures client du ' + str(today) 
                    corps = "La facture {} a été validée. L'envoi INVOIC n'est pas actif pour le client {}. <br/><br>".format(self.name,self.partner_id.name) 
                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                    destinataire = company_id.gestion_user_id.email
                    if destinataire:
                        self.edi_generation_mail(destinataire, sujet, corps)
                    code_erreur = self.env['erreur.edi'].search([('name','=', '0405')], limit=1) 
                    flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                    message = "La facture {} a été validée. L'envoi INVOIC n'est pas actif pour le client {}.".format(self.name,self.partner_id.name) 
                    self.edi_generation_erreur(code_erreur, flux, sujet, message)                    
            else:
                self.invoic_edi_genere = False
        else:
            self.invoic_edi_genere = False       
            
        return super().action_post()
    '''    

    #########################################################################################
    #                                                                                       #
    #                                 Génération INVOIC du jour                             #
    #                                                                                       #
    #########################################################################################     
    def export_invoic_journalier(self):
        company =  self.env.company 
        today = fields.Date.to_string(datetime.now())   

        logger.info("__________________________________________________")    
        logger.info("  Début de l'export journalier des factures EDI   ")
        logger.info("__________________________________________________")

        nb_enreg = 0
        rows_to_write = []

        moves = self.env['account.move'].search([('move_type', 'in', ('out_invoice','out_refund')),('state','=','posted'),('invoic_edi_envoye','=',False),('company_id','=', company.id)])
        if moves:
            for move in moves:
                logger.info("____________________")    
                logger.info("Facture: " + move.name)
                logger.info("____________________")
                # 
                # On génére l'invoic edi
                #  
                commande_edi_ok = False
                if move.move_type == 'out_invoice':
                    ###########  
                    # Facture #                
                    ###########
                    #
                    # On recherche la première commande de vente rattaché à la facture
                    #
                    if move.invoice_origin:
                        commande_origine = self.recherche_commande_origin(move.invoice_origin)
                        if commande_origine:
                            sale = self.env['sale.order'].search([('id', '=', commande_origine)],limit=1)
                            if len(sale)>0:
                                if sale.commande_edi:
                                    commande_edi_ok = True
                else:
                    #########  
                    # Avoir #                
                    #########
                    #
                    # On recherche la première commande de vente rattaché à la facture lié à l'avoir
                    #
                    if move.reversed_entry_id.invoice_origin:
                        commande_origine = self.recherche_commande_origin(move.reversed_entry_id.invoice_origin)
                        if commande_origine:
                            sale = self.env['sale.order'].search([('id', '=', commande_origine)],limit=1)
                            if len(sale)>0:
                                if sale.commande_edi:    
                                    commande_edi_ok = True

                if commande_edi_ok:    
                    #logger.info("commande ok : " + sale.name)                   
                    if sale.partner_invoice_id.client_edi:
                        if sale.partner_invoice_id.edi_invoic:                                
                            #
                            # On génére l'enregistrement Entête
                            #
                            enreg_ent = self.export_invoic_entete(move,sale)
                            if enreg_ent:
                                rows_to_write.append(enreg_ent)
                                nb_enreg = nb_enreg + 1
                            #logger.info("entete ok : " + sale.name)     
                            #
                            # On génère l'enregistrement NAD+BY
                            # 
                            if sale.partner_acheteur_id:
                                enreg_par = self.export_invoic_param('BY',move,sale,True) 
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1 
                            #logger.info("NAD+BY ok : " + sale.name)            
                            #
                            # On génère l'enregistrement NAD+SU et NAD+RE
                            # 
                            if sale.partner_vendeur_id:
                                enreg_par = self.export_invoic_param('SU',move,sale,True)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1  
                                # 
                                # On recréé un segment identique pour gérer le PAR+RE (Règlé à) pour CASTORAMA 
                                # 
                                enreg_par = self.export_invoic_param('RE',move,sale,True)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1   
                            #logger.info("NAD+SU ok : " + sale.name)         
                            #
                            # On génère l'enregistrement NAD+DP
                            # 
                            if sale.partner_livre_a_id:
                                enreg_par = self.export_invoic_param('DP',move,sale,True)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1  
                            #logger.info("NAD+DP ok : " + sale.name)           
                            #
                            # On génère l'enregistrement NAD+UC
                            # 
                            if sale.partner_final_id:
                                enreg_par = self.export_invoic_param('UC',move,sale,True)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1  
                            #logger.info("NAD+UC ok : " + sale.name)   
                            #
                            # On génère l'enregistrement NAD+IV
                            # 
                            if sale.partner_facture_a_id:
                                enreg_par = self.export_invoic_param('IV',move,sale,True)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1  
                            else:
                                enreg_par = self.export_invoic_param('IV',move,sale,False)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1  
                            #logger.info("NAD+IV ok : " + sale.name)   
                            #
                            # On génère l'enregistrement NAD+OB
                            # 
                            if sale.partner_commande_par_id:
                                enreg_par = self.export_invoic_param('OB',move,sale,True)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1 
                            #logger.info("NAD+OB ok : " + sale.name)   
                            #
                            # On génère l'enregistrement NAD+PR
                            # 
                            if sale.partner_paye_par_id:
                                enreg_par = self.export_invoic_param('PR',move,sale,True)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1 
                            #logger.info("NAD+PR ok : " + sale.name)   
                            #
                            # On génère l'enregistrement NAD+UD
                            # 
                            if sale.partner_final_ud_id:
                                enreg_par = self.export_invoic_param('UD',move,sale,True)
                                if enreg_par:
                                    rows_to_write.append(enreg_par)
                                    nb_enreg = nb_enreg + 1  
                            #logger.info("NAD+UD ok : " + sale.name)   
                            #
                            # On génére l'enregistrement Com
                            #
                            enreg_com = self.export_invoic_com(move,sale)
                            if enreg_com:
                                rows_to_write.append(enreg_com)
                                nb_enreg = nb_enreg + 1
                            #logger.info("Commentaire ok : " + sale.name) 
                            #
                            # On génére l'enregistrement Reg
                            #
                            enreg_reg = self.export_invoic_reg(move,sale,'R')
                            if enreg_reg:
                                rows_to_write.append(enreg_reg)
                                nb_enreg = nb_enreg + 1  
                            #logger.info("Segment Reg ok : " + sale.name)  
                            #
                            # On génére l'enregistrement Reg frais Transport
                            #
                            #logger.info("Etape 1")
                            enreg_reg_frais = self.export_invoic_reg_frais_transport(move,sale,'C')
                            if enreg_reg_frais:
                                rows_to_write.append(enreg_reg_frais)
                                nb_enreg = nb_enreg + 1               
                            #logger.info("Segment Reg Frais ok : " + sale.name)    
                            #
                            # On génère les enregistrements ligne
                            # 
                            nb_line_invoice = 0
                            for line in move.invoice_line_ids:  
                                if line.product_id.id != company.product_rem_global_id.id and not line.product_id.art_frais_transport:                                     
                                    nb_line_invoice += 1  
                                    enreg_lig = self.export_invoic_ligne(move,sale,line,nb_line_invoice) 
                                    if enreg_lig:
                                        rows_to_write.append(enreg_lig)
                                        nb_enreg = nb_enreg + 1 
                                        #logger.info("Segment Lig ok : " + sale.name)  
                                        #
                                        # On génère les enregistrements ligne de remise
                                        # 
                                        nb_rem = 0
                                        if line.discount > 0:
                                            nb_rem += 1
                                            enreg_rel = self.export_invoic_rel(move,sale,line,'R','1',nb_rem)
                                            if enreg_rel:
                                                rows_to_write.append(enreg_rel)
                                                nb_enreg = nb_enreg + 1 
                                            #logger.info("Segment Rel 1 ok : " + sale.name)      
                                        if line.discount2 > 0:
                                            nb_rem += 1
                                            enreg_rel = self.export_invoic_rel(move,sale,line,'R','2',nb_rem)
                                            if enreg_rel:
                                                rows_to_write.append(enreg_rel)
                                                nb_enreg = nb_enreg + 1 
                                            #logger.info("Segment Rel 2 ok : " + sale.name)      
                                        if line.discount3 > 0:
                                            nb_rem += 1
                                            enreg_rel = self.export_invoic_rel(move,sale,line,'R','3',nb_rem)
                                            if enreg_rel:
                                                rows_to_write.append(enreg_rel)
                                                nb_enreg = nb_enreg + 1 
                                            #logger.info("Segment Rel 3 ok : " + sale.name)                     
                            #
                            # On génére l'enregistrement Pied
                            #
                            enreg_pie = self.export_invoic_pied(move)
                            if enreg_pie:
                                rows_to_write.append(enreg_pie)
                                nb_enreg = nb_enreg + 1
                            #logger.info("Segment Pied ok : " + sale.name)     
                            #
                            # On génére l'enregistrement TVA
                            #
                            detail_tva = move.amount_by_group
                            if detail_tva:
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
                                        #logger.info("Segment TVA ok : " + sale.name)    

                        else:
                            client = self.env['res.partner'].search([('id','=', sale.partner_invoice_id.id)],limit=1)
                            #
                            # Erreur sur envoi ARC : Client ne recoit pas les factures en EDI
                            #
                            sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du ' + str(today) 
                            corps = "Le client {} ne reçoit pas les factures en EDI. <br/><br>".format(client.name) 
                            corps+= "L'INVOIC n'est pas envoyé. <br/><br>"                         
                            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                            
                            flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                            if flux.envoi_auto_mail:   
                                destinataire = company.gestion_user_id.email
                                if destinataire:
                                    self.edi_generation_mail(destinataire, sujet, corps)

                            code_erreur = self.env['erreur.edi'].search([('name','=', '0405')], limit=1) 
                            flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                            message = "Le client {} ne reçoit pas les factures en EDI. L'INVOIC n'est pas envoyé. ".format(client.name) 
                            self.edi_generation_erreur(code_erreur, flux, sujet, message)  
                    else:
                        client = self.env['res.partner'].search([('id','=', sale.partner_invoice_id.id)],limit=1)
                        #
                        # Erreur sur envoi ARC : Client pas en gestion EDI
                        #
                        sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du  ' + str(today) 
                        corps = "Le client {} n'est pas en gestion EDI. <br/><br>".format(client.name) 
                        corps+= "L' INVOIC n'est pas envoyé. <br/><br>"                         
                        corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                        flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                        if flux.envoi_auto_mail:   
                            destinataire = company.gestion_user_id.email
                            if destinataire:
                                self.edi_generation_mail(destinataire, sujet, corps)
                        
                        code_erreur = self.env['erreur.edi'].search([('name','=', '0400')], limit=1) 
                        flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                        message = "Le client {} n'est pas en gestion EDI. L'INVOIC n'est pas envoyé. ".format(client.name) 
                        self.edi_generation_erreur(code_erreur, flux, sujet, message)

                else:
                    #
                    # Erreur sur envoi INVOIC : La commande associée n'est pas une commande EDI
                    #
                    sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du ' + str(today) 
                    corps = "La commande associée à la facture {} n'est pas une commande EDI. <br/><br>".format(move.name) 
                    corps+= "L'INVOIC n'est pas envoyé. <br/><br>"                         
                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 

                    flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                    if flux.envoi_auto_mail:   
                        destinataire = company.gestion_user_id.email
                        if destinataire:
                            self.edi_generation_mail(destinataire, sujet, corps)

                    
                    code_erreur = self.env['erreur.edi'].search([('name','=', '0802')], limit=1) 
                    flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                    message = "Aucune commande associée à la facture {} n'est pas une commande EDI. L'INVOIC n'est pas envoyé.".format(move.name) 
                    self.edi_generation_erreur(code_erreur, flux, sujet, message)     

                #
                # On met à jour la commande
                #
                move.write({'invoic_edi_envoye':True}) 

            #logger.info("===========================================================================")
            #logger.info("Nombre d'enregistrement"+ str(nb_enreg))
            #logger.info(rows_to_write)
            #logger.info("===========================================================================")
            #
            # on écrit le fichier d'export
            #
            if nb_enreg >= 1:
                date_generation = fields.Datetime.now()
                date_fic = fields.Datetime.from_string(date_generation)
                datefic = date_fic.strftime("%d%m%Y%H%M%S")
                company =  self.env.company 
                gln_societe = company.partner_id.code_gln
                if company.param_edi_id:
                    param = self.env['parametre.edi'].search([('id', '=', company.param_edi_id.id)])
                    if len(param)>0:        
                        adresse_ftp = param.adresse_ftp
                        rep_export = param.rep_export_interne_edi 
                        if param.nom_fichier_invoic_edi_export:
                            fichier_invoic = param.nom_fichier_invoic_edi_export.strip()+'_%s_%s' %(gln_societe,datefic) 
                            fichier_invoic_txt = fichier_invoic+'.txt' 
                        else:
                            rep_export = 'data/export_ftp'
                            fichier_invoic = 'INVOIC_%s_%s' %(gln_societe,datefic)  
                            fichier_invoic_txt = fichier_invoic+'.txt'  
                    else:
                        rep_export = 'data/export_ftp' 
                        fichier_invoic = 'INVOIC_%s_%s' %(gln_societe,datefic)  
                        fichier_invoic_txt = fichier_invoic+'.txt'  
                else:
                    rep_export = 'data/export_ftp' 
                    fichier_invoic = 'INVOIC_%s_%s' %(gln_societe,datefic)  
                    fichier_invoic_txt = fichier_invoic+'.txt'   
                                
                fich_path = rep_export
                fichier_genere = fich_path + '/%s' % fichier_invoic_txt
                #                
                # On envoie le fichier généré par FTP
                #
                fichier_invoic_genere = open(fichier_genere, "w", encoding='iso_8859_1')
                for rows in rows_to_write:
                    retour_chariot = '\n'    #'\r\n'
                    #retour_chariot = retour_chariot.encode('ascii')
                    rows += retour_chariot                    
                    fichier_invoic_genere.write(str(rows))
                fichier_invoic_genere.close()        
            
                fichier_genere_dest = fich_path + '/%s.txt' % fichier_invoic   
                fichier_invoic_txt = '%s.txt' % fichier_invoic  
                #
                # On envoie le fichier généré par FTP ou SFTP
                #
                company =  self.env.company 
                param = self.env['parametre.edi'].search([('id', '=', company.param_edi_id.id)])
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
                            ftp.storbinary('STOR '+ fichier_invoic_txt, fp)
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
                            sftp.put(fichier_genere_dest,fichier_invoic_txt)

                #
                # Envoi INVOIC : Fichier généré
                #
                sujet = str(self.env.company.name) + ' - Gestion EDI - Factures du ' + str(today) 
                corps = "Le fichier {} des factures client a été envoyé. <br/><br>".format(fichier_invoic) 
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email)
                destinataire = company.gestion_user_id.email
                if destinataire:
                    self.edi_generation_mail(destinataire, sujet, corps)
                code_erreur = self.env['erreur.edi'].search([('name','=', '0801')], limit=1) 
                flux = self.env['flux.edi'].search([('name','=', 'INVOIC')], limit=1)
                message = "Le fichier {} des factures client a été envoyé.".format(fichier_invoic)
                self.edi_generation_erreur(code_erreur, flux, sujet, message)  

        logger.info("__________________________________________________")    
        logger.info("    Fin de l'export journalier des factures EDI   ")
        logger.info("__________________________________________________")



    #########################################################################################
    #                                                                                       #
    #                                 Export Enregistrement Entete                          #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_entete(self,move,sale): 
        espace = ' '    
        enreg_entete  = 'ENT' 
        enreg_entete += maxi(sale.edi_destinataire,35)
        enreg_entete += maxi(sale.edi_emetteur,35)
        if move.move_type == 'out_refund':
            enreg_entete += '381'  # Avoir
            #sale_facture = self.recherche_commande_lie_facture_origine(move)
        else:
            enreg_entete += '380'  # Facture   
        enreg_entete += maxi(move.name,35)
        date_invoic_calc = self.transforme_date_heure(move.invoice_date,'date')
        heure_invoic_calc = self.transforme_date_heure(move.write_date,'heure')
        enreg_entete += maxi(date_invoic_calc,8)                                
        enreg_entete += maxi(heure_invoic_calc,4)                            
        enreg_entete += maxi(sale.company_id.name,70)                           
        enreg_entete += maxi(sale.company_id.type_societe,70)
        enreg_entete += maxi(sale.company_id.capital_social,70)
        enreg_entete += maxi(move.currency_id.name,3)
        enreg_entete += maxi(move.company_currency_id.name,3)
        enreg_entete += maxi(move.company_currency_id.rate,12)

        w_ref_cde_client_edi = sale.ref_cde_client_edi.strip()
        if sale.ref_cde_client_edi:
            w_ref_cde_client_edi = sale.ref_cde_client_edi.strip()
            if w_ref_cde_client_edi:
                enreg_entete += maxi(sale.ref_cde_client_edi,35)                #   M   352	386	an	35	n° de la commande
            else:
                enreg_entete += maxi(sale.no_cde_client,35)                     #   M   352	386	an	35	n° de la commande    
        else:
            enreg_entete += maxi(sale.no_cde_client,35)                         #   M   352	386	an	35	n° de la commande
        date_cde_calc = self.transforme_date_heure(sale.date_order,'date')
        enreg_entete += maxi(date_cde_calc,8)                                   #   M   387	394	n	8	Date de la commande
        picking = self.recherche_bon_livraison_client(sale)        
        if picking:
            date_liv_calc = self.transforme_date_heure(picking.date_done,'date')
            if picking.no_bl_edi_desadv:
                enreg_entete += maxi(picking.no_bl_edi_desadv,35)               #   M   395	429	an	35	N° du DESADV
            else:    
                enreg_entete += maxi(picking.name,35)                           #   M   395	429	an	35	N° du DESADV
            enreg_entete += maxi(date_liv_calc,8)                               #   M   430	437	n	8	Date de DESADV
        else:
            enreg_entete += maxi(espace,35)                                     #   M   395	429	an	35	No de DESADV
            enreg_entete += maxi(espace,8)                                      #   M   430	437	n	8	Date de DESADV
        enreg_entete += maxi(sale.no_contrat,35)                                #   C   438 472 an  35  N° de contrat
        if move.move_type == 'out_refund':
            enreg_entete += maxi(move.reversed_entry_id.name,35)                #   M   473	507	an	35	N° de facture origine
            date_avoir_calc = self.transforme_date_heure(move.reversed_entry_id.invoice_date,'date')
            enreg_entete += maxi(date_avoir_calc,8)                             #   M   508	515	n	8	Date de facture origine
            enreg_entete += maxi(espace,35)                                     #   C   516 550 an  35  N° de retour
            enreg_entete += maxi(espace,8)                                      #   C   551 558 n   8   Date de retour
        else:
            enreg_entete += maxi(espace,35)                                     #   M   473	507	an	35	N° de facture origine  
            enreg_entete += maxi(espace,8)                                      #   M   508	515	n	8	Date de facture origine  
            enreg_entete += maxi(espace,35)                                     #   C   516 550 an  35  N° de retour
            enreg_entete += maxi(espace,8)                                      #   C   551 558 n   8   Date de retour
        enreg_entete += maxi(date_invoic_calc,8)                                #   C   559 566 n   8   Date du taux de change
        if move.invoice_date_due:
            date_ech_calc = self.transforme_date_heure(move.invoice_date_due,'date')
        else:
            date_ech_facture = self.calcul_date_echeance_facture(move)    
            date_ech_calc = self.transforme_date_heure(date_ech_facture,'date')
        enreg_entete += maxi(date_ech_calc,8)                                   #   M   567	574	n	8	Date d'échéance du règlement
        nb_jour_ech = self.calcul_nb_jours_echeance(move.invoice_date_due)
        enreg_entete += maxi(nb_jour_ech,3)                                     #   C   575	577	n	3	Nombre de jour avant la date d'échéance
        if picking:
            date_liv_calc = self.transforme_date_heure(picking.date_done,'date')
            enreg_entete += maxi(date_liv_calc,8)                               #   M   578	585	n	8	Date réelle de livraison
            enreg_entete += maxi(date_liv_calc,8)                               #   M   586	593	n	8	Date d'expédition
            enreg_entete += maxi(date_liv_calc,8)                               #   M   594	601	n	8	Date d'enlèvement
        else:
            enreg_entete += maxi(espace,8)                                      #   M   578	585	n	8	Date réelle de livraison
            enreg_entete += maxi(espace,8)                                      #   M   586	593	n	8	Date d'expédition
            enreg_entete += maxi(espace,8)                                      #   M   594	601	n	8	Date d'enlèvement  
        enreg_entete += maxi(move.payment_mode_id.payment_method_edi.name,2)    #   M   602	603	n	2	Moyen de paiement
        enreg_entete += maxi(espace,3)                                          #   C   604	613	an	10	Pourcentage des pénalités
        enreg_entete += maxi(move.fiscal_position_id.regime_tva_edi,3)          #   C   614	614	n	1	Régime TVA
        enreg_entete += maxi(move.invoice_incoterm_id.code,3)                   #   C   615	617	an	3	Conditions Incoterms

        return enreg_entete           

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement Paramétre                         #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_param(self,typ_interv,move,sale,param_ok): 

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
        RE ==> Règlé à (Pour CASTORAMA)
        '''
        if typ_interv == 'BY':
            enreg_param += 'BY '                                                        # Type d'intervenant (qualifiant)
            enreg_param += maxi(sale.partner_acheteur_id.code_gln,20)                   # Code identifiant de l'intervenant
            enreg_param += maxi(espace,3)                                               # Type d'identifiant
            enreg_param += maxi(sale.partner_acheteur_id.name,70)                       # Nom de l'intervenant
            enreg_param += maxi(sale.partner_acheteur_id.street,35)                     # Ligne adresse 1 intervenant    
            enreg_param += maxi(sale.partner_acheteur_id.street2,35)                    # Ligne adresse 2 intervenant
            enreg_param += maxi(espace,35)                                              # Ligne adresse 3 intervenant
            enreg_param += maxi(sale.partner_acheteur_id.zip,9)                         # Code postal intervenant
            enreg_param += maxi(sale.partner_acheteur_id.city,35)                       # Ville intervenant
            enreg_param += maxi(sale.partner_acheteur_id.country_id.code,2)             # Code pays intervenant
            if sale.partner_acheteur_id.siret:
                if len(sale.partner_acheteur_id.siret)>=9:
                    siren = sale.partner_acheteur_id.siret[0:9]    
                else:
                    siren = '' 
            else:
                siren = '' 
            enreg_param += maxi(siren,20)                                               # Identification Complémentaire 1
            type_id = 'XA '
            enreg_param += maxi(type_id,3)                                              # Type identification 1
            enreg_param += maxi(sale.partner_acheteur_id.vat,20)                        # Identification Complémentaire 2
            type_id = 'VA '
            enreg_param += maxi(type_id,3)                                              # Type identification 2
            enreg_param += maxi(sale.partner_acheteur_id.siret,20)                      # Identification Complémentaire 3
            type_id = 'GN '
            enreg_param += maxi(type_id,3)                                              # Type identification 3
        else:
            if typ_interv == 'SU' or typ_interv == 'RE':
                if typ_interv == 'RE':
                    enreg_param += 'RE '                                                # Type d'intervenant (qualifiant)
                else:    
                    enreg_param += 'SU '                                                # Type d'intervenant (qualifiant)
                enreg_param += maxi(sale.partner_vendeur_id.code_gln,20)                # Code identifiant de l'intervenant
                enreg_param += maxi(espace,3)                                           # Type d'identifiant
                enreg_param += maxi(sale.partner_vendeur_id.name,70)                    # Nom de l'intervenant
                enreg_param += maxi(sale.partner_vendeur_id.street,35)                  # Ligne adresse 1 intervenant    
                enreg_param += maxi(sale.partner_vendeur_id.street2,35)                 # Ligne adresse 2 intervenant
                enreg_param += maxi(espace,35)                                          # Ligne adresse 3 intervenant
                enreg_param += maxi(sale.partner_vendeur_id.zip,9)                      # Code postal intervenant
                enreg_param += maxi(sale.partner_vendeur_id.city,35)                    # Ville intervenant
                enreg_param += maxi(sale.partner_vendeur_id.country_id.code,2)          # Code pays intervenant
                if sale.company_id.company_registry:
                    rcs = sale.company_id.company_registry 
                else:
                    rcs = ''  
                enreg_param += maxi(rcs,20)                                             # Identification Complémentaire 1
                type_id = 'XA '
                enreg_param += maxi(type_id,3)                                          # Type identification 1
                enreg_param += maxi(sale.partner_vendeur_id.vat,20)                     # Identification Complémentaire 2
                type_id = 'VA '
                enreg_param += maxi(type_id,3)                                          # Type identification 2
                enreg_param += maxi(sale.partner_vendeur_id.siret,20)                   # Identification Complémentaire 3
                type_id = 'GN '
                enreg_param += maxi(type_id,3)                                          # Type identification 3
            else:
                if typ_interv == 'DP':
                    enreg_param += 'DP '                                                # Type d'intervenant (qualifiant)
                    enreg_param += maxi(sale.partner_livre_a_id.code_gln,20)            # Code identifiant de l'intervenant
                    enreg_param += maxi(espace,3)                                       # Type d'identifiant
                    enreg_param += maxi(sale.partner_livre_a_id.name,70)                # Nom de l'intervenant
                    enreg_param += maxi(sale.partner_livre_a_id.street,35)              # Ligne adresse 1 intervenant    
                    enreg_param += maxi(sale.partner_livre_a_id.street2,35)             # Ligne adresse 2 intervenant
                    enreg_param += maxi(espace,35)                                      # Ligne adresse 3 intervenant
                    enreg_param += maxi(sale.partner_livre_a_id.zip,9)                  # Code postal intervenant
                    enreg_param += maxi(sale.partner_livre_a_id.city,35)                # Ville intervenant
                    enreg_param += maxi(sale.partner_livre_a_id.country_id.code,2)      # Code pays intervenant
                    if sale.partner_livre_a_id.siret:
                        if len(sale.partner_livre_a_id.siret)>=9:
                            siren = sale.partner_livre_a_id.siret[0:9]    
                        else:
                            siren = ''      
                    else:
                        siren = ''                                          
                    enreg_param += maxi(siren,20)                                       # Identification Complémentaire 1
                    type_id = 'XA '
                    enreg_param += maxi(type_id,3)                                      # Type identification 1
                    enreg_param += maxi(sale.partner_livre_a_id.vat,20)                 # Identification Complémentaire 2
                    type_id = 'VA '
                    enreg_param += maxi(type_id,3)                                      # Type identification 2
                    enreg_param += maxi(sale.partner_livre_a_id.siret,20)               # Identification Complémentaire 3
                    type_id = 'GN '
                    enreg_param += maxi(type_id,3)
                else:
                    if typ_interv == 'UC':
                        enreg_param += 'UC '                                            # Type d'intervenant (qualifiant)
                        enreg_param += maxi(sale.partner_final_id.code_gln,20)          # Code identifiant de l'intervenant
                        enreg_param += maxi(espace,3)                                   # Type d'identifiant
                        enreg_param += maxi(sale.partner_final_id.name,70)              # Nom de l'intervenant
                        enreg_param += maxi(sale.partner_final_id.street,35)            # Ligne adresse 1 intervenant    
                        enreg_param += maxi(sale.partner_final_id.street2,35)           # Ligne adresse 2 intervenant
                        enreg_param += maxi(espace,35)                                  # Ligne adresse 3 intervenant
                        enreg_param += maxi(sale.partner_final_id.zip,9)                # Code postal intervenant
                        enreg_param += maxi(sale.partner_final_id.city,35)              # Ville intervenant
                        enreg_param += maxi(sale.partner_final_id.country_id.code,2)    # Code pays intervenant
                        if sale.partner_final_id.siret:
                            if len(sale.partner_final_id.siret)>=9:
                                siren = sale.partner_final_id.siret[0:9]    
                            else:
                                siren = ''  
                        else:
                            siren = ''                                              
                        enreg_param += maxi(siren,20)                                   # Identification Complémentaire 1
                        type_id = 'XA'
                        enreg_param += maxi(type_id,3)                                  # Type identification 1
                        enreg_param += maxi(sale.partner_final_id.vat,20)               # Identification Complémentaire 2
                        type_id = 'VA'
                        enreg_param += maxi(type_id,3)                                  # Type identification 2
                        enreg_param += maxi(sale.partner_final_id.siret,20)             # Identification Complémentaire 3
                        type_id = 'GN'
                        enreg_param += maxi(type_id,3)                                  # Type identification 3
                    else:
                        if typ_interv == 'IV':
                            if param_ok:
                                enreg_param += 'IV '                                        # Type d'intervenant (qualifiant)
                                enreg_param += maxi(sale.partner_facture_a_id.code_gln,20)  # Code identifiant de l'intervenant
                                enreg_param += maxi(espace,3)                               # Type d'identifiant
                                enreg_param += maxi(sale.partner_facture_a_id.name,70)      # Nom de l'intervenant
                                enreg_param += maxi(sale.partner_facture_a_id.street,35)    # Ligne adresse 1 intervenant    
                                enreg_param += maxi(sale.partner_facture_a_id.street2,35)   # Ligne adresse 2 intervenant
                                enreg_param += maxi(espace,35)                              # Ligne adresse 3 intervenant
                                enreg_param += maxi(sale.partner_facture_a_id.zip,9)        # Code postal intervenant
                                enreg_param += maxi(sale.partner_facture_a_id.city,35)      # Ville intervenant
                                enreg_param += maxi(sale.partner_facture_a_id.country_id.code,2) # Code pays intervenant
                                if sale.partner_facture_a_id.siret:
                                    if len(sale.partner_facture_a_id.siret)>=9:
                                        siren = sale.partner_facture_a_id.siret[0:9]    
                                    else:
                                        siren = ''    
                                else:
                                    siren = ''                                            
                                enreg_param += maxi(siren,20)                               # Identification Complémentaire 1
                                type_id = 'XA'
                                enreg_param += maxi(type_id,3)                              # Type identification 1
                                enreg_param += maxi(sale.partner_facture_a_id.vat,20)       # Identification Complémentaire 2
                                type_id = 'VA'
                                enreg_param += maxi(type_id,3)                              # Type identification 2                                                                           
                                enreg_param += maxi(sale.partner_facture_a_id.siret,20)     # Identification Complémentaire 3
                                type_id = 'GN'
                                enreg_param += maxi(type_id,3)                              # Type identification 3
                            else:
                                enreg_param += 'IV '                                        # Type d'intervenant (qualifiant)
                                enreg_param += maxi(move.partner_id.code_gln,20)            # Code identifiant de l'intervenant
                                enreg_param += maxi(espace,3)                               # Type d'identifiant
                                enreg_param += maxi(move.partner_id.name,70)                # Nom de l'intervenant
                                enreg_param += maxi(move.partner_id.street,35)              # Ligne adresse 1 intervenant    
                                enreg_param += maxi(move.partner_id.street2,35)             # Ligne adresse 2 intervenant
                                enreg_param += maxi(espace,35)                              # Ligne adresse 3 intervenant
                                enreg_param += maxi(move.partner_id.zip,9)                  # Code postal intervenant
                                enreg_param += maxi(move.partner_id.city,35)                # Ville intervenant
                                enreg_param += maxi(move.partner_id.country_id.code,2)      # Code pays intervenant
                                if move.partner_id.siret:
                                    if len(move.partner_id.siret)>=9:
                                        siren = move.partner_id.siret[0:9]    
                                    else:
                                        siren = ''   
                                else:
                                    siren = ''                                             
                                enreg_param += maxi(siren,20)                               # Identification Complémentaire 1
                                type_id = 'XA'
                                enreg_param += maxi(type_id,3)                              # Type identification 1
                                enreg_param += maxi(move.partner_id.vat,20)                 # Identification Complémentaire 2
                                type_id = 'VA'
                                enreg_param += maxi(type_id,3)                              # Type identification 2                                                                           
                                enreg_param += maxi(move.partner_id.siret,20)               # Identification Complémentaire 3
                                type_id = 'GN'
                                enreg_param += maxi(type_id,3)                              # Type identification 3
                        else:
                            if typ_interv == 'OB':
                                enreg_param += 'OB '                                            # Type d'intervenant (qualifiant)
                                enreg_param += maxi(sale.partner_commande_par_id.code_gln,20)   # Code identifiant de l'intervenant
                                enreg_param += maxi(espace,3)                                   # Type d'identifiant
                                enreg_param += maxi(sale.partner_commande_par_id.name,70)       # Nom de l'intervenant
                                enreg_param += maxi(sale.partner_commande_par_id.street,35)     # Ligne adresse 1 intervenant    
                                enreg_param += maxi(sale.partner_commande_par_id.street2,35)    # Ligne adresse 2 intervenant
                                enreg_param += maxi(espace,35)                                  # Ligne adresse 3 intervenant
                                enreg_param += maxi(sale.partner_commande_par_id.zip,9)         # Code postal intervenant
                                enreg_param += maxi(sale.partner_commande_par_id.city,35)       # Ville intervenant
                                enreg_param += maxi(sale.partner_commande_par_id.country_id.code,2) # Code pays intervenant
                                if sale.partner_commande_par_id.siret:
                                    if len(sale.partner_commande_par_id.siret)>=9:
                                        siren = sale.partner_commande_par_id.siret[0:9]    
                                    else:
                                        siren = ''
                                else:
                                    siren = ''                                                
                                enreg_param += maxi(siren,20)                                   # Identification Complémentaire 1
                                type_id = 'XA'
                                enreg_param += maxi(type_id,3)                                  # Type identification 1
                                enreg_param += maxi(sale.partner_commande_par_id.vat,20)        # Identification Complémentaire 2
                                type_id = 'VA'
                                enreg_param += maxi(type_id,3)                                  # Type identification 2                                                                             
                                enreg_param += maxi(sale.partner_commande_par_id.siret,20)      # Identification Complémentaire 3
                                type_id = 'GN'
                                enreg_param += maxi(type_id,3)                                  # Type identification 3
                            else:
                                if typ_interv == 'PR':
                                    enreg_param += 'PR '                                        # Type d'intervenant (qualifiant)
                                    enreg_param += maxi(sale.partner_paye_par_id.code_gln,20)   # Code identifiant de l'intervenant
                                    enreg_param += maxi(espace,3)                               # Type d'identifiant
                                    enreg_param += maxi(sale.partner_paye_par_id.name,70)       # Nom de l'intervenant
                                    enreg_param += maxi(sale.partner_paye_par_id.street,35)     # Ligne adresse 1 intervenant    
                                    enreg_param += maxi(sale.partner_paye_par_id.street2,35)    # Ligne adresse 2 intervenant
                                    enreg_param += maxi(espace,35)                              # Ligne adresse 3 intervenant
                                    enreg_param += maxi(sale.partner_paye_par_id.zip,9)         # Code postal intervenant
                                    enreg_param += maxi(sale.partner_paye_par_id.city,35)       # Ville intervenant
                                    enreg_param += maxi(sale.partner_paye_par_id.country_id.code,2)  # Code pays intervenant
                                    if sale.partner_paye_par_id.siret:
                                        if len(sale.partner_paye_par_id.siret)>=9:
                                            siren = sale.partner_paye_par_id.siret[0:9]    
                                        else:
                                            siren = ''  
                                    else:
                                        siren = ''                                              
                                    enreg_param += maxi(siren,20)                               # Identification Complémentaire 1
                                    type_id = 'XA'
                                    enreg_param += maxi(type_id,3)                              # Type identification 1
                                    enreg_param += maxi(sale.partner_paye_par_id.vat,20)        # Identification Complémentaire 2
                                    type_id = 'VA'
                                    enreg_param += maxi(type_id,3)                              # Type identification 2                                                                             
                                    enreg_param += maxi(sale.partner_paye_par_id.siret,20)      # Identification Complémentaire 3
                                    type_id = 'GN'
                                    enreg_param += maxi(type_id,3)                              # Type identification 3
                                else:
                                    if typ_interv == 'UD':
                                        enreg_param += 'UD '                                        # Type d'intervenant (qualifiant)
                                        enreg_param += maxi(sale.partner_final_ud_id.code_gln,20)   # Code identifiant de l'intervenant
                                        enreg_param += maxi(espace,3)                               # Type d'identifiant
                                        enreg_param += maxi(sale.partner_final_ud_id.name,70)       # Nom de l'intervenant
                                        enreg_param += maxi(sale.partner_final_ud_id.street,35)     # Ligne adresse 1 intervenant    
                                        enreg_param += maxi(sale.partner_final_ud_id.street2,35)    # Ligne adresse 2 intervenant
                                        enreg_param += maxi(espace,35)                              # Ligne adresse 3 intervenant
                                        enreg_param += maxi(sale.partner_final_ud_id.zip,9)         # Code postal intervenant
                                        enreg_param += maxi(sale.partner_final_ud_id.city,35)       # Ville intervenant
                                        enreg_param += maxi(sale.partner_final_ud_id.country_id.code,2) # Code pays intervenant
                                        if sale.partner_final_ud_id.siret:
                                            if len(sale.partner_final_ud_id.siret)>=9:
                                                siren = sale.partner_final_ud_id.siret[0:9]    
                                            else:
                                                siren = '' 
                                        else:
                                            siren = ''                                               
                                        enreg_param += maxi(siren,20)                               # Identification Complémentaire 1
                                        type_id = 'XA'
                                        enreg_param += maxi(type_id,3)                              # Type identification 1
                                        enreg_param += maxi(sale.partner_final_ud_id.vat,20)        # Identification Complémentaire 2
                                        type_id = 'VA'
                                        enreg_param += maxi(type_id,3)                              # Type identification 2                                                                                 
                                        enreg_param += maxi(sale.partner_final_ud_id.siret,20)      # Identification Complémentaire 3
                                        type_id = 'GN'
                                        enreg_param += maxi(type_id,3)                              # Type identification 3
                                    else:
                                        enreg_param += 'SU '                                        # Type d'intervenant (qualifiant)
                                        enreg_param += maxi(sale.partner_vendeur_id.code_gln,20)    # Code identifiant de l'intervenant
                                        enreg_param += maxi(espace,3)                               # Type d'identifiant
                                        enreg_param += maxi(sale.partner_vendeur_id.name,70)        # Nom de l'intervenant
                                        enreg_param += maxi(sale.partner_vendeur_id.street,35)      # Ligne adresse 1 intervenant    
                                        enreg_param += maxi(sale.partner_vendeur_id.street2,35)     # Ligne adresse 2 intervenant
                                        enreg_param += maxi(espace,35)                              # Ligne adresse 3 intervenant
                                        enreg_param += maxi(sale.partner_vendeur_id.zip,9)          # Code postal intervenant
                                        enreg_param += maxi(sale.partner_vendeur_id.city,35)        # Ville intervenant
                                        enreg_param += maxi(sale.partner_vendeur_id.country_id.code,2) # Code pays intervenant
                                        if sale.partner_vendeur_id.siret:
                                            if len(sale.partner_vendeur_id.siret)>=9:
                                                siren = sale.partner_vendeur_id.siret[0:9]    
                                            else:
                                                siren = ''     
                                        else:
                                            siren = ''                                           
                                        enreg_param += maxi(siren,20)                               # Identification Complémentaire 1
                                        type_id = 'XA'
                                        enreg_param += maxi(type_id,3)                              # Type identification 1
                                        enreg_param += maxi(sale.partner_vendeur_id.vat,20)         # Identification Complémentaire 2
                                        type_id = 'VA'
                                        enreg_param += maxi(type_id,3)                              # Type identification 2                                                                                
                                        enreg_param += maxi(sale.partner_vendeur_id.siret,20)       # Identification Complémentaire 3
                                        type_id = 'GN'
                                        enreg_param += maxi(type_id,3)                              # Type identification 3
        
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
    def export_invoic_ligne(self,move,sale,line,nb_line_invoice): 

        espace       = ' '
        enreg_ligne  = 'LIG'                                        #   M   3	LIG  
        #if line.sale_line_ids:
        #    for line_cde in line.sale_line_ids:
        #        enreg_ligne	+= maxi(line_cde.no_ligne_edi,6)    #	M   6	n° de ligne article
        #        break
        #else:
        #    enreg_ligne	+= maxi(espace,6)                       #	M   6	n° de ligne article

        nb_line_invoice_str = str(nb_line_invoice)
        enreg_ligne	+= maxi(nb_line_invoice_str,6)                  #	M   6	n° de ligne article
        enreg_ligne	+= maxi(line.product_id.barcode,35)             #   M   35	Code EAN article
        enreg_ligne += maxi(espace,35)                              #	C   35	Code article vendeur
        enreg_ligne += maxi(espace,35)                              #	C   35	Code article acheteur
        desc_ligne = self.suppression_retour_chariot_ligne(line.name)
        enreg_ligne += maxi(desc_ligne,140)                         #	M   140	Description article
        enreg_ligne += maxi(espace,140)                             #	M   140	Certification Bio        

        enreg_ligne += maxi(str(line.quantity),15)                  #	M   15	Quantité facturée
        enreg_ligne += maxi(line.product_uom_id.unite_edi,3)        #	M   3	Unité de quantité facturée
        enreg_ligne += maxi(espace,15)                              #	M   15	Quantité gratuite
        enreg_ligne += maxi(espace,3)                               #	M   3	Unité de quantité gratuite
        enreg_ligne += maxi(espace,15)                              #	C   15	Quantité par colis (PCB)
        enreg_ligne += maxi(espace,3)                               #	C   3	Unité de quantité par colis

        enreg_ligne += maxi(str(line.price_subtotal),18)             #	M   18	Montant net de ligne
        enreg_ligne += maxi(str(line.price_unit),15)                 #	M   15	Prix brut unitaire
        prixpar = "1"
        enreg_ligne += maxi(prixpar,9)                               #	M   9	Base de prix brut unitaire
        enreg_ligne += maxi(str(line.product_uom_id.unite_edi),3)    #	M   3	Unité de base de prix brut unitaire
        if line.quantity:
            punet = line.price_subtotal / line.quantity
        else:
            punet = 0   
        punet_str = str('%.2f'%round(punet,2))    
        enreg_ligne += maxi(punet_str,15)                            #	M   15	Prix net unitaire
        prixpar = "1"
        enreg_ligne += maxi(prixpar,9)                               #	M   9	Base de prix net unitaire
        enreg_ligne += maxi(str(line.product_uom_id.unite_edi),3)    #	M   3	Unité de base de prix net unitaire
        taux_tva = self.recherche_taux_tva_ligne(line.tax_ids)
        enreg_ligne += maxi(str(taux_tva),5)                         #	C   5	Taux de TVA
        rff_li = self.recherche_rff_li_ligne_commande(move,sale,line)
        enreg_ligne += maxi(rff_li,6)                                #	C   6	No Ligne de commande ERP Client (RFF+LI)
        
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
    #                               Export Enregistrement Pied                              #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_pied(self,move): 

        espace      = ' '
        enreg_pied  = 'PIE'                                    #    M   3	PIE    
        enreg_pied += maxi(str(move.amount_untaxed),18)        #    M   18	Montant taxable
        enreg_pied += maxi(str(move.amount_total),18)          #    M   18	Montant TTC
        enreg_pied += maxi(str(move.amount_tax),18)            #	M   18	Montant Taxe
        enreg_pied += maxi(espace,18)                          #	C   18	Montant net ristournable
        enreg_pied += maxi(espace,18)                          #	C   18	Montant total des taxes dont parafiscales
        enreg_pied += maxi(str(move.amount_untaxed),18)        #	C   18	Montant total des lignes (MOA+79)

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
        enreg_taxe += maxi(espace,3)                           #	M   3	Catégorie TVA
        enreg_taxe += maxi(mtt_tva,18)                         #	M   18	Montant TVA

        return enreg_taxe    

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement TPP                               #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_tpp(self,move): 
        espace      = ' '        
        enreg_tpp  = 'TPP'                                     #    M   3	TPP    
        enreg_tpp += maxi(espace,35)                           #    M   35	Libellé de la Taxe parafiscale
        enreg_tpp += maxi(espace,20)                           #    M   20	Code (EAN) Taxe parafiscale
        enreg_tpp += maxi(espace,9)                            #	M   18	Montant Taxe parafiscale
        return enreg_tpp    

    #########################################################################################
    #                                                                                       #
    #                               Export Enregistrement COM                               #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_com(self,move,sale): 
        company =  self.env.company 
        espace      = ' '        
        enreg_com  = 'COM'                                           #    M   3	COM    
        if sale.partner_facture_a_id:
            if sale.partner_facture_a_id.factor:
                enreg_com += maxi(company.client_factor_text,350)   #    M   350	Texte conditions d'escompte
            else:
                enreg_com += maxi(company.cond_escompte_text,350)   #    M   350	Texte conditions d'escompte
        else:
            if move.partner_id.factor:
                enreg_com += maxi(company.client_factor_text,350)   #    M   350	Texte conditions d'escompte
            else:
                enreg_com += maxi(company.cond_escompte_text,350)   #    M   350	Texte conditions d'escompte    
        enreg_com += maxi(company.resa_proprio_text,350)            #    M   350	Mention légale  
        enreg_com += maxi(company.penal_retard_text,350)            #    M   350	Texte conditions de pénalités       
               
        if move.fiscal_position_id.regime_tva_edi == '3' or move.fiscal_position_id.regime_tva_edi == 3:
            enreg_com += maxi(move.fiscal_position_id.note,350)     #    M   350	Texte exonération de TVA 
        else:    
            enreg_com += maxi(espace,350)                           #    M   350	Texte exonération de TVA 
        enreg_com += maxi(espace,350)                               #    M   350	Commentaires Fournisseurs  
        return enreg_com      

    #########################################################################################
    #                                                                                       #
    #                Export Enregistrement REG : Remise ou charge globale                   #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_reg(self,move,sale,type): 
        # 
        # On recherche la ligne de remise globale de la facture 
        #
        ligne_trouve = False
        company =  self.env.company 
        ligne = self.env['account.move.line'].search([('move_id', '=', move.id),('product_id','=',company.product_rem_global_id.id)],limit=1)
        if ligne:
            espace      = ' '        
            enreg_reg  = 'REG'                                     #    M   3	REG 
            enreg_reg += maxi(type,1)                              #    M   1	Type remise ou charge R = remise, C = taxe
            enreg_reg += maxi(company.product_rem_global_id.description_sale,35) #    M   35	Libellé remise ou charge
            code_remise = 'TD'
            enreg_reg += maxi(code_remise,35)                      #    M   35	Code remise ou charge     
            enreg_reg += maxi(str(ligne.price_subtotal),9)         #    M   9	Montant remise ou charge
            enreg_reg += maxi(str(sale.global_discount),5)         #    M   5	Pourcentage remise ou charge 
            taux_tva = self.recherche_taux_tva_ligne(ligne.tax_ids)
            enreg_reg += maxi(str(taux_tva),5)                     #    M   5	Taux de TVA remise ou charge
            enreg_reg += maxi(company.product_rem_global_id.barcode,20)  #    M   20	Code (EAN)  charge taxe parfiscale
            etape = '1'
            enreg_reg += maxi(etape,2)                             #    M   2	Etape de Calcul
            type_regl = '2'
            enreg_reg += maxi(type_regl,1)                         #    M   1	Reglement 1=Hors Facture, 2=Déduit de la facture
            return enreg_reg   
        else:
            return False    

    #########################################################################################
    #                                                                                       #
    #                Export Enregistrement REG : Remise ou charge globale                   #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_reg_frais_transport(self,move,sale,type): 
        # 
        # On recherche la ligne de remise globale de la facture 
        #
        ligne_trouve = False
        company =  self.env.company 
        ligne = self.env['account.move.line'].search([('move_id', '=', move.id),('product_id.art_frais_transport','=',True)],limit=1)
        if ligne:
            espace      = ' '        
            enreg_reg  = 'REG'                                     #    M   3	REG 
            enreg_reg += maxi(type,1)                              #    M   1	Type remise ou charge R = remise, C = taxe
            enreg_reg += maxi(ligne.product_id.name,35)            #    M   35	Libellé remise ou charge
            code_frais = 'FC'
            enreg_reg += maxi(code_frais,35)                       #    M   35	Code remise ou charge  
            enreg_reg += maxi(str(ligne.price_subtotal),9)         #    M   9	Montant remise ou charge
            enreg_reg += maxi(espace,5)                            #    M   5	Pourcentage remise ou charge 
            taux_tva = self.recherche_taux_tva_ligne(ligne.tax_ids)
            enreg_reg += maxi(str(taux_tva),5)                     #    M   5	Taux de TVA remise ou charge
            enreg_reg += maxi(ligne.product_id.barcode,20)         #    M   20	Code (EAN)  charge taxe parfiscale
            etape = '1'
            enreg_reg += maxi(etape,2)                             #    M   2	Etape de Calcul
            type_regl = '2'
            enreg_reg += maxi(type_regl,1)                         #    M   1	Reglement 1=Hors Facture, 2=Déduit de la facture
            return enreg_reg   
        else:
            return False                

    #########################################################################################
    #                                                                                       #
    #                  Export Enregistrement REL : Remise ou charge lignes                  #
    #                                                                                       #
    #########################################################################################   
    def export_invoic_rel(self,move,sale,line,type,num,nb_rem): 
        espace     = ' '        
        enreg_rel  = 'REL'                                     #    M   3	REL 
        enreg_rel += maxi(type,1)                              #    M   1	Type remise ou charge R = remise, C = taxe
        code_remise = 'TD'
        enreg_rel += maxi(code_remise,35)                      #    M   35	Code remise ou charge  
        librem = "Remise commerciale"
        enreg_rel += maxi(librem,35)                           #    M   35	Libellé remise ou charge
        txrem = 0
        if num == '1':
            txrem = line.discount 
        else:
            if num == '2':
                txrem = line.discount2 
            else:
                txrem = line.discount3   

        #mttrem = line.price_unit * (txrem/100)
        mttrem = 0
        enreg_rel += maxi(str(mttrem),9)                       #    M   9	Montant remise ou charge
        enreg_rel += maxi(str(txrem),5)                        #    M   5	Pourcentage remise ou charge 

        taux_tva = self.recherche_taux_tva_ligne(line.tax_ids)
        enreg_rel += maxi(str(taux_tva),5)                     #    M   5	Taux de TVA remise ou charge
        enreg_rel += maxi(espace,20)                           #    M   20	Code (EAN)  charge taxe parfiscale
        enreg_rel += maxi(str(nb_rem),2)                       #    M   2	Etape de Calcul
        type_regl = '2'
        enreg_rel += maxi(type_regl,1)                         #    M   1	Reglement 1=Hors Facture, 2=Déduit de la facture
        return enreg_rel                         

    #########################################################################################
    #                                                                                       #
    #              Recherche de la RFF+LI de la ligne de commande correspondante            #
    #                                                                                       #
    #########################################################################################   
    def recherche_rff_li_ligne_commande(self,move,sale,line): 
        rff_li = ''
        if line.sale_line_ids:
            for line_cde in line.sale_line_ids:
                if line_cde.no_lig_erp_cli:
                    rff_li = line_cde.no_lig_erp_cli
                    break                
        else:
            rff_li = ''    

        return rff_li

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
    #                                    Génération mail                                    #
    #                                                                                       #
    #########################################################################################
    def edi_generation_mail(self, destinataire, sujet, corps):
        #
        # On envoie un mail au destinataire reçu
        #
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
        
    #########################################################################################
    #                                                                                       #
    #                                     Génération erreur EDI                             #
    #                                                                                       #
    #########################################################################################
    def edi_generation_erreur(self, erreur, flux, sujet, corps):
        #
        # On cree un enregistrement dans le suivi EDI
        #
        company =  self.env.company 
        suivi_edi = self.env['suivi.edi']
        today = fields.Date.from_string(fields.Date.context_today(self))
        if len(sujet)>0:
            suivi_data = {
                        'company_id': company.id,
                        'name': sujet,
                        'libelle_mvt_edi': corps,
                        'flux_id': flux.id,
                        'erreur_id': erreur.id,                        
                        }

            suivi = suivi_edi.create(suivi_data)                  
              
    #########################################################################################
    #                                                                                       #
    #                                Recherche Commande Origine                             #
    #                                                                                       #
    #########################################################################################
    def recherche_commande_origin(self,invoice_origin):
        if invoice_origin:
            for origin in invoice_origin.split():
                if origin != ',': 
                    sale = self.env['sale.order'].search([('name', '=', origin)],limit=1)
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
        livraison = ''
        if sale:
            bl_trouve = False
            pickings = self.env['stock.picking'].search([('sale_id', '=', sale.id),('state','=','done')])
            if len(pickings)>0:
                for picking in pickings:
                    if picking.picking_type_id.desadv_edi:
                        bl_trouve = True
                        break
            if bl_trouve:
                livraison = picking
            else:
                livraison = ''            

        return livraison

    #########################################################################################
    #                                                                                       #
    #                        Calcul du nombre de jours avant l'échéance                     #
    #                                                                                       #
    #########################################################################################
    def calcul_nb_jours_echeance(self,echeance):
        today = fields.Datetime.now()
        nb_jour = 0 
        if echeance:
            date_jour = date.today()
            nb_entier = (echeance - date_jour)
            nb_jour = nb_entier.days
        else:
            nb_jour = 0   

        return nb_jour     

    #########################################################################################
    #                                                                                       #
    #                        Calcul de la date d'échéance de la facture                     #
    #                                                                                       #
    #########################################################################################
    def calcul_date_echeance_facture(self,move):
        if not move.invoice_date_due:
            date_ech = move.invoice_date
        else:
            date_ech = move.invoice_date_due    

        return date_ech

    #########################################################################################
    #                                                                                       #
    #                           Recherche du taux de TVA de la ligne                        #
    #                                                                                       #
    #########################################################################################
    def recherche_taux_tva_ligne(self,tax_ids):
        tx_tva = ''
        if tax_ids:
            for tax in tax_ids:
                tx_tva = tax.amount
                break            
        else:
            tx_tva = ''   

        return tx_tva        
