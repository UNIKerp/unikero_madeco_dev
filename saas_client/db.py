# flake8: noqa
from odoo.service import db
from odoo.service.db import _drop_conn, list_dbs, exp_db_exist, _initialize_db, DatabaseExists
from odoo import SUPERUSER_ID
from odoo.addons.server_mode.mode import get_mode
import logging
import os
import tempfile
import json
import shutil
from psycopg2.extensions import AsIs
from contextlib import closing
import psycopg2
import zipfile
import odoo
import odooly
from . import gcs

_logger = logging.getLogger(__name__)


# this patch could go on saas_provider but then saas provider should go on server_wide_modules
odooly._methods['db'] = odooly._methods['db'] + [
    'saas_create_database', 'saas_duplicate_database', 'saas_drop', 'saas_dump_db', 'saas_drop_pg_user',
    'saas_restore_db_from_bucket', 'saas_rename', 'saas_restore_db_from_odoo', 'saas_run_sql']


def _get_dsn(super_pg_user, super_pg_pass):
    return 'postgres://%s:%s@%s:%s/' % (
        super_pg_user,
        super_pg_pass,
        odoo.tools.config['db_host'],
        odoo.tools.config['db_port'],
    )


def _run_sql(sql, fetchall=False):
    if not get_mode():
        return 'No se puede correr run_sql en entornos de produccion'
    db_name = odoo.tools.config['db_name']
    if not db_name:
        return 'No db_name on odoo conf'
    db = odoo.sql_db.db_connect(db_name)
    with closing(db.cursor()) as cr:
        cr.autocommit(True)  # avoid transaction block
        _logger.info('Executing sql query')
        cr.execute(sql)
        if fetchall:
            return cr.fetchall()
        else:
            return True


def exp_saas_run_sql(sql, fetchall=False, do_not_raise=False):
    """This is used to run sql queries when upgrading a database.
    Usage eg. client.db.saas_run_sql(database.instance_password, sql, fetchall, do_not_raise)
    TODO sanitize sql
    """
    if do_not_raise:
        try:
            return _run_sql(sql, fetchall=fetchall)
        except Exception:
            return True
    else:
        return _run_sql(sql, fetchall=fetchall)


db.exp_saas_run_sql = exp_saas_run_sql


def _saas_create_user(pg_user, pg_pass, super_pg_user, super_pg_pass):
    """ Creates or update password of pg user """
    dsn = _get_dsn(super_pg_user, super_pg_pass)
    db = odoo.sql_db.db_connect(dsn + 'postgres', True)
    _logger.info('Creating / updating user %s', pg_user)
    with closing(db.cursor()) as cr:
        cr.autocommit(True)     # avoid transaction block
        try:
            cr.execute("SELECT 1 FROM pg_roles WHERE rolname=%s;", (pg_user,))
            if cr.fetchall():
                _logger.warning('User %s already exists. Updating password', (pg_user))
                cr.execute("ALTER USER %s WITH ENCRYPTED PASSWORD '%s';", (AsIs(pg_user), AsIs(pg_pass)))
            else:
                cr.execute("CREATE USER %s WITH ENCRYPTED PASSWORD '%s';", (AsIs(pg_user), AsIs(pg_pass)))
        except Exception as e:
            _logger.error('Could not create/update pg user, this is what we get %s', e)
        _logger.info('Creating / updating user successful')
    return True

