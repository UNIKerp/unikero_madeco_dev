##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import odoo.http as http
from odoo import _, tools
from odoo.service import db as db_ws
import tempfile
from .. import gcs

import logging
_logger = logging.getLogger(__name__)


class DbTools(http.Controller):

    @http.route(
        '/saas_client/restore_db',
        type='json',
        auth='none',
    )
    def restore_database(
            self, instance_password, bucket_type, bucket_name, object_key,
            db_name, access_id=None, access_key=None, gcs_json=None):
        _logger.info(
            "Starting restore process with data:\n"
            "* object_key: %s\n"
            "* bucket_name: %s\n"
            "* db_name: %s\n" % (
                object_key, bucket_name, db_name))

        if not tools.config.verify_admin_password(instance_password):
            return {'error': _('Incorrect ADMIN_PASSWORD')}

        if not bucket_name:
            return {'error': _('Bucket name is mandatory')}

        args = {}
        if bucket_type == 'aws_s3' and access_key and access_id:
            args.update({
                'aws_access_key_id': access_id,
                'aws_secret_access_key': access_key})

        with tempfile.NamedTemporaryFile() as file:
            if bucket_type == 'gcs':
                gcs.download_blob(
                    bucket_name, object_key, destination_file=file.name,
                    gcs_json=gcs_json)
            else:
                return {"error": "Aws S3 has been deprecated since 14.0"}
            try:
                _logger.info("Restoring from file %s", file.name)
                # por ahora solo implementamos copy=False para que sirva
                # restaurando bds que tienen contrato. Habria que ver
                # si necesitamos implementar generar nuevo uuid
                # TODO
                db_ws.restore_db(db_name, file.name, copy=False)
            except Exception as e:
                return {
                    "error": _(
                        "Unable to restore database '%s'.\n"
                        "Error: %s"
                    ) % (db_name, repr(e))
                }
        _logger.info("Databse %s restored succesfully!" % db_name)
        return {}
