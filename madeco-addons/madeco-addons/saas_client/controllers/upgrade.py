import odoo.http as http
from odoo import _, api, SUPERUSER_ID
from odoo.service import db as db_ws
import odoo
import subprocess
import logging
import os
import psutil
from pathlib import Path

_logger = logging.getLogger(__name__)


class DbTools(http.Controller):

    log_file = '/tmp/upgrade.log'

    @http.route(
        '/saas_client/upgrade_database',
        type='json',
        auth='none',
    )
    def upgrade_database(
            self, instance_password, db_name, odoo_upgrade_repo,
            renamed_modules=None, merged_modules=None, to_remove=None, xmlid_renames=None,
            pre_migration=None, end_migration=None):
        """
        TODO. Revisar que ahora quedo viejo lo de abajo, podriamos hacer algo parecido a exp_migrate_databases,
        sería algo como "exp_migrate_databases" pero deberiamos correrlo en backround. A su vez, ademas deberiamos
        setear en el conf sobrel upgrade repo (Similar a como hace con el base, ver acá abajo). Igual por ahora
        dejamos como estabamos para minimizar los cambios (ya tenemos resuelto el control del pid el log y demas)
        odoo.tools.config['update']['base'] = True

        Usamos un odoo en paralelo porque al odoo actual no le podemos
        cambiar los addons path (si no usariamos algo parecido a
        exp_migrate_databases). Usamos subprocess para mandarlo en background
        (en vez de os)
        """

        if not odoo.tools.config.verify_admin_password(instance_password):
            return {'error': 'Clave de instancia incorrecta'}

        _logger.info('Upgrading database %s', db_name)

        # TODO en realidad todo esto estaria depreciado. Borrar o implementar con nueva modalidad / ruta de upgrade path
        if merged_modules or renamed_modules or to_remove or xmlid_renames:
            dynamic_data_path = os.path.join(odoo_upgrade_repo, "base/", "dynamic_data.py")
            f = open(dynamic_data_path, "w+")
            f.write("renamed_modules = %s\n" % renamed_modules or {})
            f.write("merged_modules = %s\n" % merged_modules or {})
            f.write("to_remove = %s\n" % to_remove or [])
            f.write("xmlid_renames = %s\n" % xmlid_renames or [])
            f.close()

        migrations_dir = "base/migrations/%s.1.4" % (os.environ.get('ODOO_VERSION'))
        Path(migrations_dir).mkdir(parents=True, exist_ok=True)
        if pre_migration:
            pre_migration_path = os.path.join(odoo_upgrade_repo, migrations_dir, "pre-migration.py")
            f = open(pre_migration_path, "w+")
            f.write(pre_migration)
            f.close()
        if end_migration:
            end_migration_path = os.path.join(odoo_upgrade_repo, migrations_dir, "end-migration.py")
            f = open(end_migration_path, "w+")
            f.write(end_migration)
            f.close()

        command = [
            "odoo", "--workers", "0", "--stop-after-init", "-d", db_name,
            "-u", "all", "--upgrade-path=%s" % odoo_upgrade_repo,
            "--without-demo=True", "--no-xmlrpc",
            "--logfile=%s" % self.log_file]
        try:
            p = subprocess.Popen(command)
        except Exception as e:
            error = (_(
                'Unable to upgrade bd %s, this is what we get: \n %s') % (
                db_name, e))
            return {'error': error}
        return {'pid': p.pid}

    @http.route(
        '/saas_client/get_upgrade_state',
        type='json',
        auth='none',
    )
    def get_upgrade_state(self, db_name, instance_password, upgrade_pid):
        """
        Por ahora consideramos que odoo actualizo bien si en el log se llega a
        la parte de computing left and...
        TODO otra alternativa es chequear si existe la palabra critical o error
        aparecen en el log, en ese caso, deberíamos generar un nuevo archivo de
        log para cada base y borrarlo antes de arrancar, para que no se
        confunda con errores de otros arranques
        """

        if not odoo.tools.config.verify_admin_password(instance_password):
            return {'error': 'Clave de instancia incorrecta'}

        _logger.info('Checking upgrade state on pid %s', upgrade_pid)
        # suponemos que si no hay pid es porque terminó
        try:
            process = psutil.Process(upgrade_pid)
            # luego de running queda como proceso idle..
            # if process.status() in ['running', 'sleeping']:
            if process.status() != 'zombie':
                return {'state': 'running'}
        except Exception:
            pass
            # error = (_(
            #     'Unable to get state, this is what we get: \n %s') % (e))
            # return {'error': error}

        log_lines = subprocess.check_output(['tail', '-10', self.log_file])

        # al final chequeamos si hay cirticial o error solamente
        # log_lines = subprocess.check_output(['tail', '-10', log_file])
        # if log_lines.find('CRITICAL', 'ERROR'):
        if log_lines.decode('utf-8').find(
                "odoo.modules.loading: Modules loaded") == -1:
            error = (
                'Abortando. Parece que hubo algun error en la '
                'actualización de odoo. Por favor revise "%s" e intente'
                'nuevamente') % (self.log_file)
            _logger.error(error)
            return {'error': error}
        # si el upgrade fue bien reseteamos el enviroment porque la
        # actualizacion se hizo en otro hilo y el server de odoo no se enteró
        api.Environment.reset()
        odoo.modules.registry.Registry.new(db_name, update_module=True)
        return {'state': 'ok'}
