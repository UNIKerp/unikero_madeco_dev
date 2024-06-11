# -*- coding: utf-8 -*-

import base64
import io
import inspect, os
import ftplib

from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning
from odoo.tools import float_is_zero, pycompat
from datetime import datetime, timedelta
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules import get_module_resource
from odoo.modules import get_module_path
from ftplib import FTP

import logging
logger = logging.getLogger(__name__)

class CopyBackupFTP(models.Model):
    _name = 'copy.backup.ftp'
    _description = 'Copy Database Backup'
    
    
    def copy_database(self):
        ftp_user = "preprod-8b74c2-odoo"
        ftp_password = "X$vIxrm}azb4"
        adresse_ftp = "nc1438.nexylan.net"
        ftp_port = 21
        rep_envoi_ftp ="/"
        ftp = ftplib.FTP() 
        ftp.connect(adresse_ftp, ftp_port, 30*5) 
        ftp.login(ftp_user, ftp_password)             
        passif=True
        ftp.set_pasv(passif)
        ftp.cwd(rep_envoi_ftp)
        directory_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        backup_filename = os.path.join(directory_path, 'test.zip')
        print(directory_path,backup_filename)
        #
        with open(backup_filename, "rb") as file:
            # use FTP's STOR command to upload the file
            ftp.storbinary(f"STOR {backup_filename}", file)