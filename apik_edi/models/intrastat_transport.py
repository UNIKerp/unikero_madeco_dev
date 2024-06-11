# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
logger = logging.getLogger(__name__)


class IntrastatTransportMode(models.Model):
    _inherit = "intrastat.transport_mode"
    
    mode_transport_edi = fields.Selection([
        ('10', 'Transport maritime'),
        ('20', 'Transport ferroviaire'),
        ('30', 'Transport routier'),
        ('40', 'Transport aérien'),
        ('50', 'Courrier'),
        ('80', 'Transport fluvial'),
        ], required=True, default='30',string="Mode de transport EDI", copy=False)
    type_transport_edi = fields.Selection([
        ('23', 'Wagon de vrac'),
        ('25', 'Express rail'),
        ('31', 'Camion'),
        ('32', 'Camion citerne'),
        ('34', 'Colis express par route'),
        ('16E', 'Camion plat articulé 10T'),
        ('21E', 'Camion plat 15T'),
        ('34E', 'Remorque pour vrac'),
        ('36E', 'Camionnette'),
        ], required=True, default='31',string="Mode de transport EDI", copy=False)    


