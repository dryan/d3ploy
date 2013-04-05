#!/usr/bin/env python

import os, sys, json, re, hashlib

try:
    import boto
except ImportError:
    print "Please install boto. `pip install boto`"
    sys.exit(os.EX_UNAVAILABLE)
    
from optparse import OptionParser

parser          =   OptionParser()
parser.add_option('-a', '--access-key', help = "AWS Access Key ID", dest = "AWS_KEY", type = "string")
parser.add_option('-s', '--access-secret', help = "AWS Access Key Secret", dest = "AWS_SECRET", type = "string")
parser.add_option('-e', '--environment', help = "Which environment to deploy to", dest = "environment", type = "string", default = "default",)
parser.add_option('-f', '--force', help = "Upload all files whether they are currently up to date on S3 or not", dest = "force", action = "store_true", default = False)

(options, args) =   parser.parse_args()

# allow positional argument for environment
if len(args) and options.environment == "default":
    options.environment =   args.pop(0)

print 'Using settings for "%s" environment' % options.environment

AWS_KEY         =   options.AWS_KEY
AWS_SECRET      =   options.AWS_SECRET

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
    
# load the config file for this folder
try:
    config          =   open('deploy.json', 'r')
except IOError:
    print "deploy.json file is missing. See https://gist.github.com/dryan/5317321 for more information."
    sys.exit(os.EX_NOINPUT)

config              =   json.load(config)

if not options.environment in config:
    print 'The "%s" environment was not found in deploy.json' % options.environment
    sys.exit(os.EX_NOINPUT)
    
config              =   config[options.environment]
    
bucket              =   config.get('bucket')
if not bucket:
    print 'A bucket to upload to was not specified for "%s" environment' % options.environment
    sys.exit(os.EX_NOINPUT)

if config.get('aws_key') is not None:
    AWS_KEY         =   config.get('aws_key')

if config.get('aws_secret') is not None:
    AWS_SECRET      =   config.get('aws_secret')
    
if AWS_KEY is None or AWS_SECRET is None:
    print "AWS credentials were not found. See https://gist.github.com/dryan/5317321 for more information."
    sys.exit(os.EX_NOINPUT)
    
s3connection        =   boto.connect_s3(AWS_KEY, AWS_SECRET)

# test the bucket connection
try:
    s3bucket        =   s3connection.get_bucket(bucket)
except boto.exception.S3ResponseError:
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
    if s3key is None or options.force or not s3key.etag.strip('"') == md5.hexdigest():
        print 'Copying %s to %s%s' % (filename, bucket, keyname)
        if s3key is None:
            s3key   =   s3bucket.new_key(keyname)
        s3key.set_contents_from_filename(filename)
        s3key.set_acl('public-read')
        updated     +=  1
        
for key in s3bucket.list(prefix = bucket_path.lstrip('/')):
    if not key.name in keynames:
        print 'Deleting %s/%s' % (bucket, key.name.lstrip('/'))
        key.delete()
        deleted     +=  1
        
print "%d files were updated and %d files were removed" % (updated, deleted)
