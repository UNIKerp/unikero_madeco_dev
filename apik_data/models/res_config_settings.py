from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    company_id = fields.Many2one("res.company", "Société")
    apik_data_user = fields.Char(
        "User", related="company_id.apik_data_user", readonly=False
    )
    apik_data_password = fields.Char(
        "Mot de passe", related="company_id.apik_data_password", readonly=False
    )
