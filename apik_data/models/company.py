from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    apik_data_user = fields.Char("User")
    apik_data_password = fields.Char("Mot de passe")
