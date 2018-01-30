#!/usr/bin/env python

# Notification Center code borrowed from
# https://github.com/maranas/pyNotificationCenter/blob/master/pyNotificationCenter.py

import argparse
import base64
import ConfigParser
import gzip
import hashlib
import json
import mimetypes
import os
import Queue
import re
import signal
import sys
import threading
import time
import urllib
# disable import warnings
import warnings
import zipfile
from xml.dom import minidom

from boto.s3.connection import OrdinaryCallingFormat

VERSION = '2.2.3'

warnings.filterwarnings('ignore')

# add woff2 mimetype since it's not supported by default
mimetypes.add_type('application/font-woff2', '.woff2')

DEFAULT_COLOR = '\033[0;0m'
ERROR_COLOR = '\033[31m'
ALERT_COLOR = '\033[33m'
OK_COLOR = '\033[92m'

QUIET = False

progressbar = None

killswitch = threading.Event()

try:
    import progressbar
except ImportError:
    pass


def alert(text, error_code=None, color=None):
    if error_code is not None:
        if not QUIET:
            sys.stderr.write('%s%s%s\n' %
                             (color or ERROR_COLOR, text, DEFAULT_COLOR))
            sys.stderr.flush()
        sys.exit(error_code)
    else:
        if not QUIET:
            sys.stdout.write('%s%s%s\n' %
                             (color or DEFAULT_COLOR, text, DEFAULT_COLOR))
            sys.stdout.flush()


def progress_setup(label='Uploading: ', num_files=0, marker_color=DEFAULT_COLOR):
    global bar
    if progressbar and not QUIET:
        bar = progressbar.ProgressBar(widgets=[marker_color, label, progressbar.Percentage(
        ), ' ', progressbar.Bar(), ' ', progressbar.ETA(), DEFAULT_COLOR], maxval=num_files)
        if not hasattr(bar, 'currval'):
            bar = None  # this isn't the version we're expecting
        else:
            bar.start()
    else:
        bar = None


def progress_update(bar, count):
    if bar and not QUIET:
        bar.update(count)


def bail(*args, **kwargs):
    killswitch.set()
    try:
        bar.widgets[0] = ERROR_COLOR
        bar.finished = True
        progress_update(bar, bar.currval)
        alert("")
    except NameError:
        pass
    try:
        pool.close()
        pool.terminate()
        pool.join()
    except Exception:
        pass
    alert('\nExiting...', os.EX_OK, ALERT_COLOR)


signal.signal(signal.SIGINT, bail)

# check for updates
PYPI_URL = 'https://pypi.python.org/pypi?:action=doap&name=d3ploy'
CHECK_FILE = os.path.expanduser('~/.d3ploy-update-check')
if not os.path.exists(CHECK_FILE):
    try:
        open(CHECK_FILE, 'w')
    except IOError:
        pass
try:
    last_checked = int(open(CHECK_FILE, 'r').read().strip())
except ValueError:
    last_checked = 0
now = int(time.time())
if now - last_checked > 86400:
    # it has been a day since the last update check
    try:
        pypi_data = minidom.parse(urllib.urlopen(PYPI_URL))
        pypi_version = pypi_data.getElementsByTagName('revision')[
            0].firstChild.data
        if pypi_version > VERSION:
            alert('There has been an update for d3ploy. Version %s is now available.\nPlease see https://github.com/dryan/d3ploy or run `pip install --upgrade d3ploy`.' %
                  pypi_version, color=ALERT_COLOR)
    except Exception:
        pass
    check_file = open(CHECK_FILE, 'w')
    check_file.write(str(now))
    check_file.flush()
    check_file.close()

try:
    import boto
except ImportError:
    alert("Please install boto. `pip install boto`", os.EX_UNAVAILABLE)


try:
    import Foundation
    import objc
    notifications = True
except ImportError:
    notifications = False

if notifications:
    try:
        NSUserNotification = objc.lookUpClass('NSUserNotification')
        NSUserNotificationCenter = objc.lookUpClass('NSUserNotificationCenter')
    except objc.nosuchclass_error:
        notifications = False


def notify(env, text, error_code=None, color=None):
    if QUIET:
        return
    alert(text, error_code, color)
    if notifications:
        notification = NSUserNotification.alloc().init()
        notification.setTitle_('d3ploy')
        notification.setSubtitle_(env)
        notification.setInformativeText_(text)
        notification.setUserInfo_({})
        if os.environ.get('D3PLOY_NC_SOUND'):
            notification.setSoundName_("NSUserNotificationDefaultSoundName")
        notification.setDeliveryDate_(
            Foundation.NSDate.dateWithTimeInterval_sinceDate_(0, Foundation.NSDate.date()))
        NSUserNotificationCenter.defaultUserNotificationCenter(
        ).scheduleNotification_(notification)


