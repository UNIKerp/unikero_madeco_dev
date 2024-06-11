# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)

class ParametreEDiExt(models.Model):
    _inherit = 'parametre.edi'
    
    rep_prt = fields.Char(string="Répertoire PRT")
    nom_fichier_prt = fields.Char(string="Nom fichier PRT")


class ParametrePrestaExt(models.Model):
    _inherit = 'parametre.presta'
    
    repertoire_maj_of = fields.Char(string="Répertoire MAJ OF PrestaShop")
    nom_fichier_maj_of = fields.Char(string="Nom du fichier MAJ OF")
    
    rep_archive_maj_of = fields.Char(string="Répertoire archiveOF")
    nom_archive_maj_of = fields.Char(string="Nom archive OF")
    