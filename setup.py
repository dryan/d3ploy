import pathlib
import re
from distutils.core import setup

VERSION_FINDER = re.compile(
    r"^VERSION = \"([\d+]\.[\d+].[\d+](-beta[\d+]?)?)\"$", re.MULTILINE
)

VERSION = VERSION_FINDER.findall(pathlib.Path("d3ploy/d3ploy.py").read_text())

if VERSION:
    VERSION = VERSION.pop()[0]
else:
    raise ValueError("Could not find version number in script file")

DESCRIPTION = ""

readme_md = pathlib.Path("README.md")
readme_rst = pathlib.Path("README.rst")
if readme_md.exists():
    DESCRIPTION = readme_md.read_text()

setup(
    name="d3ploy",
    packages=["d3ploy"],
    version=VERSION,
    description="Utility for uploading files to S3 with multiple environment support.",
    long_description=DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Dan Ryan",
    author_email="opensource@dryan.com",
    url="https://github.com/dryan/d3ploy",
    download_url="https://github.com/dryan/d3ploy/archive/{}.tar.gz".format(VERSION),
    scripts=["bin/d3ploy"],
)
