#!/usr/bin/env python

# Notification Center code borrowed from https://github.com/maranas/pyNotificationCenter/blob/master/pyNotificationCenter.py

import os, sys, json, re, hashlib, argparse

try:
    import boto
except ImportError:
    print "Please install boto. `pip install boto`"
    sys.exit(os.EX_UNAVAILABLE)
    
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
    if __name__ == "__main__":
        print text
    if notifications:
        notification    =   NSUserNotification.alloc().init()
        notification.setTitle_('d3ploy')
        notification.setSubtitle_(env)
        notification.setInformativeText_(text)
        notification.setUserInfo_({})
        notification.setSoundName_("NSUserNotificationDefaultSoundName")
        notification.setDeliveryDate_(Foundation.NSDate.dateWithTimeInterval_sinceDate_(0, Foundation.NSDate.date()))
        NSUserNotificationCenter.defaultUserNotificationCenter().scheduleNotification_(notification)
    
valid_acls      =   ["private", "public-read", "public-read-write", "authenticated-read"]

parser          =   argparse.ArgumentParser()
parser.add_argument('environment', help = "Which environment to deploy to", nargs = "?", type = str, default = "default",)
parser.add_argument('-a', '--access-key', help = "AWS Access Key ID", type = str)
parser.add_argument('-s', '--access-secret', help = "AWS Access Key Secret", type = str)
parser.add_argument('-f', '--force', help = "Upload all files whether they are currently up to date on S3 or not", action = "store_true", default = False)
parser.add_argument('--all', help = "Upload to all environments", action = "store_true", default = False)
parser.add_argument('-n', '--dry-run', help = "Show which files would be updated without uploading to S3", action = "store_true", default = False)
parser.add_argument('--acl', help = "The ACL to apply to uploaded files. Must be one of: %s" % ' '.join(valid_acls), type = str, default = "public-read",)

args            =   parser.parse_args()

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
    if __name__ == "__main__":
        print 'Using settings for "%s" environment' % env
    
    bucket              =   config.get('bucket')
    if not bucket:
        if __name__ == "__main__":
            print 'A bucket to upload to was not specified for "%s" environment' % args.environment
        sys.exit(os.EX_NOINPUT)

    KEY         =   config.get('aws_key', AWS_KEY)

    SECRET      =   config.get('aws_secret', AWS_SECRET)
    
    if KEY is None or SECRET is None:
        if __name__ == "__main__":
            print "AWS credentials were not found. See https://gist.github.com/dryan/5317321 for more information."
        sys.exit(os.EX_NOINPUT)
    
    s3connection        =   boto.connect_s3(KEY, SECRET)

    # test the bucket connection
    try:
        s3bucket        =   s3connection.get_bucket(bucket)
    except boto.exception.S3ResponseError:
        if __name__ == "__main__":
            print 'Bucket "%s" could not be retrieved with the specified credentials' % bucket
        sys.exit(os.EX_NOINPUT)

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
            if __name__ == "__main__":
                print 'Copying %s to %s%s' % (filename, bucket, keyname)
            updated     +=  1
            if args.dry_run:
                continue
            if s3key is None:
                s3key   =   s3bucket.new_key(keyname)
            s3key.set_contents_from_filename(filename)
            s3key.set_acl(args.acl)
        
    for key in s3bucket.list(prefix = bucket_path.lstrip('/')):
        if not key.name in keynames:
            if __name__ == "__main__":
                print 'Deleting %s/%s' % (bucket, key.name.lstrip('/'))
            deleted     +=  1
            if args.dry_run:
                continue
            key.delete()
        
    verb    =   "would be" if args.dry_run else "were"
    notify(args.environment, "%d files %s updated and %d files %s removed" % (updated, verb, deleted, verb))
    if __name__ == "__main__":
        print ""

# load the config file for this folder
try:
    config          =   open('deploy.json', 'r')
except IOError:
    if __name__ == "__main__":
        print "deploy.json file is missing. See https://gist.github.com/dryan/5317321 for more information."
    sys.exit(os.EX_NOINPUT)

config              =   json.load(config)

if not args.environment in config:
    if __name__ == "__main__":
        print 'The "%s" environment was not found in deploy.json' % args.environment
    sys.exit(os.EX_NOINPUT)

def main():
    if args.all:
        for environ in config:
            if __name__ == "__main__":
                print "Uploading environment %d of %d" % (config.keys().index(environ) + 1, len(config.keys()))
            upload_files(environ, config[environ])
    else:
        upload_files(args.environment, config[args.environment])

if __name__ == "__main__":
    main()
