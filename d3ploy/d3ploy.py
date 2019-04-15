#!/usr/bin/env python

# Notification Center code borrowed from
# https://github.com/maranas/pyNotificationCenter/blob/master/pyNotificationCenter.py

import argparse
import contextlib
import fnmatch
import hashlib
import json
import mimetypes
import multiprocessing
import os
import re
import signal
import sys
import threading
import time
import urllib
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor

import boto3
import botocore
import pathspec
import progressbar

with warnings.catch_warnings():
    try:
        import pync
    except Exception:  # pragma: no cover, sadly this module raises a base Exception when imported on unsupported platforms
        pync = False

VERSION = '3.0.0-beta'
VALID_ACLS = [
    'private',
    'public-read',
    'public-read-write',
    'authenticated-read',
]
DEFAULT_COLOR = '\033[0;0m'
ERROR_COLOR = '\033[31m'
ALERT_COLOR = '\033[33m'
OK_COLOR = '\033[92m'
QUIET = False

# From https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types#Important_MIME_types_for_Web_developers
MIMETYPES = {
    'application/ogg': ['.ogg'],
    'audio/wave': ['.wav'],
    'font/otf': ['.otf'],
    'font/ttf': ['.ttf'],
    'font/woff': ['.woff'],
    'font/woff2': ['.woff2'],
    'image/gif': ['.gif'],
    'image/jpeg': ['.jpeg', '.jpg'],
    'image/png': ['.png'],
    'image/svg+xml': ['.svg'],
    'image/webp': ['.webp'],
    'image/x-icon': ['.ico'],
    'text/css': ['.css'],
    'text/html': ['.html', '.htm'],
    'text/javascript': ['.js'],
    'video/webm': ['.webm'],
}

for mimetype in MIMETYPES:
    for extension in MIMETYPES[mimetype]:
        mimetypes.add_type(
            mimetype,
            extension,
        )


def alert(
    text,
    error_code=None,
    color=None,
):
    buffer = sys.stderr if error_code else sys.stdout
    if not QUIET:
        buffer.write(
            '{}{}{}\n'.format(
                color or (
                    ERROR_COLOR if error_code else DEFAULT_COLOR),
                text,
                DEFAULT_COLOR,
            )
        )
        buffer.flush()
    if error_code is not None:
        sys.exit(error_code)


killswitch = threading.Event()


def progress_setup(
    label='Uploading: ',
    num_files=0,
    marker_color=DEFAULT_COLOR,
):
    if progressbar and not QUIET:
        bar = progressbar.ProgressBar(widgets=[marker_color, label, progressbar.Percentage(
        ), ' ', progressbar.Bar(), ' ', progressbar.ETA(), DEFAULT_COLOR], max_value=num_files)
        bar.start()
    else:
        bar = None
    return bar


def progress_update(
    bar,
    count,
):
    if bar and not QUIET:
        bar.update(
            bar.value + count
        )


def bail(
    *args,
    **kwargs
):  # pragma: no cover
    killswitch.set()
    try:
        bar.widgets[0] = ERROR_COLOR
        bar.finished = True
        progress_update(bar, 0)
        alert('')
    except NameError:
        pass
    alert('\nExiting...', os.EX_OK, ALERT_COLOR)


signal.signal(signal.SIGINT, bail)


def check_for_updates(
    check_file_path='~/.d3ploy-update-check',
    this_version=VERSION
):
    update_available = None
    try:
        from pkg_resources import parse_version
    except ImportError:  # pragma: no cover
        return None
    PYPI_URL = 'https://pypi.org/pypi/d3ploy/json'
    CHECK_FILE = os.path.expanduser(check_file_path)
    if not os.path.exists(CHECK_FILE):
        try:
            with open(CHECK_FILE, 'w') as _f:
                pass
        except IOError:  # pragma: no cover
            pass
    try:
        with open(CHECK_FILE, 'r') as _f:
            last_checked = int(_f.read().strip())
    except ValueError:
        last_checked = 0
    now = int(time.time())
    if now - last_checked > 86400:
        if os.environ.get('D3PLOY_DEBUG'):
            print('checking for update')
        # it has been a day since the last update check
        try:
            with contextlib.closing(urllib.request.urlopen(PYPI_URL)) as pypi_response:
                pypi_data = json.load(pypi_response)
                pypi_version = parse_version(
                    pypi_data.get('info', {}).get('version')
                )
                if pypi_version > parse_version(this_version):
                    alert(
                        'There has been an update for d3ploy. Version {} is now available.\nPlease see https://github.com/dryan/d3ploy or run `pip install --upgrade d3ploy`.'.format(
                            pypi_version,
                        ),
                        color=ALERT_COLOR,
                    )
                    update_available = True
                else:
                    update_available = False
        except ConnectionResetError:  # pragma: no cover
            update_available = False  # if pypi fails, assume we can't get an update anyway
        except Exception as e:  # pragma: no cover
            if os.environ.get('D3PLOY_DEBUG'):
                raise e
        with open(CHECK_FILE, 'w') as check_file:
            check_file.write(str(now))
            check_file.flush()
            check_file.close()
    return update_available


