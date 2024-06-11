##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import tools, api, models, fields, SUPERUSER_ID, _
from odoo.exceptions import ValidationError, AccessDenied
from odoo.addons.server_mode.mode import get_mode
from ast import literal_eval

import logging
_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    saas_provider_uuid = fields.Char(
        'SaaS Provider UUID',
        readonly=False,
        copy=False,
    )

    @api.model
    def _check_credentials(self, password, env):
        """
        Si el usuario es admin permitimos login con pass de instancia tmb
        Si el usuario es otro, permitimos con pass intancia o admin solo si:
        * no produccion
        * producción y allow on production True
        """
        passkey_allowed = True
        if not get_mode():
            if not literal_eval(
                    self.env['ir.config_parameter'].sudo().get_param(
                        'saas_client.allow_bypass_on_production',
                        'True')):
                passkey_allowed = False
        if self.env.uid != SUPERUSER_ID and passkey_allowed:
            # try with user pass
            try:
                super(ResUsers, self)._check_credentials(password, env)
                return True
            except AccessDenied:
                # try with instance password
                try:
                    self.check_super(password)
                    return True
                except AccessDenied:
                    return super(ResUsers, self)._check_credentials(password, env)
        # si es super admin, probamos tmb con clave de instancia
        elif self.env.uid in [SUPERUSER_ID, 2]:
            # try with instance password
            try:
                self.check_super(password)
                return True
            except AccessDenied:
                return super(ResUsers, self)._check_credentials(password, env)
        # si no es super admin y no hay passkey allowed, entonces por defecto
        else:
            return super(ResUsers, self)._check_credentials(password, env)
