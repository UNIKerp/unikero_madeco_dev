# -*- coding: utf-8 -*-

#import json
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime, timedelta
from tempfile import TemporaryFile
import base64,pysftp,ftplib
import io
import logging
logger = logging.getLogger(__name__)

class SaleOrderExt(models.Model):
    _inherit = 'sale.order'
    
    def test_connexion(self):
        company_id =  self.env.company
        presta_obj = self.env['parametre.presta']
        param = presta_obj.search([('id', '=', company_id.param_presta_id.id)])
        if len(param)>0: 
            if param.type_connexion == 'ftp':  
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
                ftp.retrlines('LIST') 
                ftp.quit() 
            else:                      
                sftp_url = param.adresse_ftp
                sftp_user = param.compte_ftp_presta
                sftp_password = param.mdp_presta
                sftp_port = param.port_ftp
                rep_envoi_sftp = param.repertoire_envoi_livraison_presta
                cnopts = pysftp.CnOpts()
                cnopts.hostkeys = None

                # with pysftp.Connection(host=sftp_url,username=sftp_user,password=sftp_password,port=int(sftp_port),cnopts=cnopts) as sftp:
                #     # on ouvre le dossier envoi
                #     sftp.chdir(rep_envoi_sftp)
                #     # export des fichiers
                #     sftp.put(fichier_liv_dest,fichier_genere_dest)
                #     with open(fichier_genere_dest,"rb") as f:
                #         out = f.read()  