def notify(
    env,
    text,
    error_code=None,
    color=None,
):  # pragma: no cover
    if QUIET:
        return
    alert(text, error_code, color)
    if pync:
        pync.notify(
            title='d3ploy',
            subtitle=env,
            message=text,
            sound=os.environ.get(
                'D3PLOY_NC_SOUND'
            ),
            group=os.getpid(),
        )
        return True


# this is where the actual upload happens, called by sync_files
def upload_file(
    file_name,
    bucket_name,
    s3,
    bucket_path,
    prefix_regex,
    acl='public-read',
    bar=None,
    force=False,
    dry_run=False,
    charset=None,
    caches={},
):
    if killswitch.is_set():
        return (file_name, 0)
    updated = 0
    key_name = '/'.join(
        [
            bucket_path.rstrip('/'),
            prefix_regex.sub('', file_name).lstrip('/')
        ]
    )
    s3_obj = s3.Object(bucket_name, key_name)
    try:
        s3_obj.load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            s3_obj = None
        else:  # pragma: no cover
            raise e
    local_md5 = hashlib.md5()
    with open(file_name, 'rb') as local_file:
        for chunk in iter(lambda: local_file.read(4096), b''):
            local_md5.update(chunk)
    local_md5 = local_md5.hexdigest()
    mimetype = mimetypes.guess_type(file_name)

    if s3_obj is None or force or not s3_obj.metadata.get('d3ploy-hash') == local_md5:
        with open(file_name, 'rb') as local_file:
            updated += 1
            if bar:  # pragma: no cover
                progress_update(bar, +1)
            else:
                alert(
                    'Copying {} to {}/{}'.format(
                        file_name,
                        bucket_name,
                        key_name.lstrip('/'),
                    )
                )
            if dry_run:
                return (key_name.lstrip('/'), updated)
            extra_args = {
                'ACL': acl,
                'Metadata': {
                    'd3ploy-hash': local_md5,
                },
            }
            if charset and mimetype[0] and mimetype[0].split('/')[0] == 'text':
                extra_args['ContentType'] = '{};charset={}'.format(
                    mimetype[0],
                    charset,
                )
            elif mimetype[0]:
                extra_args['ContentType'] = mimetype[0]
            if mimetype[0] in caches.keys():
                extra_args['CacheControl'] = 'max-age={}, public'.format(
                    caches.get(mimetype[0])
                )
            s3.meta.client.upload_fileobj(
                local_file,
                bucket_name,
                key_name,
                ExtraArgs=extra_args,
            )
    else:
        if(bar):  # pragma: no cover
            progress_update(bar, +1)
    return (key_name.lstrip('/'), updated)


def get_confirmation(
    message,
):  # pragma: no cover
    confirm = input(
        '{} [yN]: '.format(message),
    )

    return confirm.lower() in ['y', 'yes']


# this where the actual removal happens, called by sync_files
def delete_file(
    key_name,
    bucket_name,
    s3,
    needs_confirmation=False,
    bar=None,
    dry_run=False
):
    if killswitch.is_set():
        return 0
    deleted = 0
    if needs_confirmation:
        confirmed = get_confirmation(
            '{}Remove {}/{}'.format(
                '\n' if bar else '',
                bucket_name,
                key_name.lstrip('/'))
        )
    else:
        confirmed = True
    if confirmed:
        if bar:
            progress_update(bar, +1)
        else:
            alert(
                'Deleting {}/{}'.format(
                    bucket_name,
                    key_name.lstrip('/')
                )
            )
        deleted += 1
        if not dry_run:
            s3.Object(
                bucket_name,
                key_name,
            ).delete()
    else:
        if bar:
            progress_update(bar, +1)
        alert(
            '{}Skipping removal of {}/{}'.format(
                '\n' if bar and not needs_confirmation else '',
                bucket_name,
                key_name.lstrip('/'),
            )
        )
    return deleted


