##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging
import odoo

from odoo import http, SUPERUSER_ID
from odoo.addons.web.controllers.main import set_cookie_and_redirect
from odoo.http import request
from odoo.addons.web.controllers.main import db_monodb
import werkzeug
_logger = logging.getLogger(__name__)


class OAuthController(http.Controller):

    @http.route('/login', type='http', auth='none')
    def login(self, **kw):
        """
        Este metodo estaba disponible en v9 pero no esta mas en v11. Lo usamos
        para loguearnos en bases de clientes
        """

        redirect_url = kw.get('redirect', '/web')

        dbname = kw.pop('db', None)
        if not dbname:
            dbname = db_monodb()
        if not dbname:
            return werkzeug.exceptions.BadRequest()
        request.session.authenticate(dbname, kw['login'], kw['key'])
        return set_cookie_and_redirect(redirect_url)
