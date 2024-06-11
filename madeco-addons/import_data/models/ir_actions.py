# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)


class ir_actions(models.Model):
    _name = 'ir.actions.server'
    _inherit = 'ir.actions.server'
    
    #state = fields.Selection(selection_add=[('moulinette','Lancer une moulinette')],ondelete={'moulinette':'cascade'})
    moulinette = fields.Many2one('import.data','Moulinette à lancer')
    
    
    @api.model
    def run_action_moulinette(self, action, eval_context=None):
        action.sudo().moulinette.lancer_moulinette()
