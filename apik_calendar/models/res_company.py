# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class res_company(models.Model):
    _inherit = 'res.company'
    
    nb_days_worked_per_week = fields.Integer(string="Number of days worked per week", default=5)
    nb_weekend_days = fields.Integer(string="Number weekend days", default=2)
    zone_geo = fields.Selection([
        ('metropole', 'Métropole'),
        ('alsacemoselle', 'Alsace-Moselle'),
        ('guadeloupe', 'Guadeloupe'),
        ('guyane', 'Guyane'),
        ('martinique', 'Martinique'),
        ('mayotte', 'Mayotte'),
        ('nouvellecaledonie', 'Nouvelle-Calédonie'),
        ('lareunion', 'La Réunion'),
        ('polynesie', 'Polynésie Française'),
        ('saintbarth', 'Saint-Barthélémy'),
        ('saintmartin', 'Saint-Martin'),
        ('wallis', 'Wallis-et-Futuna'),
        ('saintpierre','Saint-Pierre-et-Miquelon'),
        ], string="Zone géographique", required=True, default="metropole")
    


    @api.onchange("nb_days_worked_per_week")
    def get_nb_days_worked_per_week(self):
        for soc in self:
            if soc.nb_days_worked_per_week <= 7 :
                soc.nb_weekend_days = 7 - soc.nb_days_worked_per_week
            else:
                soc.nb_weekend_days = 0  
