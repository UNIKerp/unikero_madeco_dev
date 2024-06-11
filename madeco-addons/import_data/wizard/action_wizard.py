# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)
from odoo.addons.http_routing.models.ir_http import slugify


class action_wizard(models.TransientModel):
    _name = 'action.wizard'
    
    name = fields.Char('Nom')
    moulinette = fields.Many2one('import.data',string='Moulinette')
    nom_action = fields.Char("Nom de l'action")
    objet = fields.Many2one('ir.model',"Objet")
    
    def creer_action(self):
        action_server_obj = self.env['ir.actions.server']        
        value = {
            'name': self.nom_action,
            'model_id': self.objet.id,
            'binding_model_id': self.objet.id,
            'state': 'code',
            'code': "env['import.data'].search([('id','=',{})]).lancer_moulinette(records)".format(self.moulinette.id),
        }
        action_server = action_server_obj.create(value)
        
        self.moulinette.model_action = self.objet.id
        
        return {}