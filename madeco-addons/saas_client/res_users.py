
from odoo.addons.base.models.res_users import Users
from odoo import api
from odoo.exceptions import AccessDenied
from odoo import tools
import contextlib

old_get_login_domain = Users._get_login_domain


def new_get_login_domain(self, login):
    """ allow to connect with __system__ and admin, no matter it is inactive
    we make it on a monkey patch to allow use __system__ when creating db
    and saas_client is not installed yet
    """
    res = old_get_login_domain(self, login=login)
    if login in ['__system__', 'admin']:
        res += ['|', ('active', '=', False), ('active', '=', True)]
    return res


Users._get_login_domain = new_get_login_domain


# In 14.0 we need to monkeypatch this method too
old_check = Users.check


@classmethod
@tools.ormcache('uid', 'passwd')
def new_check(cls, db, uid, passwd):
    """Verifies that the given (uid, password) is authorized for the database ``db`` and
        raise an exception if it is not."""
    if not passwd:
        # empty passwords disallowed for obvious security reasons
        raise AccessDenied()

    with contextlib.closing(cls.pool.cursor()) as cr:
        self = api.Environment(cr, uid, {})[cls._name]
        with self._assert_can_auth():
            # We comment these lines out to allow to log in to archived users
            # if not self.env.user.active:
            #    raise AccessDenied()
            self._check_credentials(passwd, {'interactive': False})


Users.check = new_check
