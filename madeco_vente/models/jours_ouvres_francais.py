# -*- coding: utf-8 -*-
"""
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
    Default Docstring
"""
import logging
import datetime
import calendar

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
from datetime import datetime

logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order' 

    ##############################################################
    #       Générateur de jours ouvrés français en python        #
    #############################################################
    def easter_date(self,year):
        """
        Calcule la date du jour de Pâques d'une année donnée
        Voir https://github.com/dateutil/dateutil/blob/master/dateutil/easter.py
        
        :return: datetime
        """
        a = year // 100
        b = year % 100
        c = (3 * (a + 25)) // 4
        d = (3 * (a + 25)) % 4
        e = (8 * (a + 11)) // 25
        f = (5 * a + b) % 19
        g = (19 * f + c - e) % 30
        h = (f + 11 * g) // 319
        j = (60 * (5 - d) + b) // 4
        k = (60 * (5 - d) + b) % 4
        m = (2 * j - k - g + h) % 7
        n = (g - h + m + 114) // 31
        p = (g - h + m + 114) % 31
        day = p + 1
        month = n
        easter_date = datetime(year, month, day)
        return easter_date


    def is_holiday(self,the_date):
        """
        Vérifie si la date donnée est un jour férié
        :param the_date: datetime
        :return: bool
        """
        year = the_date.year
        easter = self.easter_date(year)
        days = [
            datetime(year, 1, 1),  # Premier de l'an
            easter + timedelta(days=1),  # Lundi de Pâques
            datetime(year, 5, 1),  # Fête du Travail
            datetime(year, 5, 8),  # Victoire de 1945
            easter + timedelta(days=39),  # Ascension
            easter + timedelta(days=49),  # Pentecôte
            datetime(year, 7, 14),  # Fête Nationale
            datetime(year, 8, 15),  # Assomption
            datetime(year, 11, 1),  # Toussaint
            datetime(year, 11, 11),  # Armistice 1918
            datetime(year, 12, 25),  # Noël
        ]

        mois = the_date.month
        jour = the_date.day
        date_calc = datetime(year, mois, jour)

        if date_calc in days:
            error = True
        else:
            error = False

        return error


    def business_days(date_from, date_to):
        """
        Générateur retournant les jours ouvrés dans la période [date_from:date_to]
        :param date_from: Date de début de la période
        :param date_to: Date de fin de la période
        :return: Générateur
        """
        while date_from <= date_to:
            # Un jour est ouvré s'il n'est ni férié, ni samedi, ni dimanche
            if not is_holiday(date_from) and date_from.isoweekday() not in [6, 7]:
                yield date_from
            date_from += timedelta(days=1)


    def calcule_jour_ouvre_francais(self, date_controle):
        """
        Controle si une date est ouvrée ou fériée 
        :param date_controle: Date à contrôler
        :return: Date calculée 
        """
        date_calculee = date_controle
        if date_calculee:
            if date_calculee.weekday == 5:
                date_calculee += timedelta(days=2)
            if date_calculee.weekday == 6:
                date_calculee += timedelta(days=1)

            if self.is_holiday(date_calculee):
                date_calculee += timedelta(days=1) 

        return date_calculee               

        