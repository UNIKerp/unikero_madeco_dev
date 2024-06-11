##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Odoo Saas Client',
    'version': "14.0.1.0.0",
    'category': 'SaaS',
    'author': 'ADHOC SA,Odoo Community Association (OCA)',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'server_mode',
    ],
    'data': [
        'security/saas_client_security.xml',
        'security/ir.model.access.csv',
        'wizards/db_configuration_view.xml',
        'data/ir_config_parameter_data.xml',
        'data/ir_cron_data.xml',
        'data/res_users_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'demo': [
        'demo/res_users_demo.xml',
    ],
}