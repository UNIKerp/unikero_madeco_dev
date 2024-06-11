# -*- coding: utf-8 -*-

import base64
import io
import os
import ftplib
from tempfile import TemporaryFile

from numpy import delete
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
import traceback 
logger = logging.getLogger(__name__)


class UNIKArcCommandePrestaExport(models.TransientModel):
    _name = "apik_prestashop.majof"
    _description = "Mise à jour des OF"
    
    
    #########################################################################################
    #                                                                                       #
    #                          Bouton Export des ARC de commandes PrestaShop                #
    #                                                                                       #
    #########################################################################################        
    """def export_arc_cde_presta(self):  
        self.ensure_one()
        today = fields.Date.to_string(datetime.now())
        company_id =  self.env.company               

        if self.export_auto:
            sale_ids = self.env['sale.order'].search([('state','=','sale'),('company_id','=',company_id.id),('commande_presta','=',True),('arc_presta_genere','=',True),('arc_presta_envoye','=',False)])
        else:    
            sale_ids = self.env['sale.order'].search([('id', 'in', self._context.get('active_ids', True))])
        
        nb_enreg = 1
        rows_to_write = []
        for sale in sale_ids: 
            if sale.partner_id.client_presta:
                #
                # On génére l'enregistrement Entête
                #
                # enreg_ent = sale.no_cde_presta + ";" + sale.name + ";"
                #########################################################################################
                #                                                                                       #
                #  UNIKerp : Modification de la Structure du Fichier ARCWEB pour ajouter                #
                #       Couple « REFPRESTA-IDCONF »                                                     #
                #       N° d’OF (vide si commande d’achat)                                              #
                #       N° de commande d’achat (vide si OF)                                             #
                #########################################################################################   
                for l in sale.order_line:
                    enreg_ent_line = sale.no_cde_presta + ";" + sale.name + ";"
                    if l.product_id.typologie_article  == 'A3':
                        enreg_ent_line = enreg_ent_line + l.unik_ref_prestashop +";"
                        ref_of = ''
                        ref_cde_achat = ''
                        if l.ordre_fabrication_id:
                            ref_of = l.ordre_fabrication_id.name 
                        elif l.bon_commande_id:
                            ref_cde_achat = l.bon_commande_id.name
                        enreg_ent_line = enreg_ent_line + ref_of + ";" + ref_cde_achat + ";"
                    if enreg_ent_line:
                        rows_to_write.append(enreg_ent_line)
                        nb_enreg = nb_enreg + 1                
            else:
                client = self.env['res.partner'].search([('id','=', sale.partner_id.id)],limit=1)
                #
                # Erreur sur envoi cde 
                #
                sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Enregistrement des ARC de commandes du ' + str(today) 
                corps = "Le client {} n'est pas en gestion PrestaShop. <br/><br>".format(client.name) 
                corps+= "L'ARC n'est pas envoyé. <br/><br>"                         
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.presta_generation_mail(destinataire, sujet, corps)
                code_erreur = self.env['erreur.presta'].search([('name','=', '0400')], limit=1) 
                message = "Le client {} n'est pas en gestion PrestaShop. L'ARC n'est pas envoyé. ".format(client.name) 
                self.presta_generation_erreur(code_erreur, sujet, message) 
            
            #
            # On met à jour la commande
            #
            sale.write({'arc_presta_envoye': True}) 

            client = self.env['res.partner'].search([('id','=', sale.partner_id.id)],limit=1)
            #
            # Envoi ARC : Envoi généré
            #
            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Enregistrement des commandes du ' + str(today) 
            corps = "L'ARC de la commande {} pour le client {} a été envoyé. <br/><br>".format(sale.name, client.name) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.presta_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.presta'].search([('name','=', '0600')], limit=1) 
            message = "L'ARC de la commande {} pour le client {} a été envoyé. ".format(sale.name, client.name) 
            self.presta_generation_erreur(code_erreur, sujet, message)
            
        #
        # on écrit le fichier d'export
        #
        if nb_enreg >= 1:  
            logger.info("__________________________")
            logger.info(rows_to_write)   
            logger.info("__________________________")
       
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
                    rep_envoi_ftp = param.repertoire_envoi_arc_cde_presta

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
                    rep_envoi_sftp = param.repertoire_envoi_arc_cde_presta
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
            # Envoi ARC : Fichier généré
            #
            sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Envoi des ARC de commandes du ' + str(today) 
            corps = "Le fichier {} des ARC de commande client a été envoyé. <br/><br>".format(fichier_arc) 
            corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
            destinataire = company_id.gestion_user_id.email
            if destinataire:
                self.presta_generation_mail(destinataire, sujet, corps)
            code_erreur = self.env['erreur.presta'].search([('name','=', '0602')], limit=1) 
            message = "Le fichier {} des ARC de commande client a été envoyé.".format(fichier_arc)
            self.presta_generation_erreur(code_erreur, sujet, message)    
        else:
            raise UserError(_("Aucun accusé de commande PrestaShop à envoyer."))"""          
     
     
    #########################
    ###############################
    # Mise à jour des OF prestashop UNIKerp
    ############################
    def mise_a_jour_of_prestashop(self):
        company_id =  self.env.company 
        today = fields.Date.to_string(datetime.now())
        param = self.env['parametre.presta'].search([('id', '=', company_id.param_presta_id.id)])
        if len(param)>0:  
            if param.type_connexion == 'ftp':
                ftp_user = param.compte_ftp_presta.strip()
                ftp_password = param.mdp_presta.strip()
                adresse_ftp = param.adresse_ftp.strip()
                ftp_port = param.port_ftp
                rep_recup_ftp = param.repertoire_maj_of.strip()                 
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
                is_correct = False
                rep_archive_maj_of = param.rep_archive_maj_of.strip()
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
                        #
                        dest = "/"+rep_archive_maj_of+fichier_import
                        with open(fich_integ_presta,'rb') as fp:
                            ftp.storbinary('STOR '+ dest, fp)
                        #    
                        with fichier_cde_presta as f:
                            ftp.retrbinary('RETR ' + fichier_import, f.write)          
                        fichier_donnees_presta = os.path.basename(fich_integ_presta)    
                        with open(fich_integ_presta, "rb") as fileread:
                            byte_data = fileread.read()
                        file_bytes = byte_data
                        fileobj.write(file_bytes)
                        fileobj.seek(0)
                        decoded_string = file_bytes.decode('utf-8')
                        fileobj.close()
                        for l in decoded_string.split('\n'):
                            nbr_enregistr = l.split(';')
                            if len(nbr_enregistr) == 3:
                                numero_of = l.split(';')[0]
                                ref_product = l.split(';')[1]
                                qty_maj = l.split(';')[2]
                                of_id = self.env['mrp.production'].search([('name','=',numero_of)])
                                lines_product_list = []
                                if of_id:
                                    product_id = self.env['product.product'].search([('default_code','=',ref_product)])	 
                                    location_id = self.env['stock.location'].search([('id','=',60)])
                                    if of_id.move_raw_ids:
                                        for line in  of_id.move_raw_ids:
                                            lines_product_list.append(line.product_id.id)
                                    if product_id:
                                        if product_id.id not in lines_product_list:
                                            self.env['stock.move'].sudo().create({
                                                'raw_material_production_id':of_id.id,
                                                'product_id':product_id.id,
                                                'name':product_id.name,
                                                'product_uom_qty':float(qty_maj),
                                                'product_uom':product_id.uom_id.id,
                                                'location_id':location_id.id,
                                                'location_dest_id':product_id.property_stock_production.id
                                            })
                                            is_correct = True
                                        else:
                                            lines = self.env['stock.move'].search([('product_id','=',product_id.id),('raw_material_production_id','=',of_id.id)])
                                            for l in lines:
                                                l.write({'product_uom_qty':float(qty_maj)})
                                                is_correct = True
                                    else:
                                        code_erreur = self.env['erreur.presta'].search([('name','=', '0300')], limit=1)
                                        message = "Fichier "+fichier_import+" Le produit avec la réference "+ref_product+ "n'existe pas"
                                        self.env['suivi.presta'].create({
                                            'name':str(self.env.company.name) + ' - Gestion PrestaShop - ERREUR Mise à jour OF du  ' + str(today),
                                            'date_mvt_presta':today,
                                            'erreur_id':code_erreur.id,
                                            'company_id':company_id.id,
                                            'libelle_mvt_presta':message,
                                        })
                                else:
                                    code_erreur = self.env['erreur.presta'].search([('name','=', '0300')], limit=1)
                                    message =  "Fichier "+fichier_import+" Le OF numéro "+numero_of+ " n'existe pas"
                                    self.env['suivi.presta'].create({
                                        'name':str(self.env.company.name) + ' - Gestion PrestaShop - ERREUR Mise à jour OF du  ' + str(today),
                                        'date_mvt_presta':today,
                                        'erreur_id':code_erreur.id,
                                        'company_id':company_id.id,
                                        'libelle_mvt_presta':message,
                                    })
                            else:
                                code_erreur = self.env['erreur.presta'].search([('name','=', '0300')], limit=1)
                                message = "La ligne "+l+" du fichier "+fichier_import+" est incorrecte"
                                self.env['suivi.presta'].create({
                                    'name':str(self.env.company.name) + ' - Gestion PrestaShop - ERREUR Mise à jour OF du  ' + str(today),
                                    'date_mvt_presta':today,
                                    'erreur_id':code_erreur.id,
                                    'company_id':company_id.id,
                                    'libelle_mvt_presta':message,
                                })
                    if is_correct == True:
                        code_erreur = self.env['erreur.presta'].search([('name','=', '0200')], limit=1)
                        message = "Le fichier {} a été mise à jour dans odoo.".format(fichier_import)
                        self.env['suivi.presta'].create({
                            'name':str(self.env.company.name) + ' - Gestion PrestaShop - Mise à jour des OF du  ' + str(today),
                            'date_mvt_presta':today,
                            'erreur_id':code_erreur.id,
                            'company_id':company_id.id,
                            'libelle_mvt_presta':message,
                        })
                        print("----------------------------- La mise à jour a bien réussie ----------------------")
                        print(fichier_import)
                        print("----------------------------- La mise à jour a bien réussie ----------------------")
                    ftp.delete(filename)
                ftp.quit()       
            else: 
                sftp_user = param.compte_ftp_presta.strip()
                sftp_password = param.mdp_presta.strip()
                sftp_url = param.adresse_ftp.strip()
                sftp_port = param.port_ftp
                rep_recup_sftp = param.repertoire_maj_of.strip()                     
                rep_import = '/tmp'
                fich_path = rep_import
                fichier_import = '*.csv'
                fich_presta = fich_path + '/%s' % fichier_import
                cnopts = pysftp.CnOpts()
                cnopts.hostkeys = None
                with pysftp.Connection(host=sftp_url,username=sftp_user,password=sftp_password,port=int(sftp_port),cnopts=cnopts) as sftp:
                    sftp.chdir(rep_recup_sftp)
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
                        fileobj.seek(0)
                        decoded_string = file_bytes.decode('utf-8')
                        fileobj.close()
                        for l in decoded_string.split('\n'):
                            nbr_enregistr = l.split(';')
                            if len(nbr_enregistr) == 3:
                                numero_of = l.split(';')[0]
                                ref_product = l.split(';')[1]
                                qty_maj = l.split(';')[2]
                                of_id = self.env['mrp.production'].search([('name','=',numero_of)])
                                if of_id:
                                    if of_id.move_raw_ids:
                                        for line in of_id.move_raw_ids:
                                            if line.product_id.default_code == ref_product:
                                                line.sudo().write({'product_uom_qty':float(qty_maj)})
                        # sftp.delete(filename)           
                    sftp.quit()       
