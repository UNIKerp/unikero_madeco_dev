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
import logging
logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'  

    commande_edi = fields.Boolean(string="Commande EDI",default=False)
    partner_emet_id = fields.Many2one('res.partner',string="Partenaire EDI émetteur", copy=True)
    type_cde_id = fields.Many2one('type.flux',string="Type de commande EDI", copy=True)
    code_function_id = fields.Many2one('function.flux',string="Code fonction EDI", copy=True)
    date_enlev = fields.Datetime(string="Date d'enlèvement demandée", copy=True)                                                   
    no_contrat = fields.Char(string="No de contrat RFF+CT", copy=True)
    no_cde_rempl = fields.Char(string="No de commande remplacée RFF+PW", copy=True)
    no_ope_promo = fields.Char(string="No d'opération promotionnelle RFF+PD", copy=True)
    cond_liv = fields.Text(string="Conditions de livraison", copy=True)
    ref1_div = fields.Char(string="Numéro de commande fournisseur RFF+VN", copy=True)
    ref2_div = fields.Char(string="Numéro de commande magasin RFF+CR", copy=True)
    comment_edi = fields.Text(string="Commentaire EDI", copy=True)
    no_cde_client = fields.Char(string="No de commande client EDI BGM", copy=True)
    arc_edi_genere = fields.Boolean(string="Arc de commande EDI généré", copy=False, default=False)
    arc_edi_envoye = fields.Boolean(string="Arc de commande EDI envoyé", copy=False, default=False)
    partner_vendeur_id = fields.Many2one('res.partner',string="Vendeur EDI (NAD+SU)", copy=True)
    partner_final_id = fields.Many2one('res.partner',string="Client final EDI (NAD+UC)", copy=True)
    partner_acheteur_id = fields.Many2one('res.partner',string="Acheteur EDI (NAD+BY)", copy=True)
    partner_commande_par_id = fields.Many2one('res.partner',string="Commandé par EDI (NAD+OB)", copy=True)
    partner_paye_par_id = fields.Many2one('res.partner',string="Payé par EDI (NAD+PR)", copy=True)
    partner_livre_a_id = fields.Many2one('res.partner',string="Livré à EDI (NAD+DP)", copy=True)
    partner_facture_a_id = fields.Many2one('res.partner',string="Facturé à EDI (NAD+IV)", copy=True)
    edi_emetteur = fields.Char(string="Emetteur EDI", copy=True)
    edi_destinataire = fields.Char(string="Destinataire EDI", copy=True)
    ref_cde_client_edi = fields.Char(string="Référence de commande client EDI RFF+ON", copy=True)
    partner_final_ud_id = fields.Many2one('res.partner',string="Client final EDI (NAD+UD)", copy=True)
    segment_ftx_gen = fields.Boolean(string="Segment FTX+GEN", default=False, copy=True)
    comment_ftx_gen = fields.Text(string="Commentaire FTX+GEN", copy=True)
    reponse_cde_edi = fields.Selection([('29', 'Accpeté sans modification'),('27', 'Non accepté'),], 
        required=True, default='29',string="Réponse à la commande EDI", copy=False)
    motif_refus_edi = fields.Char(string="Motif refus de la commande EDI", copy=False)
    date_devis_edi = fields.Datetime(string="Date du devis")
    ref_cde_client_final_edi = fields.Char(string="Référence de commande client final EDI RFF+UC", copy=True)


    def action_confirm(self):
        #
        # On regarde si le client est en EDI et si la gestion des ARC EDI est active
        #        
        if self.partner_id.client_edi:
            if self.partner_id.edi_ordrsp:
                self.arc_edi_genere = True
            else:
                self.arc_edi_genere = False
                #
                # On envoie un mail et on met à jour le suivi EDI
                #     
                today = fields.Date.to_string(datetime.now())        
                company_id =  self.env.company 
                sujet = str(self.env.company.name) + ' - Gestion EDI - Commandes client du ' + str(today) 
                corps = "La commande {} a été validée. L'ARC de commande n'est pas actif pour le client {}. <br/><br>".format(self.name,self.partner_id.name) 
                corps+= "La pièce est en devis dans votre ERP. <br/><br>"                         
                corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                destinataire = company_id.gestion_user_id.email
                if destinataire:
                    self.edi_generation_mail(destinataire, sujet, corps)
                code_erreur = self.env['erreur.edi'].search([('name','=', '0402')], limit=1) 
                flux = self.env['flux.edi'].search([('name','=', 'ORDERS')], limit=1)
                message = "La commande {} a été validée. L'ARC de commande n'est pas actif pour le client {}.".format(self.name,self.partner_id.name) 
                self.edi_generation_erreur(code_erreur, flux, sujet, message)                    
        else:
            self.arc_edi_genere = False       
            
        return super().action_confirm()        
        

    def recherche_nom_picking_cmde(self, pick, sale):
        nom_bl = ''
        if sale:
            pickings = sorted(sale.picking_ids, key=lambda b: b.id, reverse=True)
            for picking in pickings:
                if picking.state not in ('done','cancel'):
                    if picking.id < pick.id:
                        nom_bl = picking.name
                        break
        return nom_bl    

    def _prepare_confirmation_values(self):
        #
        # On regarde si c'est une commande EDI  
        # 
        if self.commande_edi:
            if self.date_devis_edi:
                return {
                    'state':'sale',
                    'date_order': self.date_devis_edi,
                    }
            else:
                return super()._prepare_confirmation_values()
        else:
            return super()._prepare_confirmation_values()       

    @api.onchange("motif_refus_edi")
    def onchange_motif_refus_edi(self):
        for sale in self:
            if sale.reponse_cde_edi == '27':
                if sale.motif_refus_edi:
                    if sale.partner_id.edi_ordrsp:
                        sale.arc_edi_genere = True                  

    #########################################################################################
    #                                                                                       #
    #                                    Génération mail                                    #
    #                                                                                       #
    #########################################################################################
    def edi_generation_mail(self, destinataire, sujet, corps):
        #
        # On envoie un mail au destinataire reçu
        #
        mail_obj = self.env['mail.mail']
        if len(destinataire)>0:
            mail_data = {
                        'subject': sujet,
                        'body_html': corps,
                        'email_from': self.env.user.email,
                        'email_to': destinataire,                        
                        }
            mail_id = mail_obj.create(mail_data)
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
        company_id =  self.env.company 
        suivi_edi = self.env['suivi.edi']
        if len(sujet)>0:
            suivi_data = {
                        'company_id': company_id.id,
                        'name': sujet,
                        'libelle_mvt_edi': corps,
                        'flux_id': flux.id,
                        'erreur_id': erreur.id,                        
                        }

            suivi = suivi_edi.create(suivi_data)
