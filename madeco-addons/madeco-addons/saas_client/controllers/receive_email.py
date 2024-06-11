##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import http
# import base64
from odoo.http import request
_logger = logging.getLogger(__name__)


class ReceiveEmail(http.Controller):

    @http.route(
        '/saas_client/receive_email', type='json', auth='public')
    def receive_email(
            self, message, custom_values=None, save_original=None, **post):
        _logger.info('Saas client message post called')
        env = request.env
        return env['mail.thread'].sudo().message_process(
            'crm.lead',
            message,
            custom_values,
            save_original)

    @http.route(
        '/saas_client/receive_email_mailgun/mime', type='http', auth='public',
        csrf=False)
    def receive_email_mailgun(self, **post):
        _logger.info('Saas client incoming message from mailgun')
        env = request.env
        env['mail.thread'].sudo().message_process(
            'crm.lead',
            post.get('body-mime'),
        )
        return http.Response("OK", status=200)
