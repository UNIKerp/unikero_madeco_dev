from odoo import models, api, fields, tools, _
from datetime import datetime
from odoo.service import db
from odoo.exceptions import ValidationError, UserError
from odoo.addons.server_mode.mode import get_mode
from urllib.parse import urlencode
from .. import gcs

try:
    import pycurl
except ImportError:
    pycurl = None

from tempfile import NamedTemporaryFile
import os
import sys

import logging
_logger = logging.getLogger(__name__)


class SaasClientDashboard(models.TransientModel):
    """
    Modelo generico para implementar funcionalidades no ligadas a ningun
    objeto en particular y tambien para poder utilizar como panel de control
    y de configuracion
    """
    _name = 'saas_client.dashboard'
    _description = 'saas_client.dashboard'

    # TODO deprecate this on v14 and use only saas_run_sql

    @api.model
    def run_sql(self, sql, fetchall=False, do_not_raise=False):
        """This is used to run sql queries when upgrading a database.
        TODO sanitize sql
        """
        if do_not_raise:
            try:
                return self._run_sql(sql, fetchall=fetchall)
            except Exception:
                return True
        else:
            return self._run_sql(sql, fetchall=fetchall)

    @api.model
    def _run_sql(self, sql, fetchall=False):
        if not get_mode():
            return 'No se puede correr run_sql en entornos de produccion'
        if self._uid != 1:
            _logger.warning('Run sql can only be used by superadmin')
            return False
        self._cr.execute(sql)
        if fetchall:
            return self._cr.fetchall()
        else:
            return True

    @api.model
    def get_bucket_type(self):
        # TODO tal vez sea mejor crear un parametro saas_client.storage_type
        get_param = self.env['ir.config_parameter'].sudo().get_param
        if get_param('saas_client.gcs_bucket'):
            return 'gcs'
        else:
            raise ValidationError(_('No hay bucket configurado'))

    def action_backup_now(self):
        if get_mode():
            raise UserError(
                'Esta función no está disponible para bases de pruebas')
        self.backup_database()

    def action_list_backups(self):
        self.ensure_one()
        if get_mode():
            raise UserError(
                'Esta función no está disponible para bases de pruebas')
        if self.get_bucket_type() == 'gcs':
            msg = 'This are the available backups:\n%s' % '*\n'.join([
                "{name}\t{size}\t{created}".format(
                    name=key.name,
                    size=key.size,
                    created=key.time_created,
                ) for key in self._gcs_list()])
        raise ValidationError(msg)

    @api.model
    def cron_backup_database(self):
        """If backups enable in ir parameter, then:
        * Check if backups are enable
        * Make backup according to period defined
        * """
        if get_mode():
            _logger.info(
                'Automtatic backups are disable by server_mode.'
                'If you want to enable it you should remove develop or test '
                'value for server_mode key on openerp server config file')
            return False
        _logger.info('Running backups cron')
        self.backup_database()
        self.backups_rotation()
        return True

    @api.model
    def _get_account_prefix(self):
        """
        Backup prefix se compone del nombre de cuenta (unico para toda la
        oferta) y el nombre de la base, de esta manera garantizamos que si
        un cliente pide backups para su nombre de cuenta, solo obtenga los
        de el, ejs;
        nombre de cuenta: "saas_provider"
        backup de prod: "saas_provider_saas-provder"
        backup de test: "saas_provider_test-saas-provder"
        puede ver todos los backups que empicen con saas_provider_
        Agregamos el guion ya que esta prohibido en nombres de cuentas y nos
        ayuda a que sea unico realmente, si no si tuviesemos "saas_provider" y
        "saas" como nombres de cuenta, obtendriamos ambos con el prefix "saas"
        """
        account_name = self.env['ir.config_parameter'].sudo().get_param(
            'saas_client.account_name')
        if not account_name:
            raise ValidationError(_(
                'Account name parameter is mandatory for backups operations'))
        return "%s_" % account_name

    @api.model
    def backup_database(self, backup_format='zip'):
        """
        Por ahora, como solo tenemos implementado backup en aws, si aws
        no esta activo no hacemos backup
        """
        res = {}
        storage_type = self.get_bucket_type()
        db_name = self.env.cr.dbname
        _logger.info('Running "%s" database backup' % db_name)
        filename = (
            "%(account_prefix)s%(db_name)s_%(timestamp)s%(odoo_version)s"
            ".zip" % {
                'account_prefix': self._get_account_prefix(),
                'db_name': db_name,
                'timestamp': datetime.utcnow().strftime(
                    "%Y-%m-%d_%H-%M-%S"),
                'odoo_version': os.environ.get('ODOO_VERSION') and "-%s" % (
                    os.environ.get('ODOO_VERSION') or '')})
        try:
            with NamedTemporaryFile() as destiny:
                db.saas_dump_db(
                    self.env.cr.dbname, destiny, backup_format=backup_format)
                # if _gcs_upload_backup:
                if storage_type == 'gcs':
                    self._gcs_upload_backup(destiny.name, filename)
                res['key'] = filename
        except Exception as e:
            _logger.exception('An error happened during database %s backup' % (
                db_name))
            res['status'] = 'fail'
            res['message'] = str(e)
        return res

    @api.model
    def backups_rotation(self):
        """
        Creamos esta funcion simplemente para ser mas prolijos por si queremos
        extender a otros servicios distintos a s3
        """
        _logger.info('Running backups rotation')
        storage_type = self.get_bucket_type()
        if storage_type == 'gcs':
            return self._gcs_backups_rotation()

    @api.model
    def odoo_upload_database(self, odoo_request_key, odoo_request_nbr):
        """Upload backup to odoo upgrade request
        """
        UPLOAD_URL = "https://upgrade.odoo.com/database/v1/upload"
        _logger.info('Haciendo backup')
        with tools.osutil.tempdir() as dump_dir:
            db_name = self._cr.dbname
            DUMPFILE = "%s/%s.gz" % (dump_dir, db_name)
            _logger.info(
                'Haciendo backup y comprimiendo archivo %s' % DUMPFILE)
            os.system('pg_dump %s | gzip -9 > %s' % (db_name, DUMPFILE))
            _logger.info('Subiendo a odoo archivo %s' % DUMPFILE)
            try:
                fields = dict([
                    ('request', odoo_request_nbr),
                    ('key', odoo_request_key),
                ])
                headers = {"Content-Type": "application/octet-stream"}
                postfields = urlencode(fields)

                c = pycurl.Curl()
                c.setopt(pycurl.URL, UPLOAD_URL + "?" + postfields)
                c.setopt(pycurl.POST, 1)
                filesize = os.path.getsize(DUMPFILE)
                c.setopt(pycurl.POSTFIELDSIZE, filesize)
                fp = open(DUMPFILE, 'rb')
                c.setopt(pycurl.READFUNCTION, fp.read)
                c.setopt(
                    pycurl.HTTPHEADER,
                    ['%s: %s' % (k, headers[k]) for k in headers])

                c.perform()
                c.close()
            except Exception as e:
                return {'error': '%s' % e}
            return {}

    @api.model
    def _gcs_get_bucket(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        gcs_json = get_param('saas_client.gcs_json')
        bucket_name = get_param('saas_client.gcs_bucket')
        if not bucket_name:
            raise ValidationError('Bucket name is mandatory!')
        return gcs.get_bucket(bucket_name, gcs_json)

    @api.model
    def _gcs_upload_backup(self, filename, blob_name):
        '''
        send db dump to gc storage
        '''
        _logger.info('Uploading backup to GCS')
        bucket = self._gcs_get_bucket()

        _logger.info('Backup size %s' % sys.getsizeof(filename))
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(filename)
        _logger.info('Data successfully backed up to GCS')
        return True

    @api.model
    def _gcs_list(self):
        bucket = self._gcs_get_bucket()
        return bucket.list_blobs(prefix=self._get_account_prefix())

    @api.model
    def _gcs_backups_rotation(self):
        _logger.warning('Storage rotation for gc storage not implemented yet')
        return True