def determine_files_to_sync(
    local_path,
    excludes=[],
    gitignore=False,
):
    prefix_regex = re.compile(r'^{}'.format(local_path))
    if isinstance(excludes, str):
        excludes = [excludes]
    gitignore_patterns = list(
        map(
            pathspec.patterns.GitWildMatchPattern,
            excludes,
        )
    )
    svc_directories = ['.git', '.svn']
    if gitignore:
        gitignores = []
        base_dir = os.getcwd()
        if os.path.exists('.gitignore'):
            gitignores.append('.gitignore')
        for root, dir_names, file_names in os.walk(local_path):
            for dir_name in dir_names:
                if dir_name in svc_directories:
                    continue
                dir_name = os.path.join(root, dir_name)
                gitignore_path = os.path.join(dir_name, '.gitignore')
                if os.path.exists(gitignore_path):
                    gitignores.append(gitignore_path)
            for file_name in file_names:
                if file_name == '.gitignore':
                    gitignore_path = os.path.join(root, file_name)
                    gitignores.append(gitignore_path)
        for gitignore_file in gitignores:
            with open(gitignore_file) as f:
                spec = pathspec.PathSpec.from_lines('gitwildmatch', f)
                gitignore_patterns += [x for x in spec.patterns if x.regex]
        if not gitignores:
            alert(
                '--gitignore option set, but no .gitignore files were found',
                color=ALERT_COLOR,
            )
    gitignore_spec = pathspec.PathSpec(gitignore_patterns)

    files = []
    if os.path.isdir(local_path):
        for root, dir_names, file_names in os.walk(local_path):
            for file_name in file_names:
                file_name = os.path.join(root, file_name)
                if not gitignore_spec.match_file(file_name):
                    files.append(file_name)
            for svc_directory in svc_directories:
                if svc_directory in dir_names:
                    dir_names.remove(svc_directory)
    elif os.path.isfile(local_path) or os.path.islink(local_path):
        if not gitignore_spec.match_file(local_path):
            files.append(local_path)
    return files


def invalidate_cloudfront(
    cloudfront_id,
    env,
    dry_run=False,
):
    output = []
    if not isinstance(cloudfront_id, list):
        cloudfront_id = [cloudfront_id]
    for cf_id in cloudfront_id:
        if dry_run:
            notify(
                env,
                'CloudFront distribution {} invalidation would be requested'.format(
                    cf_id,
                ),
                color=OK_COLOR,
            )
        else:
            cloudfront = boto3.client('cloudfront')
            # we don't specify the individual paths because that's more costly monetarily speaking
            response = cloudfront.create_invalidation(
                DistributionId=cf_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': 1,
                        'Items': [
                            '/*',
                        ],
                    },
                    'CallerReference': uuid.uuid4().hex,
                },
            )
            notify(
                env,
                'CloudFront distribution {} invalidation requested'.format(
                    cf_id,
                ),
                color=OK_COLOR,
            )
            output.append(response.get('Invalidation', {}).get('Id'))
    return [x for x in output if x]


