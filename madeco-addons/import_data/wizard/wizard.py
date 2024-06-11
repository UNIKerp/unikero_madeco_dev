# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)

class menu_wizard(models.TransientModel):
    _name = 'menu.wizard'
    
    name = fields.Char('Nom')
    menu_parent = fields.Many2one('ir.ui.menu',string='Menu Parent')
    moulinette = fields.Many2one('import.data',string='Moulinette')
    
    def creer_menu(self):
        view_obj = self.env['ir.ui.view']
        action_view_obj = self.env['ir.actions.act_window.view']
        action_obj = self.env['ir.actions.act_window']
        menu_obj = self.env['ir.ui.menu']
        # on crée l'action qui va permettre de l'afficher et le menu
        value_action = {
            'name': self.name,
            'res_model': 'import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': { 'default_moulinette': self.moulinette.id}
        }

        action = action_obj.create(value_action)
        
        view = self.env.ref('import_data.import_wizard_form')
        
        value_action_view = {
            'view_id': view.id,
            'view_mode': 'form',
            'act_window_id': action.id,

        }

        action_view = action_view_obj.create(value_action_view)


        # on ajoute le menu

        value_menu = {
            'name': self.name,
            'action': "ir.actions.act_window,"+str(action.id),
            'parent_id': self.menu_parent.id,
        }
        menu = menu_obj.create(value_menu)
        

class import_wizard(models.TransientModel):
    _name = 'import.wizard'
    
    name = fields.Char('Nom')
    moulinette = fields.Many2one('import.data',string='Moulinette')
    fichier = fields.Binary('Fichier')
    
    
    def importer(self):
        
        moulinette_obj = self.env['import.data']
        moulinette = self.moulinette
        source = moulinette.source
            
            
        if source.model_cree == False:
            source.creer_modele()
            
        if source.donnees_chargees == False:
            source.charger_donnees()
        
        produits_obj = self.env[source.modele.model]
        
        if produits_obj.search_count([])>0:
            produits_obj.search([]).unlink()
            
        # on pousse le fichier joint à la place du fichier d'origine
        source.fichier = self.fichier
        
        # on charge les données
        source.charger_donnees()
        
        # on lance la moulinette
        moulinette.vider_logs()
        moulinette.lancer_moulinette()
        
        
        return {}