# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    sscc_gs1_identifier = fields.Char(string="Data identifier GS1", default="00", required=True)
    sscc_extension_character = fields.Integer(string="Extension character", required=True)
    sscc_company_prefix = fields.Integer(string="Company prefix", required=True) # TODO: big int ?

    @api.constrains('sscc_extension_character')
    def _check_sscc_extension_character(self):
        for record in self:
            if record.sscc_extension_character > 9 or record.sscc_extension_character < 0:
                raise ValidationError(_("The extension character must be between 0 and 9"))

    @api.constrains('sscc_company_prefix')
    def _check_sscc_company_prefix(self):
        for record in self:
            if len(str(record.sscc_company_prefix)) < 6 or len(str(record.sscc_company_prefix)) > 12:
                raise ValidationError(_("The company prefix must have a length between 6 and 12"))
