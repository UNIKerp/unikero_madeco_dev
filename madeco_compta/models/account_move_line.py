# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.tools.float_utils import float_compare

import base64
import csv
import io
import re

import logging
logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    affich_bouton_lettrage_client = fields.Boolean(string="Affichage bouton lettrage_client", compute='_compute_affich_bouton_lettrage_client')  
    affich_bouton_lettrage_fourn = fields.Boolean(string="Affichage bouton lettrage_fourn", compute='_compute_affich_bouton_lettrage_fourn')  

 
    @api.depends('account_id', 'journal_id','partner_id')
    def _compute_affich_bouton_lettrage_client(self):
        for line in self:
            if line.journal_id.type == 'general' and line.partner_id and ((line.account_id.id == line.partner_id.property_account_receivable_id.id) or (line.account_id.id == line.partner_id.property_account_payable_id.id)):
                if line.account_id.code[0:3]=='411':
                    line.affich_bouton_lettrage_client = True
                else:
                    line.affich_bouton_lettrage_client = False    
            else:
                line.affich_bouton_lettrage_client = False

    @api.depends('account_id', 'journal_id','partner_id')
    def _compute_affich_bouton_lettrage_fourn(self):
        for line in self:
            if line.journal_id.type == 'general' and line.partner_id and ((line.account_id.id == line.partner_id.property_account_receivable_id.id) or (line.account_id.id == line.partner_id.property_account_payable_id.id)):
                if line.account_id.code[0:3]=='401':
                    line.affich_bouton_lettrage_fourn = True
                else:
                    line.affich_bouton_lettrage_fourn = False    
            else:
                line.affich_bouton_lettrage_fourn = False            


    def action_open_reconcile(self):
        # Open reconciliation view for customers and suppliers
        reconcile_mode = self.env.context.get("reconcile_mode", False)
        accounts = self.partner_id.property_account_payable_id
        if reconcile_mode == "customers":
            accounts = self.partner_id.property_account_receivable_id

        action_context = {
            "show_mode_selector": True,
            "partner_ids": [self.partner_id.id],
            "mode": reconcile_mode,
            "account_ids": accounts.ids,
        }
        return {
            "type": "ir.actions.client",
            "tag": "manual_reconciliation_view",
            "context": action_context,
        }
            