def _saas_create_empty_database(pg_user, pg_pass, super_pg_user, super_pg_pass, db_name):
    """ Similar to odoo method but
    * creates new user if needed
    * create database with super user (because odoo pg user may not have rights
    """
    chosen_template = odoo.tools.config['db_template']

    # create user if needed
    if pg_user != super_pg_user:
        _saas_create_user(pg_user, pg_pass, super_pg_user, super_pg_pass)

    collate = "LC_COLLATE 'C'" if chosen_template == 'template0' else ""
    pg_cmd = """CREATE DATABASE "%s" ENCODING 'unicode' %s TEMPLATE "%s" OWNER %s"""
    pg_args = (AsIs(db_name), AsIs(collate), AsIs(chosen_template), AsIs(pg_user))

    dsn = _get_dsn(super_pg_user, super_pg_pass)
    db = odoo.sql_db.db_connect(dsn + 'postgres', True)
    with closing(db.cursor()) as cr:
        cr.autocommit(True)     # avoid transaction block
        cr.execute("SELECT datname FROM pg_database WHERE datname = %s", (db_name,))
        if cr.fetchall():
            raise DatabaseExists("database %r already exists!" % (db_name,))
        cr.execute(pg_cmd, pg_args)

    # create EXTENSION unaccent if enabled
    if odoo.tools.config['unaccent']:
        try:
            db = odoo.sql_db.db_connect(dsn + db_name, True)
            with closing(db.cursor()) as cr:
                cr.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
                cr.commit()
        except psycopg2.Error:
            pass

    return True


def exp_saas_create_database(pg_user, pg_pass, super_pg_user, super_pg_pass, db_name, demo, lang, user_password='admin', login='admin', country_code=None, phone=None):
    """ similar to odoo one but without check check_db_management_enabled """
    _logger.info('Create Saas database `%s`.', db_name)
    _saas_create_empty_database(pg_user, pg_pass, super_pg_user, super_pg_pass, db_name)
    _initialize_db(id, db_name, demo, lang, user_password, login, country_code, phone)

    return True


db.exp_saas_create_database = exp_saas_create_database


def exp_saas_duplicate_database(pg_user, pg_pass, old_pg_user, super_pg_user, super_pg_pass, db_original_name, db_name): 
    """ similar to odoo metod but:
    * duplicate with super user
    * allow to use parallel or hardlink for filestore duplication
    * creates new user if needed and change owner
    """
    _logger.info('Duplicate database `%s` to `%s`.', db_original_name, db_name)

    dsn = _get_dsn(super_pg_user, super_pg_pass)
    odoo.sql_db.close_db(dsn + db_original_name)
    db = odoo.sql_db.db_connect(dsn + 'postgres', True)
    with closing(db.cursor()) as cr:
        cr.autocommit(True)     # avoid transaction block
        _drop_conn(cr, db_original_name)
        cr.execute(
            """CREATE DATABASE "%s" ENCODING 'unicode' TEMPLATE "%s" """, (AsIs(db_name), AsIs(db_original_name)))

    registry = odoo.modules.registry.Registry.new(db_name)
    with registry.cursor() as cr:
        # if it's a copy of a database, force generation of a new dbuuid
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        env['ir.config_parameter'].init(force=True)

    from_fs = odoo.tools.config.filestore(db_original_name)
    to_fs = odoo.tools.config.filestore(db_name)
    if os.path.exists(from_fs) and not os.path.exists(to_fs):
        # EMPIEZA MODIFICACION
        # usamos copy del tree en parallel para tener mayor velocidad
        # TODO tal vez tmb se podría hacer en background usando algo
        # parecido a lo que usamos en infra, seria agregando adelante algo
        # como dtach -n `mktemp -u /tmp/dtach.XXXX`
        HARD_LINK = odoo.tools.config.get('filestore_copy_hard_link', False)
        N_THREADS = odoo.tools.config.get('filestore_operations_threads', 0)
        if HARD_LINK:
            _logger.info('Starting copy with hard link option')
            os.system('cp -al %s %s' % (from_fs, to_fs))
            _logger.info('Finish copy with hard link option')
        elif N_THREADS and N_THREADS != '0':
            _logger.info(
                'Starting parallel filestore copy with %s threads' % N_THREADS)
            copy_dir_tree = (
                r'cd %s && find . -type d -print0 '
                r'| parallel -j %s -0 "mkdir -p %s/{}" > /dev/null 2>&1' % (
                    from_fs, N_THREADS, to_fs))
            os.system(copy_dir_tree)

            copy_files = (
                r'cd %s && find . ! \( -type d \) -print0 '
                r'| parallel -j %s -0 "cp -f {} %s/{}"' % (
                    from_fs, N_THREADS, to_fs))
            os.system(copy_files)
            _logger.info('Parallel filestore copy finished')
        else:
            _logger.info('Starting default shutil copytree')
            shutil.copytree(from_fs, to_fs)
            _logger.info('Finish default shutil copytree')
        # TERMINA MODIFICACIOn

    # change ownership
    if pg_user != old_pg_user:
        _saas_create_user(pg_user, pg_pass, super_pg_user, super_pg_pass)
        db = odoo.sql_db.db_connect(dsn + db_name, True)
        with closing(db.cursor()) as cr:
            cr.autocommit(True)     # avoid transaction block
            cr.execute("""ALTER DATABASE "%s" OWNER TO %s""", (AsIs(db_name), AsIs(pg_user)))
            # no matter if we create database setting new owner of if we alter database owner, we still need to change
            # public schema ownership
            cr.execute("""REASSIGN OWNED BY %s TO %s""", (AsIs(old_pg_user), AsIs(pg_user)))
            # parche horrible porque al hacer reassign owner cambia el owner de la database y luego no podemos
            # borrar usuario. Si queremos ir por otro camino deberiamos dejar de usar el reassign owned y hacer
            # algo como https://gist.github.com/jirutka/afa3ce62b1430abf7572
            cr.execute("""ALTER DATABASE "%s" OWNER TO %s""", (AsIs(db_original_name), AsIs(old_pg_user)))

    return True


