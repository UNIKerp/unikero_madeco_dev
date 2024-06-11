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

def maxi_0(chaine,size):  
    if type(chaine) == str:
        if len(chaine)>size:
            return chaine[:size]
        else:
            chaine2=''
            for i in range(size-len(chaine)):
                chaine2 += "0"
            chaine_ret = chaine2 + chaine  
            return chaine_ret
    else:
        chaine = ""
        for i in range(size):
            chaine += "0"
        return chaine         


class Picking(models.Model):
    _inherit = 'stock.picking' 

    carrier_id = fields.Many2one(string="Méthode de livraison")
    intrastat_transport_id = fields.Many2one('intrastat.transport_mode', string="Transport Mode",compute="_compute_transport_mode", inverse="_set_intrastat_transport_id",store=True)
    file_transport = fields.Binary('File transport')
    file_transport_name = fields.Char('File transport name')
    madeco_transport_id = fields.Many2one('madeco.transport', string="Mode of transport",compute="_compute_mode_of_transport", inverse="_set_madeco_transport_id",store=True)


    #########################################################################################
    #                                                                                       #
    #                                _compute_transport_mode                                #
    #                                                                                       #
    #########################################################################################     
    @api.depends('origin', 'create_date', 'write_date')
    def _compute_transport_mode(self):
        for pick in self:
            if pick.origin:
                sale = self.env['sale.order'].search([('name', '=', pick.origin)],limit=1)
                if len(sale)>0:
                    if sale.intrastat_transport_id:
                        pick.intrastat_transport_id = sale.intrastat_transport_id.id
                    else:
                        pick.intrastat_transport_id = False
                else:
                    pick.intrastat_transport_id = False
            else:
                pick.intrastat_transport_id = False

    #########################################################################################
    #                                                                                       #
    #                                _compute_mode_of_transport                             #
    #                                                                                       #
    #########################################################################################     
    @api.depends('origin', 'create_date', 'write_date')
    def _compute_mode_of_transport(self):
        for pick in self:
            if pick.origin:
                sale = self.env['sale.order'].search([('name', '=', pick.origin)],limit=1)
                if len(sale)>0:
                    if sale.madeco_transport_id:
                        pick.madeco_transport_id = sale.madeco_transport_id.id
                    else:
                        pick.madeco_transport_id = False
                else:
                    pick.madeco_transport_id = False
            else:
                pick.madeco_transport_id = False            

    #########################################################################################
    #                                                                                       #
    #                              _set_intrastat_transport_id                              #
    #                                                                                       #
    #########################################################################################

    def _set_intrastat_transport_id(self):
        for record in self:
            sale = self.env['sale.order'].search([('name', '=', record.origin)], limit=1)
            if sale:
                sale.write({'intrastat_transport_id': record.intrastat_transport_id.id if record.intrastat_transport_id else False})
    
    #########################################################################################
    #                                                                                       #
    #                                _set_madeco_transport_id                               #
    #                                                                                       #
    #########################################################################################

    def _set_madeco_transport_id(self):
        for record in self:
            sale = self.env['sale.order'].search([('name', '=', record.origin)], limit=1)
            if sale:
                sale.write({'madeco_transport_id': record.madeco_transport_id.id if record.madeco_transport_id else False})
    
    #########################################################################################
    #                                                                                       #
    #                                     Export Transport                                  #
    #                                                                                       #
    #########################################################################################     
    def button_validate(self): 
        resultat = super().button_validate()   
        if resultat:
            for p in self:
                if p.state == 'done':
                    if p.madeco_transport_id:
                        if p.picking_type_id.transport_edi:
                            if p.origin: 
                                #
                                # On regarde si le client est en EDI et si la gestion des DESADV EDI est active
                                #    
                                sale = self.env['sale.order'].search([('name', '=', p.origin)],limit=1)
                                if len(sale)>0:  
                                    if p.madeco_transport_id.type_envoi_edi:
                                        if p.madeco_transport_id.type_envoi_edi == 'heppner' :
                                            #
                                            # Transport Heppner
                                            # 
                                            action2 = p.export_heppner_edi_picking()
                                        else:
                                            if p.madeco_transport_id.type_envoi_edi == 'dpd' :
                                                #             
                                                # Transport Heppner 
                                                #
                                                action2 = p.export_dpd_edi_picking()
                                            else:
                                                if self.madeco_transport_id.type_envoi_edi == 'laposte' :
                                                    #     
                                                    # Etiquettes de transport LA POSTE
                                                    #                                                     
                                                    action2 = p.export_laposte_edi_picking()
                                                else:
                                                    return resultat                                            
                                        return p.return_multi_document(resultat, action2)
                                    else:
                                        return resultat    
                                else:
                                    return resultat                                 
                            else:
                                return resultat    
                        else:
                            return resultat 
                    else:
                        return resultat  
                else:
                    return resultat                         
        return resultat

    #########################################################################################
    #                                                                                       #
    #                                     Return_multi_document                             #
    #                                                                                       #
    ######################################################################################### 
    def return_multi_document(self, action1, action2):
        return {
            "type": 'ir.actions.act_multi',
            'actions': [
                action1,
                action2
            ]
        }    

    #########################################################################################
    #                                                                                       #
    #                          suppression caractères_accentués                             #
    #                                                                                       #
    #########################################################################################
    def suppression_caractere_accentues(self, libelle):
        libelle = libelle.replace('é','e') 
        libelle = libelle.replace('è','e') 
        libelle = libelle.replace('ê','e') 
        libelle = libelle.replace('à','a') 
        libelle = libelle.replace('û','u') 
        libelle = libelle.replace('ä','a') 
        libelle = libelle.replace('ë','e') 
        libelle = libelle.replace('ï','i')
        libelle = libelle.replace('ö','o') 
        libelle = libelle.replace('ü','u') 
        return libelle

    #########################################################################################
    #                                                                                       #
    #                                     Export Tps HEPPNER                                #
    #                                                                                       #
    #########################################################################################      
    def export_heppner_edi_picking(self):           
        self.ensure_one()
        today = fields.Date.to_string(datetime.now())
        for picking in self: 
            #
            # On recherche la commande de vente rattaché à la livraison
            #
            if picking.origin:
                nb_enreg = 0
                rows_to_write = []
                sale = self.env['sale.order'].search([('name', '=', picking.origin)],limit=1)
                if len(sale)>0: 
                    #
                    # On génére l'enregistrement Entête
                    #
                    enreg_heppner = self.export_heppner_enreg(picking,sale)
                    if enreg_heppner:
                        #
                        # On supprime les caractères accentués
                        # 
                        enreg_heppner = self.suppression_caractere_accentues(enreg_heppner) 
                        rows_to_write.append(enreg_heppner)
                        nb_enreg = nb_enreg + 1
                #
                # on écrit le fichier d'export
                #
                if nb_enreg >= 1:
                    date_generation = fields.Datetime.now()
                    date_fic = fields.Datetime.from_string(date_generation)
                    datefic = date_fic.strftime("%d%m%Y%H%M%S")                    
                    fichier_tps_csv = self.generation_nom_fichier_tps("HEPPNER",picking)                  
                    fichier_genere = '/tmp' + '/%s' % fichier_tps_csv
                    logger.info("===========================================================================")
                    logger.info(rows_to_write)
                    logger.info("===========================================================================")                    
                    fichier_tps_genere = open(fichier_genere, "w")
                    for rows in rows_to_write:
                        fichier_tps_genere.write(str(rows))                    
                    fichier_tps_genere.close()  
                    with open(fichier_genere,"rb") as fichier:
                        out = fichier.read()
                    picking.file_transport = base64.b64encode(out)
                    picking.file_transport_name = fichier_tps_csv
                    self.env['ir.attachment'].search([('name','=',fichier_tps_csv)]).unlink()
                    # on crée la pièce jointe
                    attachment = self.env['ir.attachment'].create({
                        'name': fichier_tps_csv,
                        'datas': picking.file_transport,
                        'type': 'binary',
                        'res_model': self._name,
                        'res_id': self.id,
                    })                    
                    #
                    # On télécharge le fichier généré
                    #
                    url = '/web/content/{}?download=true'.format(attachment.id)
                    return {
                        "type": "ir.actions.act_url",
                        "url": url,
                        "target": "new",
                    } 

    #########################################################################################
    #                                                                                       #
    #                             Génération nom fichier transport                          #
    #                                                                                       #
    #########################################################################################   
    def generation_nom_fichier_tps(self,transporteur,picking): 
        if picking.print_delivery_type == 'chain':
            type_fic = "CHAINE"
        else:
            type_fic = "LOCAL"  
        nom_pick_dict = picking.name.split('/')
        no_dict = len(nom_pick_dict) - 1
        nom_picking = nom_pick_dict[no_dict]
        nom_fichier_genere = transporteur + '-' + type_fic + '-' + nom_picking + '.csv'  
        return nom_fichier_genere   

    #########################################################################################
    #                                                                                       #
    #                                 Export Enregistrement HEPPNER                         #
    #                                                                                       #
    #########################################################################################   
    def export_heppner_enreg(self,picking,sale): 
        espace = ' '    
        enreg_heppner  = '' 
        date_liv_calc = self.transforme_date_transport(picking.date_done)
        enreg_heppner += maxi(date_liv_calc,8) + ';'                                             #   D   8      Date d'expédition 
        enreg_heppner += maxi(picking.madeco_transport_id.code_expe_heppner,15) + ';'            #   A   15     Code Expéditeur
        enreg_heppner += maxi(picking.madeco_transport_id.code_transporteur_heppner,4) + ';'     #   A   15     Code Transporteur
        enreg_heppner += maxi(picking.madeco_transport_id.code_produit_heppner,5) + ';'          #   A   15     Code Produit
        enreg_heppner += maxi(picking.partner_id.code_gln,15) + ';'                              #   A   15     Code destinataire
        enreg_heppner += maxi(picking.partner_id.name,35) + ';'                                  #   A   35	    Nom destinataire
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35	    Complément nom 
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35	    Interlocuteur
        enreg_heppner += maxi(espace,4) + ';'                                                    #   N   4	    No Rue
        enreg_heppner += maxi(picking.partner_id.street,30) + ';'                                #   A   30	    Rue
        enreg_heppner += maxi(picking.partner_id.street2,35) + ';'                               #   A   35	    Adresse 1
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35	    Adresse 2
        enreg_heppner += maxi(picking.partner_id.country_id.code,2) + ';'                        #   A   2	    Code Pays
        enreg_heppner += maxi(picking.partner_id.zip,9) + ';'                                    #   A   9	    Code Postal
        enreg_heppner += maxi(picking.partner_id.city,35) + ';'                                  #   A   35	    Ville
        nb_um = self.calcul_nb_um_total(picking) 
        nbum = str(nb_um)
        enreg_heppner += maxi(nbum,5) + ';'                                                      #   N   5	    Nb d'UM
        nb_colis = self.calcul_nb_colis_total(picking)
        nbcolis = str(nb_colis)
        enreg_heppner += maxi(nbcolis,5) + ';'                                                   #   N   5	    Nb de colis
        enreg_heppner += maxi(espace,11) + ';'                                                   #   N   8,3	Nb unité de taxation
        type_unite = 'KG'
        enreg_heppner += maxi(type_unite,3) + ';'                                                #   A   3	    Type unité de taxation
        poids_reel = self.calcul_poids_reel_total(picking)
        poidsreel = str(poids_reel) 
        enreg_heppner += maxi(poidsreel,11) + ';'                                                #   N   8,3	Poids réel total
        type_port = 'P'
        enreg_heppner += maxi(type_port,3) + ';'                                                 #   A   3	    Type de port
        enreg_heppner += maxi(espace,15) + ';'                                                   #   M2  13,2	Montant contre-remboursement
        enreg_heppner += maxi(espace,3) + ';'                                                    #   A   3	    Devise contre-remboursement
        enreg_heppner += maxi(espace,15) + ';'                                                   #   M2  13,2	Montant valeur declarée
        enreg_heppner += maxi(espace,3) + ';'                                                    #   A   3	    Devise valeur declarée
        enreg_heppner += maxi(sale.client_order_ref,35) + ';'                                    #   A   35	    Référence expédition 1
        enreg_heppner += maxi(picking.name,35) + ';'                                             #   A   35	    Référence expédition 2
        enreg_heppner += maxi(sale.cond_liv,70) + ';'                                            #   A   70  	Instruction de livraison
        enreg_heppner += maxi(espace,8) + ';'                                                    #   D   8	    Date impérative de livraison
        enreg_heppner += maxi(espace,15) + ';'                                                   #   M2  13,2	Montant valeur marchandise totale
        enreg_heppner += maxi(espace,3) + ';'                                                    #   A   3	    Devise valeur marchandise totale
        enreg_heppner += maxi(espace,3) + ';'                                                    #   A   3	    Type support consigné
        enreg_heppner += maxi(espace,5) + ';'                                                    #   N   5	    Nb support consigné
        enreg_heppner += maxi(espace,11) + ';'                                                   #   N   8,3	Volume total
        enreg_heppner += maxi(espace,15) + ';'                                                   #   A   15  	Marque colis
        enreg_heppner += maxi(espace,20) + ';'                                                   #   A   20  	Nature de la marchandise
        enreg_heppner += maxi(espace,11) + ';'                                                   #   N   8,3	Poids net colis
        enreg_heppner += maxi(poidsreel,11) + ';'                                                #   N   8,3	Poids brut colis
        enreg_heppner += maxi(espace,15) + ';'                                                   #   M2  13,2	Montant valeur marchandise colis
        enreg_heppner += maxi(espace,3) + ';'                                                    #   A   3	    Devise valeur marchandise colis
        enreg_heppner += maxi(espace,15) + ';'                                                   #   A   15  	Marque UM consignés
        enreg_heppner += maxi(espace,20) + ';'                                                   #   A   20  	Nature de la marchandise UM consignés
        enreg_heppner += maxi(espace,11) + ';'                                                   #   N   8,3	Poids net UM consignés
        enreg_heppner += maxi(espace,11) + ';'                                                   #   N   8,3	Poids brut UM consignés
        enreg_heppner += maxi(espace,15) + ';'                                                   #   M2  13,2	Montant valeur marchandise UM consignés
        enreg_heppner += maxi(espace,3) + ';'                                                    #   A   3	    Devise valeur marchandise UM consignés
        enreg_heppner += maxi(espace,10) + ';'                                                   #   A   10  	Numéro récépissé
        enreg_heppner += maxi(espace,10) + ';'                                                   #   A   10  	Livraison samedi O/N
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35  	Libellé 1
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35  	Libellé 2
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35  	Libellé 3
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35  	Libellé 4
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35  	Libellé 5
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35  	Libellé 6
        enreg_heppner += maxi(espace,4) + ';'                                                    #   A   4  	    Code ONU matière dangereuse
        enreg_heppner += maxi(espace,11) + ';'                                                   #   N   8,3	    Poids matière dangereuse
        enreg_heppner += maxi('N',1) + ';'                                                       #   A   1   	Multi-produit matière dangereuse O/N
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35  	Réservé 1
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35  	Réservé 2
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35  	Réservé 3
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35  	Réservé 4
        enreg_heppner += maxi(espace,35) + ';'                                                   #   A   35  	Réservé 5
        type_um = self.recherche_type_um(picking)
        enreg_heppner += maxi(type_um,3) + ';'                                                   #   A   3	    Type d'UM
        enreg_heppner += maxi(espace,15) + ';'                                                   #   A   15  	Code imprimante
        enreg_heppner += maxi(espace,5) + ';'                                                    #   H   5   	Heure de livraison
        enreg_heppner += maxi(picking.partner_id.phone,25) + ';'                                 #   A   35	    Téléphone destinataire
        enreg_heppner += maxi(picking.madeco_transport_id.code_service_heppner,3) + ';'          #   A   3	    Service
        enreg_heppner += maxi(espace,3) + ';'                                                    #   A   3	    Code prestation H30
        enreg_heppner += maxi(espace,30) + ';'                                                   #   A   30	    Commentaire prestation H30
        enreg_heppner += maxi(espace,3) + ';'                                                    #   A   3	    Code prestation H33
        enreg_heppner += maxi(espace,30) + ';'                                                   #   A   30	    Commentaire prestation H33
        enreg_heppner += maxi(espace,1) + ';'                                                    #   A   1  	    Libre 5
        enreg_heppner += maxi(espace,1) + ';'                                                    #   A   1  	    Libre 6
        enreg_heppner += maxi(espace,1) + ';'                                                    #   A   1  	    Libre 7
        enreg_heppner += maxi(espace,1) + ';'                                                    #   A   1  	    Libre 8
        enreg_heppner += maxi(espace,1) + ';'                                                    #   A   1  	    Libre 9
        enreg_heppner += maxi(espace,11) + ';'                                                   #   N   8,3	    Masse brute totale LQ
        enreg_heppner += maxi(picking.partner_id.email,512) + ';'                                #   A   512	    Email destinataire
        enreg_heppner += maxi(espace,5) + ';'                                                    #   A   5 	    Type annonce livraison
        enreg_heppner += maxi(picking.partner_id.mobile,25) + ';'                                #   A   25      Portable destinataire
        enreg_heppner += maxi(espace,15) + ';'                                                   #   A   15 	    Type destinataire
        enreg_heppner += maxi(espace,1)  + ';'                                                   #   A   5 	    Indicateur de prise de rendez-vous O/N
        return enreg_heppner

    #########################################################################################
    #                                                                                       #
    #                                     Export Tps DPD                                    #
    #                                                                                       #
    #########################################################################################      
    def export_dpd_edi_picking(self):           
        self.ensure_one()
        today = fields.Date.to_string(datetime.now())
        for picking in self: 
            #
            # On recherche la commande de vente rattaché à la livraison
            #
            if picking.origin:
                nb_enreg = 0
                rows_to_write = []
                sale = self.env['sale.order'].search([('name', '=', picking.origin)],limit=1)
                if len(sale)>0: 
                    #
                    # On génére l'enregistrement Entête
                    #
                    enreg_dpd = self.export_dpd_enreg_entete()
                    if enreg_dpd:
                        #
                        # On supprime les caractères accentués
                        # 
                        enreg_dpd = self.suppression_caractere_accentues(enreg_dpd) 
                        rows_to_write.append(enreg_dpd)
                        nb_enreg = nb_enreg + 1
                    #
                    # On génére l'enregistrement Ligne
                    #
                    for package in picking.package_level_ids_details:
                        type_envoi = picking.madeco_transport_id.dpd_type_envoi
                        enreg_dpd = self.export_dpd_enreg_ligne(picking,sale,package,type_envoi)
                        if enreg_dpd:
                            #
                            # On supprime les caractères accentués
                            # 
                            enreg_dpd = self.suppression_caractere_accentues(enreg_dpd) 
                            rows_to_write.append(enreg_dpd)
                            nb_enreg = nb_enreg + 1    
                    #
                    # on écrit le fichier d'export
                    #
                    if nb_enreg >= 1:                           
                        date_generation = fields.Datetime.now()
                        date_fic = fields.Datetime.from_string(date_generation)
                        datefic = date_fic.strftime("%d%m%Y%H%M%S")                        
                        fichier_tps_csv  = self.generation_nom_fichier_tps("DPD",picking)                    
                        fichier_genere = '/tmp' + '/%s' % fichier_tps_csv
                        logger.info("===========================================================================")
                        logger.info(rows_to_write)
                        logger.info("===========================================================================")
                        fichier_tps_genere = open(fichier_genere, "w")
                        for rows in rows_to_write:
                            fichier_tps_genere.write(str(rows))                    
                    fichier_tps_genere.close()   
                    with open(fichier_genere,"rb") as fichier:
                        out = fichier.read()
                    picking.file_transport = base64.b64encode(out)
                    picking.file_transport_name = fichier_tps_csv
                    self.env['ir.attachment'].search([('name','=',fichier_tps_csv)]).unlink()
                    # on crée la pièce jointe
                    attachment = self.env['ir.attachment'].create({
                        'name': fichier_tps_csv,
                        'datas': picking.file_transport,
                        'type': 'binary',
                        'res_model': self._name,
                        'res_id': self.id,
                    })
                    #
                    # On télécharge le fichier généré
                    #
                    url = '/web/content/{}?download=true'.format(attachment.id)
                    return {
                        "type": "ir.actions.act_url",
                        "url": url,
                        "target": "new",
                    }                     
       
    #########################################################################################
    #                                                                                       #
    #                           Export Enregistrement DPD Entête                            #
    #                                                                                       #
    #########################################################################################   
    def export_dpd_enreg_entete(self): 
        enreg_dpd  = '$VERSION=110'         #   A   12      Identifiant de version  
        enreg_dpd += '\r\n'                 #   A   2	    CR/LF 
        return enreg_dpd

    #########################################################################################
    #                                                                                       #
    #                           Export Enregistrement DPD Ligne                             #
    #                                                                                       #
    #########################################################################################   
    def export_dpd_enreg_ligne(self,picking,sale,package,type_envoi): 
        company_id = self.env.company
        espace = ' '    
        enreg_dpd  = '' 
        enreg_dpd += maxi(sale.client_order_ref,35)                             #   A   35	    Référence client N° 1
        enreg_dpd += maxi(espace,2)                                             #   A   2	    Filler
        poids_decagrammes = self.calcul_poids_decagrammes_package(package)
        poids_deca = str(poids_decagrammes)
        enreg_dpd += maxi_0(poids_deca,8)                                       #   N   8	    Poids en décagrammes
        enreg_dpd += maxi(espace,15)                                            #   A   15	    Filler
        enreg_dpd += maxi(picking.partner_id.name,35)                           #   A   35	    Nom destinataire
        if type_envoi == "relais":
            enreg_dpd += maxi(picking.partner_id.name,35)                       #   A   35	    Adresse 1 ou Nom pour DPD relais
        else:    
            if len(picking.partner_id.street) > 35:            
                enreg_dpd += maxi(picking.partner_id.street[35:],35)            #   A   35	    Adresse 1    
            else:    
                enreg_dpd += maxi(espace,35)                                    #   A   35	    Adresse 1
        enreg_dpd += maxi(picking.partner_id.street2,35)                        #   A   35	    Adresse 2
        enreg_dpd += maxi(espace,35)                                            #   A   35	    Adresse 3
        enreg_dpd += maxi(espace,35)                                            #   A   35	    Adresse 4
        enreg_dpd += maxi(espace,35)                                            #   A   35	    Adresse 5
        enreg_dpd += maxi(picking.partner_id.zip,10)                            #   A   10	    Code postal
        enreg_dpd += maxi(picking.partner_id.city,35)                           #   A   35	    Ville
        enreg_dpd += maxi(espace,10)                                            #   A   10      Filler
        enreg_dpd += maxi(picking.partner_id.street,35)                         #   A   35	    Rue
        enreg_dpd += maxi(espace,10)                                            #   A   10	    Filler
        enreg_dpd += maxi(picking.partner_id.country_id.code,3)                 #   A   3	    Code pays
        enreg_dpd += maxi(picking.partner_id.phone,20)                          #   A   20	    Téléphone
        enreg_dpd += maxi(espace,25)                                            #   A   25	    Filler
        enreg_dpd += maxi(company_id.partner_id.name,35)                        #   A   35	    Nom expéditeur
        enreg_dpd += maxi(company_id.partner_id.street2,35)                     #   A   35	    Adresse 1
        enreg_dpd += maxi(espace,35)                                            #   A   35	    Filler
        enreg_dpd += maxi(espace,35)                                            #   A   35	    Filler
        enreg_dpd += maxi(espace,35)                                            #   A   35	    Filler
        enreg_dpd += maxi(espace,35)                                            #   A   35	    Filler
        enreg_dpd += maxi(company_id.partner_id.zip,10)                         #   A   10	    Code postal
        enreg_dpd += maxi(company_id.partner_id.city,35)                        #   A   35	    Ville
        enreg_dpd += maxi(espace,10)                                            #   A   10      Filler
        enreg_dpd += maxi(company_id.partner_id.street,35)                      #   A   35	    Rue
        enreg_dpd += maxi(espace,10)                                            #   A   10	    Filler
        enreg_dpd += maxi(company_id.partner_id.country_id.code,3)              #   A   3	    Code pays
        enreg_dpd += maxi(company_id.partner_id.phone,20)                       #   A   20	    Téléphone
        enreg_dpd += maxi(espace,10)                                            #   A   10	    Filler
        if sale.cond_liv:
            lg_liv = len(sale.cond_liv)
            if lg_liv == 0: 
                enreg_dpd += maxi(espace,35)                                        #   A   35	    Instruction de livraison    
                enreg_dpd += maxi(espace,35)                                        #   A   35	    Instruction de livraison   
                enreg_dpd += maxi(espace,35)                                        #   A   35	    Instruction de livraison   
                enreg_dpd += maxi(espace,35)                                        #   A   35	    Instruction de livraison   
            else:
                if lg_liv >= 140:
                    enreg_dpd += maxi(sale.cond_liv[0:35],35)                       #   A   35	    Instruction de livraison    
                    enreg_dpd += maxi(sale.cond_liv[35:71],35)                      #   A   35	    Instruction de livraison   
                    enreg_dpd += maxi(sale.cond_liv[71:106],35)                     #   A   35	    Instruction de livraison  
                    enreg_dpd += maxi(sale.cond_liv[106:],35)                       #   A   35	    Instruction de livraison      
                else:
                    if lg_liv >= 105 and lg_liv < 140:    
                        enreg_dpd += maxi(sale.cond_liv[0:35],35)                   #   A   35	    Instruction de livraison    
                        enreg_dpd += maxi(sale.cond_liv[35:71],35)                  #   A   35	    Instruction de livraison   
                        enreg_dpd += maxi(sale.cond_liv[71:106],35)                 #   A   35	    Instruction de livraison  
                        enreg_dpd += maxi(sale.cond_liv[106:],35)                   #   A   35	    Instruction de livraison      
                    else:
                        if lg_liv >= 70 and lg_liv < 105:    
                            enreg_dpd += maxi(sale.cond_liv[0:35],35)               #   A   35	    Instruction de livraison    
                            enreg_dpd += maxi(sale.cond_liv[35:71],35)              #   A   35	    Instruction de livraison   
                            enreg_dpd += maxi(sale.cond_liv[71:],35)                #   A   35	    Instruction de livraison   
                            enreg_dpd += maxi(espace,35)                            #   A   35	    Instruction de livraison      
                        else:
                            if lg_liv >= 35 and lg_liv < 70: 
                                enreg_dpd += maxi(sale.cond_liv[0:35],35)           #   A   35	    Instruction de livraison    
                                enreg_dpd += maxi(sale.cond_liv[35:],35)            #   A   35	    Instruction de livraison   
                                enreg_dpd += maxi(espace,35)                        #   A   35	    Instruction de livraison   
                                enreg_dpd += maxi(espace,35)                        #   A   35	    Instruction de livraison        
                            else:    
                                enreg_dpd += maxi(sale.cond_liv,35)                 #   A   35	    Instruction de livraison    
                                enreg_dpd += maxi(espace,35)                        #   A   35	    Instruction de livraison   
                                enreg_dpd += maxi(espace,35)                        #   A   35	    Instruction de livraison   
                                enreg_dpd += maxi(espace,35)                        #   A   35	    Instruction de livraison  
        else: 
            enreg_dpd += maxi(espace,35)                                            #   A   35	    Instruction de livraison    
            enreg_dpd += maxi(espace,35)                                            #   A   35	    Instruction de livraison   
            enreg_dpd += maxi(espace,35)                                            #   A   35	    Instruction de livraison   
            enreg_dpd += maxi(espace,35)                                            #   A   35	    Instruction de livraison   
        date_liv_calc = self.transforme_date_dpd(picking.date_done)
        enreg_dpd += maxi(date_liv_calc,10)                                     #   A   10	    Date d'expédition
        no_chargeur = picking.madeco_transport_id.no_compte_chargeur_dpd 
        no_charge = str(no_chargeur)
        enreg_dpd += maxi(no_chargeur,8)                                        #   N   8	    No compte chargeur DPD
        enreg_dpd += maxi(espace,35)                                            #   A   35	    Code à barres
        enreg_dpd += maxi(picking.name,35)                                      #   A   35	    Référence client N° 2
        enreg_dpd += maxi(espace,29)                                            #   A   29	    Filler
        enreg_dpd += maxi(espace,9)                                             #   N   9	    Montant de la valeur déclarée
        enreg_dpd += maxi(espace,8)                                             #   A   8	    Filler
        enreg_dpd += maxi(package.package_id.name,35)                           #   A   35	    Référence client N° 3
        enreg_dpd += maxi(espace,1)                                             #   A   1	    Filler
        if type_envoi == "classic":
            if len(picking.package_level_ids_details)>1:
                enreg_dpd += maxi(picking.name,35)                              #   A   35	    No de consolidation
            else:
                enreg_dpd += maxi(espace,35)                                    #   A   35	    No de consolidation    
        else: 
            enreg_dpd += maxi(espace,35)                                        #   A   35	    No de consolidation
        enreg_dpd += maxi(espace,10)                                            #   A   10	    Filler
        enreg_dpd += maxi(company_id.partner_id.email,80)                       #   A   80	    Email Expéditeur
        enreg_dpd += maxi(company_id.partner_id.mobile,35)                      #   A   35	    GSM Expéditeur
        enreg_dpd += maxi(picking.partner_id.email,80)                          #   A   80	    Email Destinataire
        enreg_dpd += maxi(picking.partner_id.phone,35)                          #   A   35	    GSM Destinataire
        enreg_dpd += maxi(espace,96)                                            #   A   96	    Filler
        if type_envoi == "relais":
            code_point_relais = self.recherche_code_point_relais(picking)
            enreg_dpd += maxi(code_point_relais,8)                              #   A   8	    Identifiant Point Relais
        else:
            enreg_dpd += maxi(espace,8)                                         #   A   8	    Identifiant Point Relais    
        enreg_dpd += maxi(espace,113)                                           #   A   113	    Filler
        if type_envoi == "classic":
            if len(picking.package_level_ids_details)>1:
                type_conso = str("38")
                enreg_dpd += maxi(type_conso,2)                                 #   N   2	    Consolidation / type
                attr_conso = str("01")
                enreg_dpd += maxi(attr_conso,2)                                 #   N   2	    Consolidation / attribut
            else:    
                enreg_dpd += maxi(espace,2)                                     #   N   2	    Consolidation / type
                enreg_dpd += maxi(espace,2)                                     #   N   2	    Consolidation / attribut
        else:    
            enreg_dpd += maxi(espace,2)                                         #   N   2	    Consolidation / type
            enreg_dpd += maxi(espace,2)                                         #   N   2	    Consolidation / attribut
        enreg_dpd += maxi(espace,1)                                             #   A   1	    Filler
        if picking.madeco_transport_id.dpd_predict:
            dpd_predict = '+'
        else:
            dpd_predict = ' '     
        enreg_dpd += maxi(dpd_predict,1)                                        #   A   1	    Predict
        enreg_dpd += maxi(espace,35)                                            #   A   35	    Nom du contact
        enreg_dpd += maxi(espace,10)                                            #   A   10	    DigiCode1
        enreg_dpd += maxi(espace,10)                                            #   A   10	    DigiCode2
        enreg_dpd += maxi(espace,10)                                            #   A   10	    Intercom
        enreg_dpd += maxi(espace,200)                                           #   A   200	    Filler
        if picking.madeco_transport_id.dpd_retour:
            dpd_retour = '3'
        else:
            dpd_retour = ' ' 
        enreg_dpd += maxi(dpd_retour,1)                                         #   A   1	    Retour
        enreg_dpd += maxi(espace,15)                                            #   A   15	    Filler
        if picking.madeco_transport_id.dpd_retour:
            enreg_dpd += maxi(company_id.partner_id.name,35)                    #   A   35	    Nom destinataire Retour
            enreg_dpd += maxi(company_id.partner_id.street2,35)                 #   A   35	    Adresse 1
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Adresse 2
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Adresse 3
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Adresse 4
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Adresse 5
            enreg_dpd += maxi(company_id.partner_id.zip,10)                     #   A   10	    Code postal
            enreg_dpd += maxi(company_id.partner_id.city,35)                    #   A   35	    Ville
            enreg_dpd += maxi(espace,10)                                        #   A   10      Filler
            enreg_dpd += maxi(company_id.partner_id.street,35)                  #   A   35	    Rue
            enreg_dpd += maxi(espace,10)                                        #   A   10	    Filler
            enreg_dpd += maxi(company_id.partner_id.country_id.code,3)          #   A   3	    Code pays
            enreg_dpd += maxi(company_id.partner_id.phone,30)                   #   A   30	    Téléphone
        else:    
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Nom destinataire Retour
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Adresse 1
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Adresse 2
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Adresse 3
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Adresse 4
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Adresse 5
            enreg_dpd += maxi(espace,10)                                        #   A   10	    Code postal
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Ville
            enreg_dpd += maxi(espace,10)                                        #   A   10      Filler
            enreg_dpd += maxi(espace,35)                                        #   A   35	    Rue
            enreg_dpd += maxi(espace,10)                                        #   A   10	    Filler
            enreg_dpd += maxi(espace,3)                                         #   A   3	    Code pays
            enreg_dpd += maxi(espace,30)                                        #   A   30	    Téléphone
        enreg_dpd += maxi(espace,18)                                            #   A   18	    CargoID
        enreg_dpd += maxi(sale.name,35)                                         #   A   35	    Référence client N° 4
        enreg_dpd += '\r\n'                                                     #   A   2	    CR/LF
        return enreg_dpd

    #########################################################################################
    #                                                                                       #
    #                                     Export LA POSTE                                   #
    #                                                                                       #
    ######################################################################################### 
    def export_laposte_edi_picking(self):           
        self.ensure_one()

        for picking in self: 
            #
            # On génère l'impression de l'étiquette LA POSTE
            #
            #liste_etiquette.append(picking)
            
            # on le génère en PDF, si c'est un rapport qweb, mettre _render_qweb_pdf à la place de render_py3o
            model_rapport = self.env.ref('madeco_transport.action_report_etiquette_laposte')
            rapport_etiq = model_rapport._render_qweb_pdf([picking.id])[0]
            fichier_laposte_pdf  = self.generation_nom_fichier_laposte("POSTE",picking)
            picking.file_transport_name = fichier_laposte_pdf
            self.env['ir.attachment'].search([('name','=',fichier_laposte_pdf)]).unlink()
            # on crée la pièce jointe
            attachment = self.env['ir.attachment'].create({
                'name': fichier_laposte_pdf,
                'datas': base64.encodebytes(rapport_etiq),
                'type': 'binary',
                'res_model': self._name,
                'res_id': self.id,
            })            
            # on la retourne
            url = '/web/content/{}?download=true'.format(attachment.id)
            return {
                "type": "ir.actions.act_url",
                "url": url,
                "target": "new",
            }     

    #########################################################################################
    #                                                                                       #
    #                             Génération nom fichier transport                          #
    #                                                                                       #
    #########################################################################################   
    def generation_nom_fichier_laposte(self,transporteur,picking): 
        if picking.print_delivery_type == 'chain':
            type_fic = "CHAINE"
        else:
            type_fic = "LOCAL"  
        nom_pick_dict = picking.name.split('/')
        no_dict = len(nom_pick_dict) - 1
        nom_picking = nom_pick_dict[no_dict]
        nom_fichier_genere = transporteur + '-' + type_fic + '-' + nom_picking + '.pdf'  
        return nom_fichier_genere   

    #########################################################################################
    #                                                                                       #
    #                                  transforme_date_transport                            #
    #                                                                                       #
    #########################################################################################
    def transforme_date_transport(self, date_origine):
        date_str = str(date_origine)
        retour_date = date_str[0:4]+date_str[5:7]+date_str[8:10]
        return retour_date   

    #########################################################################################
    #                                                                                       #
    #                                  transforme_date_dpd                                  #
    #                                                                                       #
    #########################################################################################
    def transforme_date_dpd(self, date_origine):
        date_str = str(date_origine)
        retour_date = date_str[8:10] + "/" + date_str[5:7] + "/" + date_str[0:4]
        return retour_date 

    #########################################################################################
    #                                                                                       #
    #                                    calcul_poids_reel_total                            #
    #                                                                                       #
    #########################################################################################
    def calcul_poids_reel_total(self, picking):
        poids = 0
        for line in picking.move_line_ids:
            poids += (line.product_id.weight * line.qty_done)        
        return poids     

    #########################################################################################
    #                                                                                       #
    #                                    calcul_poids_decagrammes                           #
    #                                                                                       #
    #########################################################################################
    def calcul_poids_decagrammes(self, picking):
        poids = 0
        for line in picking.move_line_ids:
            poids += (line.product_id.weight * line.qty_done)    
        poids = poids * 100    
        return poids 

    #########################################################################################
    #                                                                                       #
    #                           calcul_poids_decagrammes_package                            #
    #                                                                                       #
    #########################################################################################
    def calcul_poids_decagrammes_package(self, package):
        pds = 0
        if package:        
            pds = package.package_id.weight    
        pds = pds * 100 
        poids = int(pds)
        return poids     

    #########################################################################################
    #                                                                                       #
    #                                    calcul_nb_um_total                                 #
    #                                                                                       #
    #########################################################################################
    def calcul_nb_um_total(self, picking):
        nb_pal = 0
        if picking:
            listepal = [] 
            for line in picking.move_line_ids_without_package: 
                if line.result_package_id: 
                    if line.result_package_id.packaging_id.support_expedition:
                        exist = False
                        pal = line.result_package_id.id 
                        for dico in listepal:
                            if pal == dico['pal']:
                                exist = True                            
                        if not exist:
                            data = {
                                    'pal': line.result_package_id.id,
                                    }
                            listepal.append(data)
                            nb_pal += 1  
            if nb_pal == 0: 
                listecolis = [] 
                for line in picking.move_line_ids_without_package: 
                    if line.result_package_id: 
                        exist = False
                        colis = line.result_package_id.id 
                        for dico in listecolis:
                            if colis == dico['colis']:
                                exist = True                            
                        if not exist:
                            data = {
                                    'colis': line.result_package_id.id,
                                    }
                            listecolis.append(data)                    
                            nb_pal += 1
        else:
            nb_pal = 0    
        return nb_pal     

    #########################################################################################
    #                                                                                       #
    #                                    recherche_type_um                                  #
    #                                                                                       #
    #########################################################################################
    def recherche_type_um(self, picking):
        type_um = 'COL'
        if picking:
            for line in picking.move_line_ids_without_package: 
                if line.result_package_id: 
                    if line.result_package_id.packaging_id.support_expedition:
                        type_um = 'PAL'
        else:
            type_um = 'COL'   
        return type_um     

    #########################################################################################
    #                                                                                       #
    #                                 calcul_nb_colis_total                                 #
    #                                                                                       #
    #########################################################################################
    def calcul_nb_colis_total(self, picking):
        nb_colis = 0
        if picking:
            listecolis = [] 
            for line in picking.move_line_ids_without_package: 
                if line.result_package_id: 
                    exist = False
                    colis = line.result_package_id.id 
                    for dico in listecolis:
                        if colis == dico['colis']:
                            exist = True                            
                    if not exist:
                        data = {
                                'colis': line.result_package_id.id,
                                }
                        listecolis.append(data)                    
                        nb_colis += 1
        else:
            nb_colis = 0    
        return nb_colis             
    
    #########################################################################################
    #                                                                                       #
    #                        Recherche code point relais dans adresse.rue2                  #
    #                                                                                       #
    #########################################################################################
    def recherche_code_point_relais(self, picking):
        code_point_relais_retour = ''
        if picking:
            if picking.partner_id.street2:
                ouvre_par = '('
                ferme_par = ')'
                debut = picking.partner_id.street2.find(ouvre_par)
                fin = picking.partner_id.street2.find(ferme_par)
                if fin > debut:
                    #code_point_relais_retour = '(' + picking.partner_id.street2[debut+1:fin] + ')'
                    code_point_relais_retour = picking.partner_id.street2[debut+1:fin]
        return code_point_relais_retour     

    #########################################################################################
       
