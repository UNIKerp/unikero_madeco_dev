# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class PartnerSubcontractingDeadlines(models.Model):

    _name = "partner.subcontracting.deadlines"
    _rec_name = 'partner_id'
    _description = 'Partner subcontracting deadlines'
    _order = 'partner_id, quantity_below ASC, id'

    active = fields.Boolean(default=True)
    partner_id = fields.Many2one('res.partner', string="Partner", ondelete='cascade', required=True, index=True)
    quantity_below = fields.Integer(string="Quantity below (units)", required=True)
    production_time = fields.Integer(string="Production time (days) + delivery", required=True)
    
