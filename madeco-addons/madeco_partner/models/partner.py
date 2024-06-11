# -*- coding: utf-8 -*-

import json
from datetime import datetime
from odoo.tools import float_compare, float_round
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import unidecode
import logging
logger = logging.getLogger(__name__)


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    
    groupe_id = fields.Many2one('res.partner',string='Groupe')
    centrale_id = fields.Many2one('res.partner',string='Centrale')
    enseigne_id = fields.Many2one('res.partner',string='Enseigne')
    adresse_fac_id = fields.Many2one('res.partner',string='Adresse de facturation par défaut')
    client_web = fields.Boolean(string="Client Web", default=False)
    code_client_import_fec = fields.Char(string="Code client import FEC")
    code_magasin = fields.Char(string="Code magasin")
    franco_port = fields.Float(string="Franco de port")
    secteur_liv_id = fields.Many2one('secteur.livraison',string='Secteur de livraison')
    adresse_liv_id = fields.Many2one('res.partner',string='Adresse de livraison par défaut')
    jour_livraison_fixe = fields.Selection([
        ('non', 'Non'),
        ('lundi', 'Lundi'),
        ('mardi', 'Mardi'),
        ('mercredi', 'Mercredi'),
        ('jeudi', 'Jeudi'),
        ('vendredi', 'Vendredi'),
        ('samedi', 'Samedi'),
        ('dimanche', 'Dimanche'),],
        string='Jour de livraison fixe', default='non')
    jour_preparation = fields.Selection([
        ('non', 'Non'),
        ('lundi', 'Lundi'),
        ('mardi', 'Mardi'),
        ('mercredi', 'Mercredi'),
        ('jeudi', 'Jeudi'),
        ('vendredi', 'Vendredi'),
        ('samedi', 'Samedi'),
        ('dimanche', 'Dimanche'),],
        string='Jour de préparation', default='non')
    destinataire_relance = fields.Selection([('client', 'Client'),('centrale', 'Centrale'),], string='Destinataire des relances', default='client')



    @api.model_create_multi
    def create(self, vals_list):
        ir_default_obj = self.env['ir.default']
        company_id =  self.env.user.company_id 
        parent_obj = self.env['res.partner']
        for vals in vals_list:            
            if vals.get('parent_id',False):
                parent_id = vals['parent_id']
                parent = parent_obj.search([('id', '=', parent_id)],limit=1)
                vals['groupe_id'] = parent.groupe_id.id   
                vals['centrale_id'] = parent.centrale_id.id 
                vals['enseigne_id'] = parent.enseigne_id.id 
                vals['adresse_fac_id'] = parent.adresse_fac_id.id  
                #vals['client_web'] = parent.client_web 
                vals['code_client_import_fec'] = parent.code_client_import_fec  
                vals['code_magasin'] = parent.code_magasin  
                vals['franco_port'] = parent.franco_port          
                vals['secteur_liv_id'] = parent.secteur_liv_id.id  
                vals['adresse_liv_id'] = parent.adresse_liv_id.id 
                vals['jour_livraison_fixe'] = parent.jour_livraison_fixe 
                vals['jour_preparation'] = parent.jour_preparation  
                #vals[''] = parent.  


        res = super(Partner, self).create(vals_list)    

        if res.adresse_fac_id:
            #
            # On créé la valeur par defaut de l'adresse de facturation 
            #                  
            field_id = company_id.champ_adresse_fac.id 
            id_company = company_id.id                          
            condition = 'partner_id=' + str(res.id)
            value_json = str(res.adresse_fac_id.id) 

            ir_default = ir_default_obj.search([('field_id','=',field_id),('condition','=', condition),('company_id','=',id_company)],limit=1)

            if ir_default:
                value_json = str(res.adresse_fac_id.id) 
                values_default={'json_value': value_json,}
                ir_default.write(values_default)        
            else:    
                values_default={'field_id': field_id,
                                'json_value': value_json,
                                'condition': condition,
                                'company_id': id_company,
                                }  
                ir_default_cree = ir_default_obj.create(values_default)    

        if res.adresse_liv_id:
            #
            # On créé la valeur par defaut de l'adresse de livraison
            #                  
            field_id = company_id.champ_adresse_liv.id 
            id_company = company_id.id                          
            condition = 'partner_id=' + str(res.id)
            value_json = str(res.adresse_liv_id.id) 

            ir_default = ir_default_obj.search([('field_id','=',field_id),('condition','=', condition),('company_id','=',id_company)],limit=1)

            if ir_default:
                value_json = str(res.adresse_liv_id.id) 
                values_default={'json_value': value_json,}
                ir_default.write(values_default)        
            else:    
                values_default={'field_id': field_id,
                                'json_value': value_json,
                                'condition': condition,
                                'company_id': id_company,
                                }  
                ir_default_cree = ir_default_obj.create(values_default)                              

        return res        


    def write(self, vals):

        old_valeur_adresse_fac_id = self.adresse_fac_id
        old_valeur_adresse_liv_id = self.adresse_liv_id

        ir_default_obj = self.env['ir.default']
        company_id =  self.env.user.company_id 
        result = super(Partner, self).write(vals)

        if result:
            for partner in self:

                if partner.adresse_fac_id:
                    #
                    # On créé la valeur par defaut de l'adresse de facturation
                    #  
                    field_id = company_id.champ_adresse_fac.id                  
                    id_company = company_id.id 
                    condition = 'partner_id=' + str(partner.id)
                    value_json = str(partner.adresse_fac_id.id) 
                    ir_default = ir_default_obj.search([('field_id','=',field_id),('condition','=', condition),('company_id','=',id_company)],limit=1)
                    if ir_default:
                        value_json = str(partner.adresse_fac_id.id) 
                        values_default={'json_value': value_json,}
                        ir_default.write(values_default)                
                    else:    
                        values_default={'field_id': field_id,
                                        'json_value': value_json,
                                        'condition': condition,
                                        'company_id': id_company,
                                        }  
                        ir_default_cree = ir_default_obj.create(values_default)   
                if partner.adresse_liv_id:
                    #
                    # On créé la valeur par defaut de l'adresse de livraison
                    #  
                    field_id = company_id.champ_adresse_liv.id                  
                    id_company = company_id.id 
                    condition = 'partner_id=' + str(partner.id)
                    value_json = str(partner.adresse_liv_id.id) 
                    ir_default = ir_default_obj.search([('field_id','=',field_id),('condition','=', condition),('company_id','=',id_company)],limit=1)
                    if ir_default:
                        value_json = str(partner.adresse_liv_id.id) 
                        values_default={'json_value': value_json,}
                        ir_default.write(values_default)                
                    else:    
                        values_default={'field_id': field_id,
                                        'json_value': value_json,
                                        'condition': condition,
                                        'company_id': id_company,
                                        }  
                        ir_default_cree = ir_default_obj.create(values_default)    

                if old_valeur_adresse_liv_id and not partner.adresse_liv_id:
                    #
                    # On supprime l'adresse de livraison par défaut dans le paramétrage
                    # 
                    field_id = company_id.champ_adresse_liv.id                  
                    id_company = company_id.id 
                    condition = 'partner_id=' + str(partner.id)
                    ir_default = ir_default_obj.search([('field_id','=',field_id),('condition','=', condition),('company_id','=',id_company)],limit=1)
                    if ir_default:  
                        ir_default.unlink()       

                if old_valeur_adresse_fac_id and not partner.adresse_fac_id:
                    #
                    # On supprime l'adresse de livraison par défaut dans le paramétrage
                    # 
                    field_id = company_id.champ_adresse_fac.id                  
                    id_company = company_id.id 
                    condition = 'partner_id=' + str(partner.id)
                    ir_default = ir_default_obj.search([('field_id','=',field_id),('condition','=', condition),('company_id','=',id_company)],limit=1)
                    if ir_default:  
                        ir_default.unlink()                                    

        return result

    