def sync_files(
    env,
    bucket_name=None,
    local_path='.',
    bucket_path='/',
    excludes=[],
    acl='public-read',
    force=False,
    dry_run=False,
    charset=False,
    gitignore=False,
    processes=1,
    delete=False,
    confirm=False,
    cloudfront_id=[],
    caches={},
):
    alert(
        'Using settings for "{}" environment'.format(
            env,
        ),
    )

    if not bucket_name:
        alert(
            'A bucket to upload to was not specified for "{}" environment'.format(
                env
            ),
            os.EX_NOINPUT,
        )

    s3 = boto3.resource('s3')

    # test the bucket connection
    try:
        s3.meta.client.head_bucket(
            Bucket=bucket_name,
        )
        bucket = s3.Bucket(bucket_name)
    except botocore.exceptions.ClientError as e:  # pragma: no cover
        if e.response['Error']['Code'] == '403':
            alert(
                'Bucket "{}" could not be retrieved with the specified credentials. Tried Access Key ID {}'.format(
                    bucket_name,
                    boto3.Session().get_credentials().access_key,
                ),
                os.EX_NOUSER,
            )
        else:
            raise e

    prefix_regex = re.compile(r'^{}'.format(local_path))
    files = determine_files_to_sync(
        local_path,
        excludes,
        gitignore=gitignore,
    )
    deleted = 0
    bar = progress_setup(
        'Updating {}: '.format(env),
        len(files),
        OK_COLOR,
    )

    key_names = []
    updated = 0
    with ThreadPoolExecutor(max_workers=processes) as executor:
        for fn in files:
            job = executor.submit(
                upload_file,
                *(
                    fn,
                    bucket_name,
                    s3,
                    bucket_path,
                    prefix_regex,
                ),
                **{
                    'acl': acl,
                    'bar': bar,
                    'force': force,
                    'dry_run': dry_run,
                    'charset': charset,
                    'caches': caches,
                }
            )
            try:
                key_names.append(job.result())
            except KeyboardInterrupt:  # pragma: no cover
                killswitch.set()
        executor.shutdown(wait=True)

    if bar and not killswitch.is_set():
        bar.finish()

    updated = sum([i[1] for i in key_names])
    key_names = [i[0] for i in key_names if i[0]]

    if delete and not killswitch.is_set():
        to_remove = [
            key.key for key in bucket.objects.filter(Prefix=bucket_path.lstrip('/')) if key.key not in key_names
        ]
        if len(to_remove):
            bar = progress_setup(
                'Cleaning {}: '.format(
                    env,
                ),
                len(to_remove),
                ALERT_COLOR,
            )
            deleted = 0
            with ThreadPoolExecutor(max_workers=processes) as executor:
                for kn in to_remove:
                    job = executor.submit(
                        delete_file,
                        *(
                            kn,
                            bucket_name,
                            s3,
                        ),
                        **{
                            'needs_confirmation': confirm,
                            'bar': bar,
                            'dry_run': dry_run,
                        },
                    )
                    try:
                        deleted += job.result()
                    except KeyboardInterrupt:  # pragma: no cover
                        killswitch.set()
                executor.shutdown(wait=True)

            if bar and not killswitch.is_set():
                bar.finish()

    verb = 'would be' if dry_run else 'were'
    outcome = {
        'uploaded': updated,
        'deleted': deleted,
        'invalidated': 0,
    }
    alert('')
    notify(
        env,
        '{:d} file{} {} updated'.format(
            updated,
            '' if updated == 1 else 's',
            'was' if verb == 'were' and updated == 1 else verb,
        ),
        color=OK_COLOR,
    )
    if delete:
        notify(
            env,
            '{:d} file{} {} removed'.format(
                deleted,
                '' if deleted == 1 else 's',
                'was' if verb == 'were' and deleted == 1 else verb,
            ),
            color=ALERT_COLOR,
        )
    if cloudfront_id:
        invalidations = invalidate_cloudfront(
            cloudfront_id,
            env,
            dry_run=dry_run,
        )
        outcome['invalidated'] = len(invalidations)
    return outcome


def processes_int(x):
    x = int(x)
    if x <= 0 or x > 50:
        raise argparse.ArgumentTypeError(
            'An integer between 0 and 50 is required'
        )
    return x


