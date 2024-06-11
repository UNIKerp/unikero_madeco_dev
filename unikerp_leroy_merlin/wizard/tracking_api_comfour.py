# -*- coding: utf-8 -*-

import base64
import io
import os
import ftplib
import csv
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


      
class TrackingAPICOMFOUR(models.TransientModel):
    _name = "api.comfour"
    _description = "Tracking API COMFOUR LDD LEROY MERLIN / MADECO"
    
    def tracking_api_comfour_ldd(self):
        today = fields.Date.to_string(datetime.now())  
        company_id =  self.env.company               
        sale_ids = self.env['sale.order'].search([('state','=','sale'),('company_id','=',company_id.id),('commande_edi','=',True),('comfour_envoye','=',False),('portail','=','PRT1')],limit=50)
        nb_enreg = 1
        rows_to_write = []
        for sale in sale_ids:
            if sale.no_contrat:
                no_contrat = sale.no_contrat.replace(' ','')
            else:
                no_contrat = ''
            enreg_ent_line = sale.partner_id.code_magasin +";"+ sale.no_cde_client +";"+ no_contrat +";" +sale.name+";"+ str(sale.date_order) +";"
            if enreg_ent_line:
                rows_to_write.append(enreg_ent_line)
                nb_enreg = nb_enreg + 1  
                    
            sale.write({'comfour_envoye': True})
            
        if nb_enreg >= 1:
            date_generation = fields.Datetime.now()
            date_fic = fields.Datetime.from_string(date_generation)
            datefic = date_fic.strftime("%d%m%Y%H%M%S")
            rep_export = '/mnt/extra-addons/unikerp_leroy_merlin/wizard/tmp/comfour.csv'
            gln_societe = company_id.partner_id.code_gln
            edi_obj = self.env['parametre.edi']
            nom_fichier = ''
            if company_id.param_edi_id:
                param = edi_obj.search([('id', '=', company_id.param_edi_id.id)])
                if len(param)>0:
                    if param.nom_fichier_prt:
                       nom_fichier_init = param.nom_fichier_prt+'_'+gln_societe+'_'+str(datefic)
                       nom_fichier = nom_fichier_init+'.csv'
                    else:
                        nom_fichier_init = 'PRT'+'_'+gln_societe+'_'+str(datefic)
            fichier_commande_comfour = open(rep_export, "w", encoding="latin_1")
            for rows in rows_to_write:
                retour_chariot = '\n'    #'\r\n'
                rows += retour_chariot
                fichier_commande_comfour.write(str(rows))
            fichier_commande_comfour.close()
            
           
            param = edi_obj.search([('id', '=', company_id.param_edi_id.id)])
            if len(param)>0: 
                if param.type_connexion == 'ftp':
                    try:
                        ftp_user = param.compte_ftp_edi
                        ftp_password = param.mdp_edi
                        adresse_ftp = param.adresse_ftp
                        ftp_port = param.port_ftp
                        rep_envoi_ftp = param.rep_prt
                        ftp = ftplib.FTP() 
                        ftp.connect(adresse_ftp, ftp_port, 30*5) 
                        ftp.login(ftp_user, ftp_password)             
                        passif=True
                        ftp.set_pasv(passif)
                        ftp.cwd(rep_envoi_ftp)
                        with open(rep_export,'rb') as fp:
                            print("===========================================================")
                            ftp.storbinary('STOR '+ nom_fichier, fp)
                        ftp.quit()
                    except:
                        print("====================================")
                        print("Erreur Connexion ou de repertoire dans FTP")
                        print("====================================")