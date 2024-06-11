##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, SUPERUSER_ID, _
from odoo.addons.base.models.ir_config_parameter import _default_parameters
from odoo.exceptions import UserError


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model
    def sync_info(self):
        default_param = _default_parameters.copy()
        default_param.pop("web.base.url")
        for key, func in default_param.items():
            params = self.sudo().search([('key', '=', key)])
            params.set_param(key, func())
        return True
