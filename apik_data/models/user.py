from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    apik_data_select = fields.Boolean("Apik Data Select")