db.exp_saas_duplicate_database = exp_saas_duplicate_database


def exp_saas_drop_pg_user(super_pg_user, super_pg_pass, pg_user):
    """ new method to delete pg user when deleting stacks """
    _logger.info('Droping postgres user %s', pg_user)
    dsn = _get_dsn(super_pg_user, super_pg_pass)
    # we drop with super user because we can not drop with same user we want to drop
    db = odoo.sql_db.db_connect(dsn + 'postgres', True)
    with closing(db.cursor()) as cr:
        cr.autocommit(True)  # avoid transaction block
        try:
            cr.execute('DROP USER "%s"', (AsIs(pg_user),))
            _logger.info('User dropped successfully')
        except Exception as e:
            _logger.info('DROP USER: %s failed:\n%s', pg_user, e)
    return True


db.exp_saas_drop_pg_user = exp_saas_drop_pg_user


def exp_saas_drop(super_pg_user, super_pg_pass, db_name):
    """ similar to odoo method but:
    * we drop with super user so that we are able to class any possible connection to db
    * speed up filestore deletion by using parallel
    """
    if db_name not in list_dbs(True):
        return False
    odoo.modules.registry.Registry.delete(db_name)
    dsn = _get_dsn(super_pg_user, super_pg_pass)
    odoo.sql_db.close_db(dsn + db_name)
    db = odoo.sql_db.db_connect(dsn + 'postgres', True)
    with closing(db.cursor()) as cr:
        cr.autocommit(True)  # avoid transaction block
        _drop_conn(cr, db_name)

        try:
            cr.execute('DROP DATABASE "%s"', (AsIs(db_name),))
        except Exception as e:
            _logger.info('DROP DB: %s failed:\n%s', db_name, e)
            raise Exception("Couldn't drop database %s: %s" % (db_name, e))
        else:
            _logger.info('DROP DB: %s', db_name)

    fs = odoo.tools.config.filestore(db_name)
    if os.path.exists(fs):
        # EMPIEZA MODIFICACION
        N_THREADS = odoo.tools.config.get('filestore_operations_threads', 0)
        if N_THREADS and N_THREADS != '0':
            _logger.info(
                'Starting parallel filestore remove with %s threads' % (
                    N_THREADS))
            remove_dir = (
                'cd %s && find . -type d -print0 | parallel -j %s -0 '
                '"rm -rfv {}" > /dev/null 2>&1' % (fs, N_THREADS))
            os.system(remove_dir)
            os.system('rm -rfv %s' % fs)
            _logger.info('Parallel filestore remove finished')
        else:
            _logger.info('Starting default shutil rmtree')
            shutil.rmtree(fs)
            _logger.info('Finish default shutil rmtree')
        # TERMINA MODIFICACIOn
    return True