if '-v' in sys.argv or '--version' in sys.argv:
    # do this here before any of the config checks are run
    alert('d3ploy %s' % VERSION, os.EX_OK, DEFAULT_COLOR)


valid_acls = ["private", "public-read",
              "public-read-write", "authenticated-read"]

parser = argparse.ArgumentParser()
parser.add_argument('environment', help="Which environment to deploy to",
                    nargs="?", type=str, default="default")
parser.add_argument('-a', '--access-key', help="AWS Access Key ID", type=str)
parser.add_argument('-s', '--access-secret',
                    help="AWS Access Key Secret", type=str)
parser.add_argument('-f', '--force', help="Upload all files whether they are currently up to date on S3 or not",
                    action="store_true", default=False)
parser.add_argument('--delete', help="Remove orphaned files from S3",
                    action="store_true", default=False)
parser.add_argument('--all', help="Upload to all environments",
                    action="store_true", default=False)
parser.add_argument('-n', '--dry-run', help="Show which files would be updated without uploading to S3",
                    action="store_true", default=False)
parser.add_argument('--acl', help="The ACL to apply to uploaded files.",
                    type=str, default="public-read", choices=valid_acls)
parser.add_argument('-v', '--version', help="Print the script version and exit",
                    action="store_true", default=False)
parser.add_argument('-z', '--gzip', help="gzip files before uploading",
                    action="store_true", default=False)
parser.add_argument('--confirm', help="Confirm each file before deleting. Only works when --delete is set.",
                    action="store_true", default=False)
parser.add_argument(
    '--charset', help="The charset header to add to text files", default=False)
parser.add_argument('--gitignore', help="Add .gitignore rules to the exclude list",
                    action="store_true", default=False)
parser.add_argument('-c', '--config', help="path to config file. Defaults to deploy.json in current directory",
                    type=str, default="deploy.json")
parser.add_argument('-q', '--quiet', help="Suppress all output. Useful for automated usage.",
                    action="store_true", default=False)
parser.add_argument('-p', '--processes',
                    help="The number of concurrent processes to use for uploading/deleting.", type=int, default=10)
parser.add_argument(
    '--cloudfront', help="Specify a CloudFront distribution to invalidate after updating.", default=None)
args = parser.parse_args()

if args.quiet:
    QUIET = True

if args.processes > 0:
    try:
        from multiprocessing.pool import ThreadPool
    except ImportError:
        alert("Please install multiprocessing. `pip install multiprocessing`",
              os.EX_UNAVAILABLE)

# load the config file
try:
    config = open(args.config, 'r')
except IOError:
    alert("config file is missing. Default is deploy.json in your current directory. See http://dryan.github.io/d3ploy for more information.", os.EX_NOINPUT)

config = json.load(config)

environments = [str(item) for item in config.keys()]

# Check if no environments are configured in the file
if not environments:
    alert("No environments found in config file: %s", os.EX_NOINPUT)

# check if environment actually exists in the config file
if args.environment not in environments:
    valid_envs = '(%s)' % ', '.join(map(str, environments))
    alert("environment %s not found in config. Choose from '%s'" %
          (args.environment, valid_envs), os.EX_NOINPUT)


AWS_KEY = args.access_key
AWS_SECRET = args.access_secret

# look for credentials file in this directory
if os.path.exists('.aws'):
    local_config = ConfigParser.ConfigParser()
    local_config.read('.aws')
    if local_config.has_section('Credentials'):
        if AWS_KEY is None:
            AWS_KEY = local_config.get('Credentials', 'aws_access_key_id')
        if AWS_SECRET is None:
            AWS_SECRET = local_config.get(
                'Credentials', 'aws_secret_access_key')

# lookup global AWS keys if needed
if AWS_KEY is None:
    AWS_KEY = boto.config.get('Credentials', 'aws_access_key_id')

if AWS_SECRET is None:
    AWS_SECRET = boto.config.get('Credentials', 'aws_secret_access_key')

# lookup AWS key environment variables
if AWS_KEY is None:
    AWS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
if AWS_SECRET is None:
    AWS_SECRET = os.environ.get('AWS_SECRET_ACCESS_KEY')

# this is where the actual upload happens, called by upload_files


