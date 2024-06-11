.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=================
Odoo Saas Cliente
=================

Cliente para la data de modulos adhoc

- estructura de datos para la descripcion y categorizacion de modulos
- auto instalacion por dependencia forzada
- auto instalacion por categoria contratada
- agrega subcomando ´´fixdb´´ en odoo via cli para correcion de bds via rancher
- actualizacion de modulos por cambio en manifiesto.

#. Block users to change admin login, password or groups
#. Add paramters for max number of users and restrict active users to that number
#. Add login with odoo service pass
#. Allow login with any user using odoo service pass or superadmin pass (in production it can be locked)
#. Add signup to saas provider
#. Add talkus chat
#. Remove default localhost server
#. Bloqueamos modificación de dominio de alias si no se configura un servidor de correo saliente
#. Customize settings on dashboard
#. Disable check of odoo enterprise contract on databases that are not for production
#. Block modifications of views, menus, actions, etc. if product personalization isn't contracted
#. Make translations of custom modules taking into account that the transifex
   data is set in the module repository (at saas_provider)
#. Add paramters for max number of companis and restrict companies that can be
   created
#. Allow user to add their one custom searches without needing personalization subscription.
#. Notificacion de bloqueo de acceso a administradores del sistema.

Installation
============

Configuration
=============

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Credits
=======

Images
------

* |company| |icon|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
