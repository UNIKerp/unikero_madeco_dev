import logging
_logger = logging.getLogger(__name__)

try:
    import boto
    from boto.s3.key import Key
except Exception:
    boto = None
    Key = None
    _logger.debug(
        'SAAS Sysadmin Bacnkup Agent S3 Requires the python library Boto which'
        ' is not found on your installation')

Key = Key
boto = boto


def get_conn(**args):
    # bucket = s3_data.get('bucket')
    # access_id = args.get('access_id')
    # access_key = args.get('access_key')
    return boto.connect_s3(**args)


def get_bucket(bucket_name, **args):
    conn = get_conn(**args)
    return conn.get_bucket(bucket_name)


# def list_files(bucket_name, prefix=None, **args):
#     bucket = get_bucket(bucket_name, **args)
#     return bucket.list(prefix)


def download_object(
        bucket_name, object_key, destination_file=None, **args):
    """
    Download a backup from s3 with object_key to the destination_file
    If not destination file is set, we donwload it to /tmp wih same
    object key name
    """
    if not destination_file:
        destination_file = '/tmp/%s' % object_key
    bucket = get_bucket(bucket_name, **args)
    key = bucket.get_key(object_key)
    key.get_contents_to_filename(destination_file)
    return True
