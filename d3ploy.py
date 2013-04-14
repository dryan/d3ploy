#!/usr/bin/env python

# Notification Center code borrowed from https://github.com/maranas/pyNotificationCenter/blob/master/pyNotificationCenter.py

VERSION =   '1.1.0'

import os, sys, json, re, hashlib, argparse, urllib, time

# disable import warnings
import warnings
warnings.filterwarnings('ignore')

DEFAULT_COLOR   =   '\033[0;0m'
ERROR_COLOR     =   '\033[01;31m'
ALERT_COLOR     =   '\033[01;33m'

def alert(text, error_code = None, color = None):
    if error_code is not None:
        sys.stderr.write('%s%s%s\n' % (color or ERROR_COLOR, text, DEFAULT_COLOR))
        sys.stderr.flush()
        sys.exit(error_code)
    else:
        sys.stdout.write('%s%s%s\n' % (color or DEFAULT_COLOR, text, DEFAULT_COLOR))
        sys.stdout.flush()

# check for updates
GIST_URL        =   'https://api.github.com/repos/dryan/d3ploy/contents/d3ploy.py'
CHECK_FILE      =   os.path.expanduser('~/.d3ploy-update-check')
if not os.path.exists(CHECK_FILE):
    try:
        open(CHECK_FILE, 'w')
    except IOError:
        pass
try:
    last_checked    =   int(open(CHECK_FILE, 'r').read().strip())
except ValueError:
    last_checked    =   0
now =   int(time.time())
if now - last_checked > 86400:
    # it has been a day since the last update check
    try:
        gist_hash       =   hashlib.md5(json.load(urllib.urlopen(GIST_URL)).get('content')).hexdigest()
        script_hash     =   hashlib.md5(open(__file__, 'r').read()).hexdigest()
        check_file      =   open(CHECK_FILE, 'w')
        check_file.write('%d' % now)
        check_file.flush()
        check_file.close()
        if not gist_hash == script_hash:
            alert('There has been an update for d3ploy.\nPlease see https://github.com/dryan/d3ploy or run `pip install --upgrade d3ploy`.', color = ALERT_COLOR)
    except:
        pass

try:
    import boto
except ImportError:
    alert("Please install boto. `pip install boto`", os.EX_UNAVAILABLE)
    
try:
    import Foundation, objc
    notifications   =   True
except ImportError:
    notifications   =   False
    
if notifications:
    try:
        NSUserNotification          =   objc.lookUpClass('NSUserNotification')
        NSUserNotificationCenter    =   objc.lookUpClass('NSUserNotificationCenter')
    except objc.nosuchclass_error:
        notifications   =   False
        
def notify(env, text):
    alert(text)
    if notifications:
        notification    =   NSUserNotification.alloc().init()
        notification.setTitle_('d3ploy')
        notification.setSubtitle_(env)
        notification.setInformativeText_(text)
        notification.setUserInfo_({})
        if os.environ.get('D3PLOY_NC_SOUND'):
            notification.setSoundName_("NSUserNotificationDefaultSoundName")
        notification.setDeliveryDate_(Foundation.NSDate.dateWithTimeInterval_sinceDate_(0, Foundation.NSDate.date()))
        NSUserNotificationCenter.defaultUserNotificationCenter().scheduleNotification_(notification)
        
# load the config file for this folder
try:
    config      =   open('deploy.json', 'r')
except IOError:
    alert("deploy.json file is missing. See https://gist.github.com/dryan/5317321 for more information.", os.EX_NOINPUT)

config          =   json.load(config)

environments    =   [str(item) for item in config.keys()]
    
valid_acls      =   ["private", "public-read", "public-read-write", "authenticated-read"]

parser          =   argparse.ArgumentParser()
parser.add_argument('environment', help = "Which environment to deploy to", nargs = "?", type = str, default = "default", choices = environments)
parser.add_argument('-a', '--access-key', help = "AWS Access Key ID", type = str)
parser.add_argument('-s', '--access-secret', help = "AWS Access Key Secret", type = str)
parser.add_argument('-f', '--force', help = "Upload all files whether they are currently up to date on S3 or not", action = "store_true", default = False)
parser.add_argument('--no-delete', help = "Don't remove orphaned files from S3", action = "store_true", default = False)
parser.add_argument('--delete', help = "Remove orphaned files from S3", action = "store_true", default = False)
parser.add_argument('--all', help = "Upload to all environments", action = "store_true", default = False)
parser.add_argument('-n', '--dry-run', help = "Show which files would be updated without uploading to S3", action = "store_true", default = False)
parser.add_argument('--acl', help = "The ACL to apply to uploaded files.", type = str, default = "public-read", choices = valid_acls)
parser.add_argument('-v', '--version', help = "Print the script version and exit", action = "store_true", default = False)