def upload_file(filename):
    if killswitch.is_set():
        return (filename, 0)
    updated = 0
    keyname = '/'.join([bucket_path.rstrip('/'),
                        prefix_regex.sub('', filename).lstrip('/')])
    s3key = s3bucket.get_key(keyname)
    local_file = open(filename, 'r')
    # this needs to be computed before gzipping
    md5 = boto.utils.compute_md5(local_file)[0]
    mimetype = mimetypes.guess_type(filename)
    local_file.close()

    if s3key is None or args.force or not s3key.get_metadata('d3ploy-hash') == md5:
        if args.gzip or environ_config.get('gzip', False):
            if not mimetype[1] == 'gzip' and not mimetype[0] in environ_config.get('gzip_skip', []):
                f_in = open(filename, 'rb')
                f_out = gzip.open(filename + '.gz', 'wb')
                f_out.writelines(f_in)
                f_out.close()
                f_in.close()
                filename = f_out.name
        local_file = open(filename, 'r')
        is_gzipped = local_file.read().find('\x1f\x8b') == 0
        local_file.seek(0)
        updated += 1
        if bar:
            progress_update(bar, bar.currval + 1)
        else:
            alert('Copying %s to %s/%s' %
                  (filename, s3bucket.name, keyname.lstrip('/')))
        if args.dry_run:
            if filename not in files:
                # this filename was modified by gzipping
                os.remove(filename)
            return (keyname.lstrip('/'), updated)
        if s3key is None:
            s3key = s3bucket.new_key(keyname)
        headers = {}
        if is_gzipped or mimetype[1] == 'gzip':
            headers['Content-Encoding'] = 'gzip'
        if args.charset or environ_config.get('charset', False) and mimetype[0] and mimetype[0].split('/')[0] == 'text':
            headers['Content-Type'] = str('%s;charset=%s' % (
                mimetype[0], args.charset or environ_config.get('charset')))
        if mimetype[0] in caches.keys():
            s3key.set_metadata(
                'Cache-Control', str('max-age=%s, public' % str(caches.get(mimetype[0]))))
        s3key.set_metadata('d3ploy-hash', md5)
        s3key.set_contents_from_file(local_file, headers=headers)
        s3key.set_acl(args.acl)
    else:
        if(bar):
            progress_update(bar, bar.currval + 1)
    if filename not in files:
        # this filename was modified by gzipping
        os.remove(filename)
    local_file.close()

    return (keyname.lstrip('/'), updated)

# this where the actual removal happens, called by upload_files


def delete_file(keyname):
    if killswitch.is_set():
        return 0
    key = s3bucket.get_key(keyname)
    deleted = 0
    needs_confirmation = args.confirm or environ_config.get('confirm', False)
    if needs_confirmation:
        confirmed = raw_input('%sRemove %s/%s [yN]: ' % (
            '\n' if bar and not needs_confirmation else '', s3bucket.name, key.name.lstrip('/'))) in ["Y", "y"]
    else:
        confirmed = True
    if confirmed:
        if bar and not needs_confirmation:
            progress_update(bar, bar.currval + 1)
        else:
            alert('Deleting %s/%s' % (s3bucket.name, key.name.lstrip('/')))
        deleted += 1
        if not args.dry_run:
            key.delete()
    else:
        if bar and not needs_confirmation:
            progress_update(bar, bar.currval + 1)
        alert('%sSkipping removal of %s/%s' %
              ('\n' if bar and not needs_confirmation else '', s3bucket.name, key.name.lstrip('/')))
    return deleted

# this is where the setup for each environment happens then passes off the
# work to upload_file()


