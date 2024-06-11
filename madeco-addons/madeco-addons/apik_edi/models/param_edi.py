# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class FluxEdi(models.Model):
    _name = 'parametre.edi'
    _description = 'Paramêtres EDI'
    
    
    name = fields.Char(string="Paramètrage EDI", required=True, store=True,translate=True)
    active = fields.Boolean('Active', default=True)
    adresse_ftp = fields.Char(string="Adresse FTP de connexion",required=True)
    repertoire_recup_edi = fields.Char(string="Répertoire de récupération données EDI",required=True)
    repertoire_envoi_edi = fields.Char(string="Répertoire d'envoi de données EDI",required=True)
    compte_ftp_edi = fields.Char(string="Compte d'accès EDI",required=True)
    mdp_edi = fields.Char(string="Mot de passe EDI",required=True)
    port_ftp = fields.Integer(string="Port FTP EDI", required=True)
    rep_export_interne_edi = fields.Char(string="Répertoire génération de fichier d'export", required=True)
    rep_import_interne_edi = fields.Char(string="Répertoire génération de fichier d'import", required=True)
    file_format = fields.Selection([
        ('edi_tx2', 'EDI (TX2)'),
        ('edi_agp', 'EDI (@Gp)'),
        ('edi_csv', 'EDI (csv)'),
        ], string='Format du fichier EDI', required=True, default="edi_csv")
    nom_fichier_cde_edi_import = fields.Char(string="Nom du fichier d'import des commandes", required=True)
    nom_fichier_arc_cde_edi_export = fields.Char(string="Nom du fichier d'export des accusés de commandes", required=True)
    rep_sauvegarde_fichier_traite = fields.Char(string="Répertoire de sauvegarde des fichiers traités", required=True)
    rep_sauvegarde_fichier_erreur = fields.Char(string="Répertoire de sauvegarde des fichiers en erreur", required=True)
    unite_par_defaut = fields.Many2one('uom.uom',string="Unité par défaut EDI", required=True)
    nom_fichier_desadv_edi_export = fields.Char(string="Nom du fichier d'export des bons de livraison", required=True)
    nom_fichier_invoic_edi_export = fields.Char(string="Nom du fichier d'export des factures", required=True)
    nom_fichier_modif_cde_edi_import = fields.Char(string="Nom du fichier d'import des changements de commandes", required=True)
    type_connexion = fields.Selection([
        ('ftp', 'FTP'),
        ('sftp', 'SFTP'),
        ], string='Type de connexion', required=True, default="ftp")

