##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
# from odoo import pooler
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class DatabaseToolsConfiguration(models.TransientModel):
    _name = 'db.configuration'
    _description = 'db.configuration'

    # dummy field to force computation of _compute_modules_data on create
    name = fields.Char(
        default='dummy',
    )
    update_detail = fields.Text(
        'Update Detail',
        readonly=True,
        compute='_compute_modules_data',
        # default=_get_update_detail,
    )
    update_state = fields.Selection([
        ('init_and_conf_required', 'Init and Config Required'),
        ('update_required', 'Update Required'),
        ('optional_update', 'Optional Update'),
        ('on_to_install', 'On To Install'),
        ('on_to_remove', 'On To Remove'),
        ('on_to_upgrade', 'On To Upgrade'),
        ('unmet_deps', 'Unmet Dependencies'),
        ('not_installable', 'Not Installable Modules'),
        ('ok', 'Ok'),
        ('installed_uninstallable', 'Installed Uninstallable'),
        ('installed_uncontracted', 'Installed Uncontracted'),
        ('uninstalled_auto_install', 'Uninstalled Auto Install'),
    ],
        'Modules Status',
        readonly=True,
        compute='_compute_modules_data',
        # default=_get_update_state,
    )
    init_and_conf_required_modules = fields.Many2many(
        'ir.module.module',
        compute='_compute_modules_data',
    )
    update_required_modules = fields.Many2many(
        'ir.module.module',
        compute='_compute_modules_data',
        string='Update Required',
    )
    optional_update_modules = fields.Many2many(
        'ir.module.module',
        compute='_compute_modules_data',
        string='Optional Update',
    )
    to_remove_modules = fields.Many2many(
        'ir.module.module',
        compute='_compute_modules_data',
        string='To Remove',
    )
    to_install_modules = fields.Many2many(
        'ir.module.module',
        compute='_compute_modules_data',
        string='To Install',
    )
    to_upgrade_modules = fields.Many2many(
        'ir.module.module',
        compute='_compute_modules_data',
        string='To Upgrade',
    )
    unmet_deps_modules = fields.Many2many(
        'ir.module.module',
        compute='_compute_modules_data',
        string='Unmet Dependencies',
    )
    not_installable_modules = fields.Many2many(
        'ir.module.module',
        compute='_compute_modules_data',
        string='Not Installable',
    )
    imported_modules = fields.Many2many(
        'ir.module.module',
        compute='_compute_modules_data',
    )

    # dummy depends to get initial data
    # TODO fix this, it can not depends on same field
    # @api.depends('update_state')
    @api.depends('name')
    def _compute_modules_data(self):
        for rec in self:
            overal_state = self.env[
                'ir.module.module'].get_overall_update_state()
            rec.update_state = overal_state['state']
            rec.update_detail = overal_state['detail']
            modules_state = overal_state['modules_state']
            # modules_state = self.env['ir.module.module']._get_modules_state()
            rec.init_and_conf_required_modules = modules_state.get(
                'init_and_conf_required')
            rec.update_required_modules = modules_state.get('update_required')
            rec.optional_update_modules = modules_state.get('optional_update')
            rec.unmet_deps_modules = modules_state.get('unmet_deps')
            rec.not_installable_modules = modules_state.get('not_installable')
            rec.imported_modules = modules_state.get('imported_modules')
            rec.to_upgrade_modules = modules_state.get('to_upgrade_modules')
            rec.to_install_modules = modules_state.get('to_install_modules')
            rec.to_remove_modules = modules_state.get('to_remove_modules')

    def action_fix_db(self):
        """
        Si lo hacemos por interfaz entonces si forzamos la desinstalacion
        porque esto es manual
        """
        self.fix_db(raise_msg=True, uninstall_modules=True)

    @api.model
    def fix_db(
            self, raise_msg=False,
            uninstall_modules=False):
        """
        Desde el cron:
        1. para no mandarnos errores, no desintalamos ningun modulo
        podria pasar de que falta un repo y borramos mucha data (los script
        de los modulos deberianser quien se encarguen de limpiar)
        2. solo actualizamos si hay modulos que requiran update o dependencias
        faltantes
        """
        # because we make methods with api multi and we use a computed field
        # we need an instance of this class to run some methods

        # TODO tal vez deberiamos ahcer que unmet_deps no sea campo m2m porque
        # si la dependencia es nueva y no se actualiza en el modulo con nueva
        # dependencia la version, entonces el update state va a devolver ok
        # ya que el modulo no es visto por el orm, el problema esta en la
        # funcion _get_modules_state que hacemos un search, deberiamos
        # directamente devolver los nombres. Igualmente, si al modulo se le
        # cambia la version, se actualiza la lista de modulos y el invalidate
        # cache hace que sea visible
        self = self.create({})

        update_state = self.update_state

        error_msg = False
        if update_state == 'ok':
            error_msg = 'No need to fix db'
        # elif update_detail['init_and_conf_required']:
        #     error_msg = _(
        #         'You can not fix db, there are some modules with "Init and '
        #         'Config". Please correct them manually. Modules %s: ') % (
        #         update_detail['init_and_conf_required'])

        # if anything to fix, we exit
        if error_msg:
            if raise_msg:
                raise ValidationError(error_msg)
            _logger.info(error_msg)
            return {'error': error_msg}

        _logger.info('Fixing database')

        # if automatic backups enable, make backup
        # we use pg_dump to make backups quickly
        # TODO reactvamos esto? lo sacamos por ahora porque no usamos
        # mas el db tools
        # if self.env['db.database'].check_automatic_backup_enable():
        #     self.backup_db(backup_format='pg_dump')

        # como ahora odoo actualiza la lista de modulos todo el tiempo
        # probamos sacarlo para reducir el tiempo
        # _logger.info('Updating modules list')
        # self.env['ir.module.module'].sudo().update_list()
        # # necesario para que unmet deps y otros se actualicen con nuevos
        # # modulos
        # self.invalidate_cache()
        # _logger.info('Modules list updated')

        self.set_to_install_unmet_deps()

        if uninstall_modules:
            self.set_to_uninstall_not_installable_modules()

        self.set_to_update_required_modules()
        self.set_to_update_optional_modules()
        self.set_to_update_init_and_conf_required_modules()

        # no estoy seguro porque pero esto ayuda a que no quede trabado cuando
        # llamamos a upgrade_module
        # save before re-creating cursor below on upgrade
        self._cr.commit()  # pylint: disable=invalid-commit
        modules = self.env['ir.module.module']
        _logger.info(
            'Runing upgrade module.\n'
            '* Modules to upgrade: %s\n'
            '* Modules to install: %s\n'
            '* Modules to remove: %s' % (
                modules.search([('state', '=', 'to upgrade')]).mapped('name'),
                modules.search([('state', '=', 'to install')]).mapped('name'),
                modules.search([('state', '=', 'to remove')]).mapped('name'),
            ))
        self.env['base.module.upgrade'].sudo().upgrade_module()
        _logger.info('Upgrade module finished')

        if uninstall_modules:
            # borramos los registros de modulos viejos para que no jodan
            # to install, necesitamos el commit para tener cambio de estado
            self.env.cr.commit()  # pylint: disable=invalid-commit
            self.not_installable_modules.sudo().unlink()
        # otra forma de hacerlo
        # pooler.restart_pool(self._cr.dbname, update_module=True)
        # interesante para analizar esto
        # odoo.modules.registry.Registry.new(
        #     cr.dbname, update_module=True)
        return {}

    def clean_todo_list(self):
        return self.env['base.module.upgrade'].upgrade_module_cancel()

    def set_to_uninstall_not_installable_modules(self):
        _logger.info('Fixing not installable')
        self.not_installable_modules.sudo()._set_to_uninstall()
        return True

    def set_to_install_unmet_deps(self):
        _logger.info('Fixing unmet dependencies')
        self.unmet_deps_modules.sudo()._set_to_install()
        return True

    def set_to_update_optional_modules(self):
        _logger.info('Fixing optional update modules')
        return self.optional_update_modules.sudo()._set_to_upgrade()

    def set_to_update_required_modules(self):
        _logger.info('Fixing update required modules')
        return self.update_required_modules.sudo()._set_to_upgrade()

    def set_to_update_init_and_conf_required_modules(self):
        _logger.info('Fixing update required modules')
        return self.init_and_conf_required_modules.sudo()._set_to_upgrade()