def cli():
    global QUIET
    if '-v' in sys.argv or '--version' in sys.argv:
        # do this here before any of the config checks are run
        alert('d3ploy {}'.format(VERSION), os.EX_OK, DEFAULT_COLOR)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'environment',
        help='Which environment to deploy to',
        nargs='*',
        type=str,
        default=['default'],
    )
    parser.add_argument(
        '--bucket-name',
        help='The bucket to upload files to',
        type=str,
    )
    parser.add_argument(
        '--local-path',
        help='The local folder to upload files from',
        type=str,
    )
    parser.add_argument(
        '--bucket-path',
        help='The remote folder to upload files to',
        type=str,
    )
    parser.add_argument(
        '--exclude',
        help='A filename or pattern to ignore. Can be set multiple times.',
        action='append',
        default=[],
    )
    parser.add_argument(
        '--acl',
        help='The ACL to apply to uploaded files.',
        type=str,
        default='public-read',
        choices=VALID_ACLS,
    )
    parser.add_argument(
        '-f',
        '--force',
        help='Upload all files whether they are currently up to date on S3 or not',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '-n',
        '--dry-run',
        help='Show which files would be updated without uploading to S3',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '--charset',
        help='The charset header to add to text files',
        default=False,
    )
    parser.add_argument(
        '--gitignore',
        help='Add .gitignore rules to the exclude list',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '-p',
        '--processes',
        help='The number of concurrent processes to use for uploading/deleting.',
        type=processes_int,
        default=10,
    )
    parser.add_argument(
        '--delete',
        help='Remove orphaned files from S3',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '--confirm',
        help='Confirm each file before deleting. Only works when --delete is set.',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '--cloudfront-id',
        help='Specify one or more CloudFront distribution IDs to invalidate after updating.',
        action='append',
        default=[],
    )
    parser.add_argument(
        '--all',
        help='Upload to all environments',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '-v',
        '--version',
        help='Print the script version and exit',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '-c',
        '--config',
        help='path to config file. Defaults to .d3ploy.json in current directory.',
        type=str,
        default='.d3ploy.json',
    )
    parser.add_argument(
        '-q',
        '--quiet',
        help='Suppress all output. Useful for automated usage.',
        action='store_true',
        default=False,
    )
    args = parser.parse_args()
    if args.quiet:
        QUIET = True

    if args.processes < 1:
        alert(
            'processes must be 1 or more',
            os.EX_CONFIG,
        )

    if os.path.exists('deploy.json'):
        alert(
            'It looks like you have an old version of deploy.json in your project. Please http://dryan.github.io/d3ploy#migrate for information on upgrading.',
            os.EX_CONFIG,
        )

    # load the config file
    config = {}
    if os.path.exists(args.config):
        with open(args.config) as f:
            config = json.load(f)
    else:
        alert(
            'Config file is missing. Looked for {}. See http://dryan.github.io/d3ploy for more information.'.format(
                args.config),
            os.EX_NOINPUT,
        )

    environments = [
        '{}'.format(item) for item in config.get('environments', {}).keys()
    ]
    defaults = config.get('defaults', {})

    # Check if no environments are configured in the file
    if not environments:
        alert(
            'No environments found in config file: {}'.format(args.config),
            os.EX_NOINPUT
        )

    if args.all:
        args.environment = environments

    # check if environment actually exists in the config file
    invalid_environments = []
    for env in args.environment:
        if env not in environments:
            invalid_environments.append(env)
    if invalid_environments:
        alert(
            'environment{} {} not found in config. Choose from "{}"'.format(
                '' if len(invalid_environments) == 1 else 's',
                ', '.join(invalid_environments),
                ', '.join(environments),
            ),
            os.EX_NOINPUT,
        )

    to_deploy = environments if args.all else args.environment

    for environ in to_deploy:
        alert(
            'Uploading environment {:d} of {:d}'.format(
                to_deploy.index(environ) + 1,
                len(to_deploy),
            )
        )
        environ_config = config['environments'][environ]
        if not environ_config.get('excludes', False):
            environ_config['excludes'] = []
        if not defaults.get('excludes', False):
            defaults['excludes'] = []
        excludes = []
        if args.exclude:
            excludes = args.exclude
        else:
            excludes = environ_config.get(
                'exclude', []) + defaults.get('exclude', [])
        excludes.append(args.config)
        sync_files(
            environ,
            bucket_name=args.bucket_name or environ_config.get(
                'bucket_name') or defaults.get('bucket_name'),
            local_path=args.local_path or environ_config.get(
                'local_path') or defaults.get('local_path'),
            bucket_path=args.bucket_path or environ_config.get(
                'bucket_path') or defaults.get('bucket_path'),
            excludes=excludes,
            acl=args.acl or environ_config.get('acl') or defaults.get('acl'),
            force=args.force or environ_config.get(
                'force') or defaults.get('force'),
            dry_run=args.dry_run,
            charset=args.charset or environ_config.get(
                'charset') or defaults.get('charset'),
            gitignore=args.gitignore or environ_config.get(
                'gitignore') or defaults.get('gitignore'),
            processes=args.processes,
            delete=args.delete or environ_config.get(
                'delete') or defaults.get('delete'),
            confirm=args.confirm,
            cloudfront_id=args.cloudfront_id or environ_config.get(
                'cloudfront_id') or defaults.get('cloudfront_id') or [],
            caches=environ_config.get(
                'caches', {}) or defaults.get('caches', {}),
        )


if __name__ == '__main__':  # pragma: no cover
    try:
        check_for_updates()
    except Exception as e:
        if os.environ.get('D3PLOY_DEBUG') == 'True':
            raise e
    cli()
