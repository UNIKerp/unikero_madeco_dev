import logging

from odoo import api, fields, models

logger = logging.getLogger(__name__)


class IrActions(models.Model):
    _inherit = "ir.actions.server"

    moulinette = fields.Many2one(
        comodel_name="import.data",
        string="Moulinette à lancer",
    )

    @api.model
    def run_action_moulinette(self, action, eval_context=None):
        action.sudo().moulinette.lancer_moulinette()