args            =   parser.parse_args()

if args.version:
    alert('d3ploy %s' % VERSION, os.EX_OK, DEFAULT_COLOR)

if args.no_delete:
    alert('--no-delete has been deprecated. Orphaned files will only be deleted if --delete is specified.')

AWS_KEY         =   args.access_key
AWS_SECRET      =   args.access_secret

# lookup global AWS keys if needed
if AWS_KEY is None:
    AWS_KEY     =   boto.config.get('Credentials', 'aws_access_key_id')
    
if AWS_SECRET is None:
    AWS_SECRET  =   boto.config.get('Credentials', 'aws_secret_access_key')
    
# lookup AWS key environment variables
if AWS_KEY is None:
    AWS_KEY     =   os.environ.get('AWS_ACCESS_KEY_ID')
if AWS_SECRET is None:
    AWS_SECRET  =   os.environ.get('AWS_SECRET_ACCESS_KEY')
    
def upload_files(env, config):
    alert('Using settings for "%s" environment' % env)
    
    bucket              =   config.get('bucket')
    if not bucket:
        alert('A bucket to upload to was not specified for "%s" environment' % args.environment, os.EX_NOINPUT)

    KEY         =   config.get('aws_key', AWS_KEY)

    SECRET      =   config.get('aws_secret', AWS_SECRET)
    
    if KEY is None or SECRET is None:
        alert("AWS credentials were not found. See https://gist.github.com/dryan/5317321 for more information.", os.EX_NOINPUT)
    
    s3connection        =   boto.connect_s3(KEY, SECRET)

    # test the bucket connection
    try:
        s3bucket        =   s3connection.get_bucket(bucket)
    except boto.exception.S3ResponseError:
        alert('Bucket "%s" could not be retrieved with the specified credentials' % bucket, os.EX_NOINPUT)

    # get the rest of the options
    local_path          =   config.get('local_path', '.')
    bucket_path         =   config.get('bucket_path', '/')
    excludes            =   config.get('exclude', [])
    svc_directories     =   ['.git', '.svn']

    if type(excludes) == str or type(excludes) == unicode:
        excludes        =   [excludes]
    
    exclude_regexes     =   [re.compile(r'%s' % s) for s in excludes]
    
    files               =   []

    for dirname, dirnames, filenames in os.walk(local_path):
        for filename in filenames:
            filename    =   os.path.join(dirname, filename)
            for regex in exclude_regexes:
                if regex.match(filename):
                    continue
                    continue
            files.append(filename)
        
        for svc_directory in svc_directories:
            if svc_directory in dirnames:
                dirnames.remove(svc_directory)
            
    prefix_regex        =   re.compile(r'^%s' % local_path)

    keynames            =   []
    updated             =   0
    deleted             =   0
            
    for filename in files:
        keyname         =   '/'.join([bucket_path.rstrip('/'), prefix_regex.sub('', filename).lstrip('/')])
        keynames.append(keyname.lstrip('/'))
        s3key           =   s3bucket.get_key(keyname)
        local_file      =   open(filename, 'r')
        md5             =   hashlib.md5()
        while True:
            data        =   local_file.read(8192)
            if not data:
                break
            md5.update(data)
        if s3key is None or args.force or not s3key.etag.strip('"') == md5.hexdigest():
            alert('Copying %s to %s%s' % (filename, bucket, keyname))
            updated     +=  1
            if args.dry_run:
                continue
            if s3key is None:
                s3key   =   s3bucket.new_key(keyname)
            s3key.set_contents_from_filename(filename)
            s3key.set_acl(args.acl)
    
    if args.delete:
        for key in s3bucket.list(prefix = bucket_path.lstrip('/')):
            if not key.name in keynames:
                alert('Deleting %s/%s' % (bucket, key.name.lstrip('/')))
                deleted     +=  1
                if args.dry_run:
                    continue
                key.delete()
        
    verb    =   "would be" if args.dry_run else "were"
    notify(args.environment, "%d files %s updated" % (updated, verb))
    if args.delete:
        notify(args.environment, "%d files %s removed" % (deleted, verb))
    alert("")

if not args.environment in config:
    alert('The "%s" environment was not found in deploy.json' % args.environment, os.EX_NOINPUT)

def main():
    if args.all:
        for environ in config:
            alert("Uploading environment %d of %d" % (config.keys().index(environ) + 1, len(config.keys())))
            upload_files(environ, config[environ])
    else:
        upload_files(args.environment, config[args.environment])

if __name__ == "__main__":
    main()
