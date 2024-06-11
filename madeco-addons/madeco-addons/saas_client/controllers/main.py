from odoo.addons.web.controllers.main import Home
import odoo.http as http
from werkzeug.exceptions import Forbidden


class SaasHome(Home):

    @http.route()
    def switch_to_admin(self):
        if http.request.env.user.id in [1, 2]:
            return super().switch_to_admin()
        return Forbidden()