db.exp_saas_drop = exp_saas_drop


def exp_saas_restore_db_from_bucket(
        pg_user, pg_pass, super_pg_user, super_pg_pass, bucket_type, bucket_name, object_key,
        db_name, access_id=None, access_key=None, gcs_json=None):
    """ Restore db from bucket """
    _logger.info(
        "Starting restore process with data:\n"
        "* object_key: %s\n"
        "* bucket_name: %s\n"
        "* db_name: %s\n" % (object_key, bucket_name, db_name))

    args = {}

    with tempfile.NamedTemporaryFile() as file:
        if bucket_type == 'gcs':
            gcs.download_blob(bucket_name, object_key, destination_file=file.name, gcs_json=gcs_json)
        _logger.info("Restoring from file %s", file.name)
        # por ahora solo implementamos copy=False para que sirva
        # restaurando bds que tienen contrato. Habria que ver
        # si necesitamos implementar generar nuevo uuid
        # TODO
        _saas_restore_db(pg_user, pg_pass, super_pg_user, super_pg_pass, db_name, file.name, copy=False)
    _logger.info("Databse %s restored succesfully!" % db_name)
    return True


db.exp_saas_restore_db_from_bucket = exp_saas_restore_db_from_bucket


def _saas_restore_db(pg_user, pg_pass, super_pg_user, super_pg_pass, db, dump_file, copy=False):
    """ Similar to odoo restore_db but:
    * without 'check_db_management_enabled'
    * use super user
    * create user if needed
    * before getting cursos cancel any module to upgrade/install. Useful to speed up restore and also when restoring
    db from odoo upgrade
    """
    assert isinstance(db, str)
    if exp_db_exist(db):
        _logger.info('RESTORE DB: %s already exists', db)
        raise Exception("Database already exists")

    # como el container se levanto sin base y odoo intentó crear una base quedó el base en init y hace que ni bien se
    # restaure la base se ponga a actualizar base. Por eso borramos init. Es por esta linea:
    # https://github.com/odoo/odoo/blob/cb2862ad2a60ff4ce66c14e7af2548fdf6fc5961/odoo/cli/start.py#L64
    odoo.tools.config['init'] = {}

    _saas_create_empty_database(pg_user, pg_pass, super_pg_user, super_pg_pass, db)

    filestore_path = None
    with odoo.tools.osutil.tempdir() as dump_dir:
        if zipfile.is_zipfile(dump_file):
            # v8 format
            with zipfile.ZipFile(dump_file, 'r') as z:
                # only extract known members!
                filestore = [m for m in z.namelist() if m.startswith('filestore/')]
                z.extractall(dump_dir, ['dump.sql'] + filestore)

                if filestore:
                    filestore_path = os.path.join(dump_dir, 'filestore')

            pg_cmd = 'psql'
            pg_args = ['-q', '-f', os.path.join(dump_dir, 'dump.sql')]

        else:
            # <= 7.0 format (raw pg_dump output)
            pg_cmd = 'pg_restore'
            pg_args = ['--no-owner', dump_file]

        args = []
        args.append('--dbname=' + db)
        pg_args = args + pg_args

        if odoo.tools.exec_pg_command(pg_cmd, *pg_args):
            raise Exception("Couldn't restore database")

        # before getting cursos cancel any module upgrade / installation
        pg_cmd = 'psql'
        pg_args = ['-d', db, '-c', """
            UPDATE ir_module_module set state = 'installed' WHERE state in
            ('to upgrade', 'to remove'); UPDATE ir_module_module set state =
            'uninstalled' WHERE state = 'to install';"""]
        odoo.tools.exec_pg_command(pg_cmd, *pg_args)

        registry = odoo.modules.registry.Registry.new(db)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, SUPERUSER_ID, {})
            if copy:
                # if it's a copy of a database, force generation of a new dbuuid
                env['ir.config_parameter'].init(force=True)
            if filestore_path:
                filestore_dest = env['ir.attachment']._filestore()
                shutil.move(filestore_path, filestore_dest)

    _logger.info('RESTORE DB: %s', db)