def upload_files(env):
    global environ_config, bucket_path, s3bucket, prefix_regex, files, caches, pool

    alert('Using settings for "%s" environment' % env)

    bucket = environ_config.get('bucket')
    if not bucket:
        alert('A bucket to upload to was not specified for "%s" environment' %
              args.environment, os.EX_NOINPUT)

    KEY = environ_config.get('aws_key', AWS_KEY)

    SECRET = environ_config.get('aws_secret', AWS_SECRET)

    if KEY is None or SECRET is None:
        alert("AWS credentials were not found. See https://gist.github.com/dryan/5317321 for more information.", os.EX_NOINPUT)

    if '.' in bucket:
        s3connection = boto.connect_s3(
            KEY, SECRET, calling_format=OrdinaryCallingFormat())
    else:
        s3connection = boto.connect_s3(KEY, SECRET)

    # test the bucket connection
    try:
        s3bucket = s3connection.get_bucket(bucket)
    except boto.exception.S3ResponseError:
        alert('Bucket "%s" could not be retrieved with the specified credentials' %
              bucket, os.EX_NOINPUT)

    # get the rest of the options
    local_path = environ_config.get('local_path', '.')
    bucket_path = environ_config.get('bucket_path', '/')
    excludes = environ_config.get('exclude', [])
    svc_directories = ['.git', '.svn']
    if args.gitignore or environ_config.get('gitignore', False):
        if os.path.exists('.gitignore'):
            gitignore = open('.gitignore', 'r')
            for line in gitignore.readlines():
                excludes.append(line.strip())
        else:
            alert(
                "--gitignore option set, but .gitignore file was not found", color=ALERT_COLOR)

    if type(excludes) == str or type(excludes) == unicode:
        excludes = [excludes]

    exclude_regexes = [re.compile(r'%s' % s) for s in excludes]

    files = []
    prefix_regex = re.compile(r'^%s' % local_path)

    for dirname, dirnames, filenames in os.walk(local_path):
        for filename in filenames:
            filename = os.path.join(dirname, filename)
            excluded = False
            for regex in exclude_regexes:
                if regex.search(filename):
                    excluded = True
            if not excluded:
                files.append(filename)

        for svc_directory in svc_directories:
            if svc_directory in dirnames:
                dirnames.remove(svc_directory)

    deleted = 0
    caches = environ_config.get('cache', {})
    progress_setup('Updating %s: ' % env, len(files), OK_COLOR)

    if args.processes > 0:
        keynames = []
        updated = 0
        pool = ThreadPool(args.processes)
        for fn in files:
            job = pool.apply_async(upload_file, args=(fn,))
            try:
                keynames.append(job.get())
            except KeyboardInterrupt:
                killswitch.set()
    else:
        keynames = []
        for fn in files:
            keynames.append(upload_file(fn))
    if bar and not killswitch.is_set():
        bar.finish()

    updated = sum([i[1] for i in keynames])
    keynames = [i[0] for i in keynames if i[0]]

    if args.delete or environ_config.get('delete', False) and not killswitch.is_set():
        to_remove = [key.name for key in s3bucket.list(
            prefix=bucket_path.lstrip('/')) if key.name not in keynames]
        if len(to_remove):
            progress_setup('Cleaning %s: ' % env, len(to_remove), ALERT_COLOR)
            if args.processes > 0:
                deleted = 0
                pool = ThreadPool(args.processes)
                for kn in to_remove:
                    job = pool.apply_async(delete_file, args=(kn,))
                    try:
                        deleted += job.get()
                    except KeyboardInterrupt:
                        killswitch.set()
            else:
                for kn in to_remove:
                    deleted += delete_file(kn)
            if bar and not killswitch.is_set():
                bar.finish()

    verb = "would be" if args.dry_run else "were"
    alert("")
    notify(args.environment, "%d files %s updated" %
           (updated, verb), color=OK_COLOR)
    if args.delete or environ_config.get('delete', False):
        notify(args.environment, "%d files %s removed" %
               (deleted, verb), color=ALERT_COLOR)
    cloudfront_id = environ_config.get('cloudfront', None)
    if cloudfront_id:
        if not isinstance(cloudfront_id, list):
            cloudfront_id = [cloudfront_id]
        for cf_id in cloudfront_id:
            if args.dry_run:
                notify(args.environment, "CloudFront distribution {} invalidation would be requested".format(
                    cf_id), color=OK_COLOR)
            else:
                cloudfront = boto.connect_cloudfront(KEY, SECRET)
                cloudfront.create_invalidation_request(cf_id, ['*'])
                notify(args.environment, "CloudFront distribution {} invalidation requested".format(
                    cf_id), color=OK_COLOR)


if args.environment not in config:
    alert('The "%s" environment was not found in deploy.json' %
          args.environment, os.EX_NOINPUT)


def main():
    global environ_config
    if args.all:
        for environ in config:
            alert("Uploading environment %d of %d" %
                  (config.keys().index(environ) + 1, len(config.keys())))
            environ_config = config[environ]
            if not environ == "default":
                environ_config = dict(
                    config['default'].items() + config[environ].items())
            if not environ_config.get('excludes', False):
                environ_config['excludes'] = []
            environ_config['excludes'].append(args.config)
            upload_files(environ)
    else:
        environ_config = config[args.environment]
        if not args.environment == "default":
            environ_config = dict(
                config['default'].items() + config[args.environment].items())
        if not environ_config.get('exclude', False):
            environ_config['exclude'] = []
        environ_config['exclude'].append(args.config)
        upload_files(args.environment)


if __name__ == "__main__":
    main()
