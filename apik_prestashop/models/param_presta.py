# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class ParametrePresta(models.Model):
    _name = 'parametre.presta'
    _description = 'Paramêtres PrestaShop'
    
    
    name = fields.Char(string="Paramètrage PrestaShop", required=True, store=True,translate=True)
    active = fields.Boolean('Active', default=True)
    adresse_ftp = fields.Char(string="Adresse FTP de connexion",required=True)
    compte_ftp_presta = fields.Char(string="Compte d'accès PrestaShop",required=True)
    mdp_presta = fields.Char(string="Mot de passe PrestaShop",required=True)
    port_ftp = fields.Integer(string="Port FTP PrestaShop", required=True)
    rep_export_interne_presta = fields.Char(string="Répertoire génération de fichier d'export", required=True)
    rep_import_interne_presta = fields.Char(string="Répertoire génération de fichier d'import", required=True)
    repertoire_recup_cde_presta = fields.Char(string="Répertoire de récupération commandes PrestaShop",required=True)
    repertoire_cde_presta_integre = fields.Char(string="Répertoire de commandes PrestaShop intégrées",required=True)
    repertoire_envoi_arc_cde_presta = fields.Char(string="Répertoire d'envoi de ARC PrestaShop",required=True)
    repertoire_envoi_livraison_presta = fields.Char(string="Répertoire d'envoi de commandes PrestaShop expédiées",required=True)
    repertoire_envoi_facture_presta = fields.Char(string="Répertoire d'envoi de factures PrestaShop",required=True)
    nom_fichier_cde_presta_export = fields.Char(string="Nom du fichier d'export des bons de commande", required=True)
    nom_fichier_arc_presta_export = fields.Char(string="Nom du fichier d'export des ARC", required=True)
    nom_fichier_liv_presta_export = fields.Char(string="Nom du fichier d'export des bons de livraison", required=True)
    nom_fichier_invoic_presta_export = fields.Char(string="Nom du fichier d'export des factures", required=True)
    type_connexion = fields.Selection([
        ('ftp', 'FTP'),
        ('sftp', 'SFTP'),
        ], string='Type de connexion', required=True, default="ftp")
    rep_sauvegarde_fichier_traite = fields.Char(string="Répertoire de sauvegarde des fichiers traités", required=True)
    rep_sauvegarde_fichier_erreur = fields.Char(string="Répertoire de sauvegarde des fichiers en erreur", required=True)

