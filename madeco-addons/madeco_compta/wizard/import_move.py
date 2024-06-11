# Copyright 2012-2020 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, date as datelib
import unicodecsv
from tempfile import TemporaryFile
import base64
import logging

logger = logging.getLogger(__name__)
try:
    import xlrd
except ImportError:
    logger.debug('Cannot import xlrd')

GENERIC_CSV_DEFAULT_DATE = '%d/%m/%Y'


class AccountMoveImport(models.TransientModel):
    _name = "account.move.import"
    _inherit = "account.move.import"
    
    def _partner_speed_dict(self):
        partner_speed_dict = {}
        company_id = self.env.company.id
        partner_sr = self.env['res.partner'].search_read(
            [
                '|',
                ('company_id', '=', company_id),
                ('company_id', '=', False),
                ('code_client_import_fec', '!=', False),
                ('parent_id', '=', False),
            ],
            ['code_client_import_fec'])
        for l in partner_sr:
            partner_speed_dict[l['code_client_import_fec'].upper()] = l['id']
        return partner_speed_dict

    

    

    