from tempfile import NamedTemporaryFile
from ast import literal_eval
import json
import logging
_logger = logging.getLogger(__name__)

try:
    from google.cloud import storage
    from google.auth import compute_engine
except Exception:
    storage = None
    compute_engine = None
    _logger.debug(
        'SAAS Sysadmin Backup Agent Requires Google CLoud Storage python '
        'library which is not found on your installation')


def get_storage_client(gcs_json=None):
    if gcs_json:
        sa_json = NamedTemporaryFile(delete=False)
        sa_json.write(json.dumps(literal_eval(gcs_json)).encode('utf-8'))
        sa_json.close()
        storage_client = storage.Client.from_service_account_json(sa_json.name)
    else:
        credentials = compute_engine.Credentials()
        storage_client = storage.Client(credentials=credentials)
        # credentials=credentials, project=project)
    return storage_client


def get_bucket(bucket_name, gcs_json=None):
    storage_client = get_storage_client(gcs_json=gcs_json)
    return storage_client.get_bucket(bucket_name)


# def list_files(bucket_name, prefix=None, **args):
#     bucket = get_bucket(bucket_name, **args)
#     return bucket.list_blobs(prefix=prefix)


def download_blob(
        bucket_name, blob_key, destination_file=None, gcs_json=None):
    """
    Download a backup from google storage with blob_key to the dest file
    If not destination file is set, we donwload it to /tmp wih same
    object key name
    """
    if not destination_file:
        destination_file = '/tmp/%s' % blob_key
    bucket = get_bucket(bucket_name, gcs_json=gcs_json)
    blob = bucket.get_blob(blob_key)
    blob.download_to_filename(destination_file)
    return True
