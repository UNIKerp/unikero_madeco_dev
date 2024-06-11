# -*- coding: utf-8 -*-


import logging
from datetime import datetime
import os
from tempfile import NamedTemporaryFile
import requests
import zipfile
import sys
from ftplib import FTP
import pysftp
import json
import multiprocessing
import sys
import math
from multiprocessing.pool import Pool

from odoo import models, fields, api, _
from odoo.service import db
from odoo.exceptions import ValidationError, UserError
from odoo.tools import config

from .. import aws_s3
from .. import ftp

_logger = logging.getLogger(__name__)

try:
    parallel_upload = False
    from filechunkio import FileChunkIO

    parallel_upload = True
except ImportError as err:
    _logger.error(err)


def get_dir_size(path="."):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(
                os.path.join(root, file),
                os.path.relpath(os.path.join(root, file), os.path.join(path, "..")),
            )


def _upload_part(
    bucket, multipart_id, part_num, source_path, offset, bytes, amount_of_retries=10
):
    """
    Uploads a part with retries.
    based on http://www.topfstedt.de/
        python-parallel-s3-multipart-upload-with-retries.html
    """

    def _upload(retries_left=amount_of_retries):
        try:
            _logger.info("Start uploading part # %d ..." % part_num)
            for mp in bucket.get_all_multipart_uploads():
                if mp.id == multipart_id:
                    with FileChunkIO(
                        source_path, "r", offset=offset, bytes=bytes
                    ) as fp:
                        mp.upload_part_from_file(fp=fp, part_num=part_num)
                    break
        except Exception as exc:
            if retries_left:
                _upload(retries_left=retries_left - 1)
            else:
                logging.info(
                    "... Failed uploading part # %d. Error %s" % (part_num, exc)
                )
                raise exc
        else:
            logging.info("... Uploaded part # %d" % part_num)

    _upload()


