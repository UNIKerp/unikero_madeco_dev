from odoo import fields, models


class ActionWizard(models.TransientModel):
    _name = "action.wizard"
    _description = "Action Wizard"

    name = fields.Char("Nom")
    moulinette = fields.Many2one("import.data", string="Moulinette")
    nom_action = fields.Char("Nom de l'action")
    objet = fields.Many2one("ir.model", "Objet")

    def creer_action(self):
        action_server_obj = self.env["ir.actions.server"]
        value = {
            "name": self.nom_action,
            "model_id": self.objet.id,
            "binding_model_id": self.objet.id,
            "state": "code",
            "code": "env['import.data'].search([('id','=',{})]).lancer_moulinette(records)".format(
                self.moulinette.id
            ),
        }
        action_server_obj.create(value)

        self.moulinette.model_action = self.objet.id

        return {}
