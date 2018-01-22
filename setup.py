import os
import re
from distutils.core import setup

VERSION_FINDER = re.compile(
    r'^VERSION = \'([\d+]\.[\d+].[\d+])\'$',
    re.MULTILINE
)

script = open('d3ploy/d3ploy.py', 'r').read()

VERSION = VERSION_FINDER.findall(script)

if VERSION:
    VERSION = VERSION.pop()
else:
    raise ValueError('Could not find version number in script file')

DESCRIPTION = ''

if os.path.exists('README.md'):
    DESCRIPTION = open('README.md', 'r').read()
if os.path.exists('README.rst'):
    DESCRIPTION = open('README.rst', 'r').read()

setup(
    name='d3ploy',
    packages=['d3ploy'],
    version=VERSION,
    description='Script for uploading files to S3 with multiple environment support.',
    long_description=DESCRIPTION,
    author='Dan Ryan',
    author_email='d@dryan.com',
    url='https://github.com/dryan/d3ploy',
    download_url='https://github.com/dryan/d3ploy/archive/{}.tar.gz'.format(
        VERSION),
    scripts=['bin/d3ploy'],
)