class SaasClientDashboard(models.TransientModel):
    _name = "saas_client.dashboard"
    _inherit = "saas_client.dashboard"

    @api.model
    def _s3_upload_backup(self, filename, key):
        """
        send db dump to S3
        TODO: si queremos mejorar velocidad podriamos implmentar el paralell
        method como hace el otro proyecto saas
        en teroia se deberia poder usar upload_file que deberia partir
        automaticamente, al menos disponible en boto3
        """

        _logger.info("Uploading backup to aws S3")
        bucket = self._s3_get_bucket()

        _logger.info("Backup size %s" % sys.getsizeof(filename))
        # parallel_upload desctivado porque aws nos devuelve un error
        # de permisos
        _logger.info("Backup en parallel")
        self._transport_backup_parallel(filename, key, bucket)
        """
        parallel_upload = True
        if parallel_upload and sys.getsizeof(filename) > 5242880:
            self._transport_backup_parallel(filename, key, bucket)
        else:
            _logger.info('Uploading simple')
            k = aws_s3.Key(bucket)
            k.key = key
            k.set_contents_from_filename(filename)
        """
        _logger.info("Data successfully backed up to s3")
        return True

    @api.model
    def get_bucket_type(self):
        # TODO tal vez sea mejor crear un parametro saas_client.storage_type
        get_param = self.env["ir.config_parameter"].sudo().get_param
        list_bucket = []
        if get_param("saas_client.gcs_bucket"):
            list_bucket.append("gcs")
        if get_param("saas_client.aws_s3_bucket"):
            list_bucket.append("aws_s3")
        if get_param("saas_client.ftp_bucket"):
            list_bucket.append("ftp")
        if get_param("saas_client.sftp_bucket"):
            list_bucket.append("sftp")
        if len(list_bucket) == 0:
            raise ValidationError(_("No hay bucket configurado"))
        return list_bucket

    def action_list_backups(self):
        self.ensure_one()
        if get_mode():
            raise UserError("Esta función no está disponible para bases de pruebas")
        if "gcs" in self.get_bucket_type():
            msg["gcs"] = "This are the available backups:\n%s" % "*\n".join(
                [
                    "{name}\t{size}\t{created}".format(
                        name=key.name,
                        size=key.size,
                        created=key.time_created,
                    )
                    for key in self._gcs_list()
                ]
            )
        if "aws_s3" in self.get_bucket_type():
            msg["aws_s3"] = "This are the available backups:\n%s" % "*\n".join(
                [
                    "{name}\t{size}\t{modified}".format(
                        name=key.name,
                        size=key.size,
                        modified=key.last_modified,
                    )
                    for key in self._s3_list()
                ]
            )

        for k in msg.keys():
            msg += msg[k]

        raise ValidationError(msg)

    @api.model
    def _transport_backup_parallel(self, filename, key, bucket):
        """
        Parallel multipart upload.
        """
        headers = {}
        _logger.info("Backing up via S3 parallel multipart upload agent")
        source_size = os.stat(filename).st_size
        parallel_processes = (multiprocessing.cpu_count() * 2) + 1

        mtype = "application/zip, application/octet-stream"
        headers.update({"Content-Type": mtype})

        mp = bucket.initiate_multipart_upload(key, headers=headers)

        bytes_per_chunk = max(int(math.sqrt(5242880) * math.sqrt(source_size)), 5242880)
        chunk_amount = int(math.ceil(source_size / float(bytes_per_chunk)))

        pool = Pool(processes=parallel_processes)
        for i in range(chunk_amount):
            offset = i * bytes_per_chunk
            remaining_bytes = source_size - offset
            bytes = min([bytes_per_chunk, remaining_bytes])
            part_num = i + 1
            pool.apply_async(
                _upload_part, [bucket, mp.id, part_num, filename, offset, bytes]
            )
        pool.close()
        pool.join()

        if len(mp.get_all_parts()) == chunk_amount:
            mp.complete_upload()
        else:
            mp.cancel_upload()

    @api.model
    def _s3_list(self):
        bucket = self._s3_get_bucket()
        return bucket.list(prefix=self._get_account_prefix())

    @api.model
    def _s3_backups_rotation(self):
        """
        Metodo que borra los backups de aws s3 segun la rotacion que queramos
        para los mismos, aprovechamos una libreria de python que a su vez usa
        otra (rotatebackups).
        Por ahora el esquema de rotación es fijo pero podemos ver de hacerlo
        variable si lo necesitamos.
        """
        rotation_scheme = {
            "daily": 7,
            "weekly": 4,
            "monthly": 12,
            "yearly": 1,
        }
        include_list = [self._get_account_prefix() + "*"]
        get_param = self.env["ir.config_parameter"].sudo().get_param
        aws_s3_accessid = get_param("saas_client.aws_s3_accessid")
        aws_s3_accesskey = get_param("saas_client.aws_s3_accesskey")
        aws_s3_bucket = get_param("saas_client.aws_s3_bucket")

        # S3RotateBackups requiere los argumetnos estos pero si pasamos
        # none funciona, con False da error
        aws_s3_accessid = aws_s3_accessid or None
        aws_s3_accesskey = aws_s3_accesskey or None
        S3RotateBackups(
            aws_access_key_id=None,
            aws_secret_access_key=None,
            rotation_scheme=rotation_scheme,
            include_list=include_list,
        ).rotate_backups(aws_s3_bucket)
        return True

    @api.model
    def backup_database(self, backup_format="zip"):
        get_param = self.env["ir.config_parameter"].sudo().get_param

        uuid = get_param("saas_client.database_uuid")
        url = "{}/apix/backup/".format(get_param("saas_client.provider_url"))
        res = {}
        storage_type = self.get_bucket_type()
        db_name = self.env.cr.dbname
        _logger.info('Running "%s" database backup' % db_name)
        filename = (
            "%(account_prefix)s%(db_name)s_%(timestamp)s%(odoo_version)s"
            ".zip"
            % {
                "account_prefix": self._get_account_prefix(),
                "db_name": db_name,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S"),
                "odoo_version": os.environ.get("ODOO_VERSION")
                and "-%s" % (os.environ.get("ODOO_VERSION") or ""),
            }
        )

        custom_filename = (
            "%(account_prefix)s%(db_name)s_custom_addons_%(timestamp)s%(odoo_version)s"
            ".zip"
            % {
                "account_prefix": self._get_account_prefix(),
                "db_name": db_name,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S"),
                "odoo_version": os.environ.get("ODOO_VERSION")
                and "-%s" % (os.environ.get("ODOO_VERSION") or ""),
            }
        )

        def error_backup(dbname, uuid, res, e, destination):
            _logger.info("An error happened during database %s backup" % (db_name))
            res["status"] = "fail"
            res["message"] = {
                "error": True,
                "message": str(e) + " - {}".format(destination),
            }
            data = {"message": json.dumps(res["message"]), "uuid": uuid}
            requests.post(url, data=data)

        def ok_backup(dbname, uuid, res, destination):
            _logger.info("Backup OK sur {}".format(destination))
            res["message"] = {
                "error": False,
                "message": "Backup Ok sur {}".format(destination),
            }
            data = {"message": json.dumps(res["message"]), "uuid": uuid}
            _logger.info(data)
            requests.post(url, data=data)

        with NamedTemporaryFile() as destiny:
            db.dump_db(self.env.cr.dbname, destiny, backup_format=backup_format)
            _logger.info(destiny.name)

            if "gcs" in storage_type:
                _logger.info("Backup GCS")
                try:
                    self._gcs_upload_backup(destiny.name, filename)
                    ok_backup(db_name, uuid, res, "GCS")
                except Exception as e:
                    error_backup(db_name, uuid, res, e, "GCS")

            if "aws_s3" in storage_type:
                _logger.info("Backup AWS")
                try:
                    self._s3_upload_backup(destiny.name, key=filename)
                    ok_backup(db_name, uuid, res, "AWS")
                except Exception as e:
                    error_backup(db_name, uuid, res, e, "AWS")

            if "ftp" in storage_type:
                _logger.info("Backup FTP")
                try:
                    self._ftp_upload_backup(destiny.name, filename)
                    ok_backup(db_name, uuid, res, "FTP")
                except Exception as e:
                    error_backup(db_name, uuid, res, e, "FTP")

            if "sftp" in storage_type:
                _logger.info("Backup SFTP")
                try:
                    self._sftp_upload_backup(destiny.name, filename)
                    ok_backup(db_name, uuid, res, "SFTP")
                except Exception as e:
                    error_backup(db_name, uuid, res, e, "SFTP")

            res["key"] = filename

        with NamedTemporaryFile() as destiny:
            with zipfile.ZipFile(destiny, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipdir("src/repositories/", zipf)
                _logger.info(destiny.name)

            if "gcs" in storage_type:
                _logger.info("Backup Custom addons GCS")
                try:
                    self._gcs_upload_backup(destiny.name, custom_filename)
                    ok_backup(db_name, uuid, res, "GCS")
                except Exception as e:
                    error_backup(db_name, uuid, res, e, "GCS")

            if "aws_s3" in storage_type:
                _logger.info("Backup Custom addons AWS")
                try:
                    self._s3_upload_backup(destiny.name, key=custom_filename)
                    ok_backup(db_name, uuid, res, "AWS")
                except Exception as e:
                    error_backup(db_name, uuid, res, e, "AWS")

            if "ftp" in storage_type:
                _logger.info("Backup Custom addons FTP")
                try:
                    self._ftp_upload_backup(destiny.name, custom_filename)
                    ok_backup(db_name, uuid, res, "FTP")
                except Exception as e:
                    error_backup(db_name, uuid, res, e, "FTP")

            if "sftp" in storage_type:
                _logger.info("Backup Custom addons SFTP")
                try:
                    self._sftp_upload_backup(destiny.name, custom_filename)
                    ok_backup(db_name, uuid, res, "SFTP")
                except Exception as e:
                    error_backup(db_name, uuid, res, e, "SFTP")

            res["key"] = filename

        return res

    @api.model
    def backups_rotation(self):
        """
        Creamos esta funcion simplemente para ser mas prolijos por si queremos
        extender a otros servicios distintos a s3
        """
        _logger.info("Running backups rotation")
        storage_type = self.get_bucket_type()
        if "gcs" in storage_type:
            return self._gcs_backups_rotation()
        if "aws_s3" in storage_type:
            return self._s3_backups_rotation()
        if "ftp" in storage_type:
            return self._ftp_backups_rotation()
        if "sftp" in storage_type:
            return self._sftp_backups_rotation()

    @api.model
    def _ftp_get_bucket(self):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        ftp_user = get_param("saas_client.ftp_user")
        ftp_password = get_param("saas_client.ftp_password")
        ftp_url = get_param("saas_client.ftp_url")
        bucket_name = get_param("saas_client.ftp_bucket")
        if not bucket_name:
            raise ValidationError(_("Bucket name is mandatory!"))
        args = {}
        if ftp_user and ftp_password and ftp_url:
            args.update(
                {
                    "ftp_user": ftp_user,
                    "ftp_password": ftp_password,
                    "ftp_url": ftp_url,
                }
            )
        return ftp.get_bucket(bucket_name, **args)

    @api.model
    def _s3_get_bucket(self):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        access_id = get_param("saas_client.aws_s3_accessid")
        access_key = get_param("saas_client.aws_s3_accesskey")
        bucket_name = get_param("saas_client.aws_s3_bucket")
        if not bucket_name:
            raise ValidationError(_("Bucket name is mandatory!"))
        args = {"host": "s3-eu-west-1.amazonaws.com"}
        if access_key and access_id:
            args.update(
                {"aws_access_key_id": access_id, "aws_secret_access_key": access_key}
            )
        return aws_s3.get_bucket(bucket_name, **args)

    @api.model
    def _ftp_upload_backup(self, filename, blob_name):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        ftp_user = get_param("saas_client.ftp_user")
        ftp_password = get_param("saas_client.ftp_password")
        ftp_url = get_param("saas_client.ftp_url")
        ftp_port = get_param("saas_client.ftp_port")
        bucket_name = get_param("saas_client.ftp_bucket")

        ftp = FTP()
        ftp.connect(ftp_url, int(ftp_port))
        ftp.login(ftp_user, ftp_password)

        with open(filename, "rb") as fp:
            ftp.storbinary("STOR " + blob_name, fp)
        ftp.quit()

        return True

    @api.model
    def _sftp_upload_backup(self, filename, blob_name):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        sftp_user = get_param("saas_client.sftp_user")
        sftp_password = get_param("saas_client.sftp_password")
        sftp_url = get_param("saas_client.sftp_url")
        sftp_port = get_param("saas_client.sftp_port")
        bucket_name = get_param("saas_client.sftp_bucket")

        sftp = pysftp.Connection(
            host=sftp_url,
            username=sftp_user,
            password=sftp_password,
            port=int(sftp_port),
        )

        sftp.put(filename, blob_name)

        return True

    @api.model
    def _ftp_backups_rotation(self):
        _logger.debug("Storage rotation for FTP storage not implemented yet")
        return True

    @api.model
    def _sftp_backups_rotation(self):
        _logger.debug("Storage rotation for SFTP storage not implemented yet")
        return True

    @api.model
    def get_size(self, db_name=None):
        database = self.get_database_size(db_name)
        filestore = self.get_filestore_size(db_name)

        return database, filestore

    @api.model
    def get_filestore_size(self, db_name=None):
        if not db_name:
            db_name = config.options.get("db_name")

        if not db_name:
            _logger.error("No database name.")
            return 0.0

        parts = [config.options.get("data_dir"), "filestore", db_name]
        path = os.path.join(*list(map(str, parts)))

        if not os.path.exists(path):
            _logger.error("Path '%s' doesn't exist", path)
            return 0.0

        return get_dir_size(path)

    @api.model
    def get_database_size(self, db_name=None):
        if not db_name:
            db_name = config.options.get("db_name")

        if not db_name:
            _logger.error("No database name.")
            return 0

        req = "SELECT pg_database_size(%s)"

        self._cr.execute(req, [db_name])
        res = self._cr.fetchone()

        return float(res[0]) if res else 0.0
