# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)
import urllib
from werkzeug.wrappers import Response


from odoo import http, SUPERUSER_ID
from odoo.http import request


