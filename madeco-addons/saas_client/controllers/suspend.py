from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import ensure_db
from odoo.addons.web.controllers.main import Home


class SaaSClientLogin(Home):

    @http.route()
    def web_login(self, redirect=None, **kw):
        ensure_db()
        param_model = request.env['ir.config_parameter']
        suspended = param_model.sudo().get_param('saas_client.suspended', '0')
        if suspended == '1':
            request.params['login_success'] = False
            values = request.params.copy()
            suspended_message = param_model.sudo().get_param('saas_client.suspended_message', False)
            if not suspended_message:
                suspended_message = _('This databases was suspended. Please contact your odoo provider.')
            values['error'] = suspended_message
            return request.render('web.login', values)
        return super(SaaSClientLogin, self).web_login(redirect, **kw)
