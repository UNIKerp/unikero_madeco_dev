from odoo import models, api, _
from odoo.exceptions import UserError
import logging
logger = logging.getLogger(__name__)



class FetchmailServer(models.Model):
    _inherit = 'fetchmail.server'

    def button_confirm_login(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        email_in = get_param('saas_client.email_in')
        logger.info("login")
        logger.info(email_in)
        if not email_in:
            raise UserError(_(
                "You Can not Confirm & Test Because Odoo is not in the right mode."))
        return super(FetchmailServer, self).button_confirm_login()

    def fetch_mail(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        email_in = get_param('saas_client.email_in')
        if not email_in:
            raise UserError(_(
                "You Can not Fetch Mail Because Odoo is not in the right mode."))
        return super(FetchmailServer, self).fetch_mail()

    def connect(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        email_in = get_param('saas_client.email_in')
        if not email_in:
            raise UserError(_(
                "Can not Connect to server because Odoo is not in the right mode."))
        return super(FetchmailServer, self).connect()