def dump_db_manifest(cr):
    """ Same as odoo method but without check_db_management_enabled, needed for saas_dump_db"""
    pg_version = "%d.%d" % divmod(cr._obj.connection.server_version / 100, 100)
    cr.execute("SELECT name, latest_version FROM ir_module_module WHERE state = 'installed'")
    modules = dict(cr.fetchall())
    manifest = {
        'odoo_dump': '1',
        'db_name': cr.dbname,
        'version': odoo.release.version,
        'version_info': odoo.release.version_info,
        'major_version': odoo.release.major_version,
        'pg_version': pg_version,
        'modules': modules,
    }
    return manifest


def saas_dump_db(db_name, stream, backup_format='zip'):
    """ Similar to odoo method but:
    * if you request dump without filestore compress the dump (in some databases it makes a dfference)
    * do not require db manager enabled
    """
    _logger.info('DUMP DB: %s format %s', db_name, backup_format)

    cmd = ['pg_dump', '--no-owner']
    cmd.append(db_name)

    # if zip the method is equal to odoo dump_db but without check_db_management_enabled
    if backup_format == 'zip':
        with odoo.tools.osutil.tempdir() as dump_dir:
            filestore = odoo.tools.config.filestore(db_name)
            if os.path.exists(filestore):
                shutil.copytree(filestore, os.path.join(dump_dir, 'filestore'))
            with open(os.path.join(dump_dir, 'manifest.json'), 'w') as fh:
                db = odoo.sql_db.db_connect(db_name)
                with db.cursor() as cr:
                    json.dump(dump_db_manifest(cr), fh, indent=4)
            cmd.insert(-1, '--file=' + os.path.join(dump_dir, 'dump.sql'))
            odoo.tools.exec_pg_command(*cmd)
            if stream:
                odoo.tools.osutil.zip_dir(dump_dir, stream, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql')
            else:
                t=tempfile.TemporaryFile()
                odoo.tools.osutil.zip_dir(dump_dir, t, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql')
                t.seek(0)
                return t
    else:
        # this is different to odoo method, we compress it in a zip as if it has filestore
        # cmd.insert(-1, '--format=c')
        # stdin, stdout = odoo.tools.exec_pg_command_pipe(*cmd)
        # if stream:
        #     shutil.copyfileobj(stdout, stream)
        # else:
        #     return stdout

        with odoo.tools.osutil.tempdir() as dump_dir:
            cmd.insert(-1, '--format=c')
            cmd.insert(-1, '--file=' + os.path.join(dump_dir, 'dump.sql'))
            odoo.tools.exec_pg_command(*cmd)
            if stream:
                odoo.tools.osutil.zip_dir(dump_dir, stream, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql')
            else:
                t=tempfile.TemporaryFile()
                odoo.tools.osutil.zip_dir(dump_dir, t, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql')
                t.seek(0)
                return t


db.saas_dump_db = saas_dump_db


def exp_saas_rename(pg_user, pg_pass, old_pg_user, super_pg_user, super_pg_pass, old_name, new_name):
    """ similar to odoo method but:
    * create new user if needed
    """
    odoo.modules.registry.Registry.delete(old_name)

    # we rename with super user to be able to close any possible connection and also because create right is needed
    dsn = _get_dsn(super_pg_user, super_pg_pass)
    odoo.sql_db.close_db(dsn + old_name)
    db = odoo.sql_db.db_connect(dsn + 'postgres', True)
    with closing(db.cursor()) as cr:
        cr.autocommit(True)     # avoid transaction block
        _drop_conn(cr, old_name)
        try:
            cr.execute('ALTER DATABASE "%s" RENAME TO "%s"', (AsIs(old_name), AsIs(new_name)))
            _logger.info('RENAME DB: %s -> %s', old_name, new_name)
        except Exception as e:
            _logger.info('RENAME DB: %s -> %s failed:\n%s', old_name, new_name, e)
            raise Exception("Couldn't rename database %s to %s: %s" % (old_name, new_name, e))

    if pg_user != old_pg_user:
        _saas_create_user(pg_user, pg_pass, super_pg_user, super_pg_pass)
        # new database is owned by new user but public schema not
        db = odoo.sql_db.db_connect(dsn + new_name, True)
        with closing(db.cursor()) as cr:
            cr.autocommit(True)     # avoid transaction block
            # el reassign tmb cambia el owner de la database
            cr.execute("""REASSIGN OWNED BY %s TO %s""", (AsIs(old_pg_user), AsIs(pg_user)))

    old_fs = odoo.tools.config.filestore(old_name)
    new_fs = odoo.tools.config.filestore(new_name)
    if os.path.exists(old_fs) and not os.path.exists(new_fs):
        shutil.move(old_fs, new_fs)
    return True


db.exp_saas_rename = exp_saas_rename


def new_list_dbs(force=False):
    """ Modify list_dbs so that if we can't connect to odoo we still leave odoo wake up so that we can connect remotely
    """
    db = odoo.sql_db.db_connect('postgres')
    try:
        cr = db.cursor()
        cr.close()
    except:
        _logger.info('Could not connect to postgres. May be you are creating stack and pg user is not created yet')
        return []
    else:
        return list_dbs(force=force)


db.list_dbs = new_list_dbs


##################
# Upgrades methods
##################


def exp_saas_restore_db_from_odoo(
        pg_user, pg_pass, super_pg_user, super_pg_pass, odoo_request_nbr, odoo_request_key,
        db_name, source_db_filestore=None):
    """ Restore db from odoo upgrade """

    _logger.info(
        "Starting restore from odoo with data:\n"
        "* odoo_request_nbr: %s\n"
        "* db_name: %s\n" % (odoo_request_nbr, db_name))

    url = (
        "https://upgrade.odoo.com/database/eu1/%s/%s/upgraded/archive") % (
            odoo_request_nbr, odoo_request_key)
    _logger.info("Downloading file from %s" % url)
    file_name = "/tmp/%s.zip" % db_name
    os.system("wget --continue -O %s %s" % (file_name, url))

    try:
        _logger.info("Restoring from %s" % file_name)
        _saas_restore_db(pg_user, pg_pass, super_pg_user, super_pg_pass, db_name, file_name, copy=False)
        _logger.info("Restore finished")
    except Exception as e:
        # TODO ver si odoo arreglo esto si el error contiene "error 1" y
        # no es un zip, entonces es un error de odoo pero que no es error
        # en realidad
        raise Exception('Unable to restore bd %s, this is what we get: \n %s' % (db_name, e))

    # copiamos el filestore de la base de versión anterior
    if source_db_filestore:
        _logger.info(
            "Copy source filestore from %s" % (source_db_filestore))
        source_filestore = odoo.tools.config.filestore(source_db_filestore)
        filestore = odoo.tools.config.filestore(db_name)
        from distutils.dir_util import copy_tree
        copy_tree(source_filestore, filestore)
        # no nos funciona del todo bien, por ahora seguimos con el copytree
        # para que sea mas rapido lo hacemos por enlaces simbolicos y con
        # -n para que no sobre-escriba
        # os.system('cp -aln %s %s' % (source_filestore, filestore))
        _logger.info("Copy filestore finished")
    _logger.info("Restore from odoo finish successfully!")

    return True


db.exp_saas_restore_db_from_odoo = exp_saas_restore_db_from_odoo
