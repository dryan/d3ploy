#!/usr/bin/env python3

import argparse
import contextlib
import hashlib
import json
import mimetypes
import os
import pathlib
import signal
import sys
import threading
import time
import typing
import urllib
import uuid
from concurrent import futures

import boto3
import botocore
import colorama
import pathspec
from boto3.resources.base import ServiceResource as AWSServiceResource
from colorama import init as colorama_init
from tqdm import tqdm

VERSION = "4.1.4"

VALID_ACLS = [
    "private",
    "public-read",
    "public-read-write",
    "authenticated-read",
]

QUIET = False

# From https://mzl.la/39XkRvH
MIMETYPES = {
    "application/manifest+json": [".webmanifest"],
    "application/ogg": [".ogg"],
    "audio/wave": [".wav"],
    "font/otf": [".otf"],
    "font/ttf": [".ttf"],
    "font/woff": [".woff"],
    "font/woff2": [".woff2"],
    "image/apng": [".apng"],
    "image/avif": [".avif"],
    "image/bmp": [".bmp"],
    "image/gif": [".gif"],
    "image/jpeg": [".jpeg", ".jpg", ".jfif", ".pjpeg", ".pjp"],
    "image/jxl": [".jxl"],
    "image/png": [".png"],
    "image/svg+xml": [".svg"],
    "image/tiff": [".tif", ".tiff"],
    "image/webp": [".webp"],
    "image/x-icon": [".ico", ".cur"],
    "text/css": [".css"],
    "text/html": [".html", ".htm"],
    "text/javascript": [".js"],
    "text/plain": [".txt"],
    "video/webm": [".webm"],
}

for mimetype in MIMETYPES:
    for extension in MIMETYPES[mimetype]:
        mimetypes.add_type(mimetype, extension)


def get_progress_bar(*args, **kwargs) -> tqdm:
    kwargs.setdefault("unit", "files")
    kwargs.setdefault("colour", "GREEN")
    if QUIET:
        kwargs["disable"] = True
    return tqdm(*args, **kwargs)


# inspired by
# https://www.peterbe.com/plog/fastest-way-to-find-out-if-a-file-exists-in-s3
def key_exists(
    s3: AWSServiceResource,
    bucket_name: str,
    key_name: str,
) -> bool:
    bucket = s3.Bucket(bucket_name)
    for obj in bucket.objects.filter(Prefix=key_name):
        if obj.key == key_name:
            return True
    return False


OUTPUT = []


def display_output():
    while len(OUTPUT):
        text, is_error = OUTPUT.pop()
        if QUIET and not is_error:
            continue
        buffer = sys.stderr if is_error else sys.stdout
        buffer.write(f"{text}\n")
        buffer.flush()


def alert(
    text: str,
    error_code: typing.Optional[int] = None,
    color: typing.Optional[str] = None,
):
    if color is None:
        color = (
            colorama.Fore.RED
            if error_code and not error_code == os.EX_OK
            else colorama.Style.RESET_ALL
        )
    if not QUIET:
        OUTPUT.append(
            (
                f"{color}{text}{colorama.Style.RESET_ALL}",
                error_code not in [None, os.EX_OK],
            )
        )
    if error_code is not None:
        display_output()
        sys.exit(error_code)


killswitch = threading.Event()


def bail(*args, **kwargs):  # pragma: no cover
    killswitch.set()
    alert("\nExiting...", os.EX_OK, colorama.Fore.RED)


signal.signal(signal.SIGINT, bail)


def check_for_updates(
    check_file_path: typing.Optional[
        typing.Union[pathlib.Path, str]
    ] = "~/.d3ploy-update-check",
    this_version: str = VERSION,
) -> bool:
    update_available = None
    try:
        from pkg_resources import parse_version
    except ImportError:  # pragma: no cover
        return None
    PYPI_URL = "https://pypi.org/pypi/d3ploy/json"
    CHECK_FILE = pathlib.Path(check_file_path).expanduser()
    if not CHECK_FILE.exists():
        try:
            CHECK_FILE.write_text("")
        except IOError:  # pragma: no cover
            pass
    try:
        last_checked = int(CHECK_FILE.read_text().strip())
    except ValueError:
        last_checked = 0
    now = int(time.time())
    if now - last_checked > 86400:
        if os.environ.get("D3PLOY_DEBUG"):
            print("checking for update")
        # it has been a day since the last update check
        try:
            with contextlib.closing(urllib.request.urlopen(PYPI_URL)) as pypi_response:
                pypi_data = json.load(pypi_response)
                pypi_version = parse_version(pypi_data.get("info", {}).get("version"))
                if pypi_version > parse_version(this_version):
                    alert(
                        (
                            f"There has been an update for d3ploy. Version "
                            f"{pypi_version} is now available.\n"
                            f"Please see https://github.com/dryan/d3ploy or run "
                            f"`pip install --upgrade d3ploy`."
                        ),
                        color=colorama.Fore.YELLOW,
                    )
                    update_available = True
                else:
                    update_available = False
        except ConnectionResetError:  # pragma: no cover
            # if pypi fails, assume we can't get an update anyway
            update_available = False
        except Exception as e:  # pragma: no cover
            if os.environ.get("D3PLOY_DEBUG"):
                raise e
        CHECK_FILE.write_text(str(now))
    return update_available


# this is where the actual upload happens, called by sync_files
def upload_file(
    file_name: pathlib.Path,
    bucket_name: str,
    s3: AWSServiceResource,
    bucket_path: str,
    prefix: pathlib.Path,
    acl: typing.Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
    charset: typing.Optional[str] = None,
    caches: typing.Optional[typing.Dict[str, int]] = None,
    bar: typing.Optional[tqdm] = None,
) -> typing.Tuple[str, bool]:
    if killswitch.is_set():
        return (file_name, 0)
    if caches is None:
        caches = {}
    updated = 0

    if not isinstance(file_name, pathlib.Path):
        file_name = pathlib.Path(file_name)

    key_name = "/".join(
        [bucket_path.rstrip("/"), str(file_name.relative_to(prefix)).lstrip("/")]
    ).lstrip("/")
    if key_exists(s3, bucket_name, key_name):
        s3_obj = s3.Object(bucket_name, key_name)
    else:
        s3_obj = None
    local_md5 = hashlib.md5()
    with open(file_name, "rb") as local_file:
        for chunk in iter(lambda: local_file.read(4096), b""):
            local_md5.update(chunk)
    local_md5 = local_md5.hexdigest()
    mimetype = mimetypes.guess_type(file_name)
    if s3_obj is None or force or not s3_obj.metadata.get("d3ploy-hash") == local_md5:
        with open(file_name, "rb") as local_file:
            updated += 1
            if dry_run:
                if bar:  # pragma: no cover
                    bar.update()
                return (key_name.lstrip("/"), updated)
            extra_args = {
                "Metadata": {"d3ploy-hash": local_md5},
            }
            if acl is not None:
                extra_args["ACL"] = acl
            if charset and mimetype[0] and mimetype[0].split("/")[0] == "text":
                extra_args["ContentType"] = f"{mimetype[0]};charset={charset}"
            elif mimetype[0]:
                extra_args["ContentType"] = mimetype[0]
            cache_timeout = None
            if mimetype[0] in caches.keys():
                cache_timeout = caches.get(mimetype[0])
            elif mimetype[0] and f"{mimetype[0].split('/')[0]}/*" in caches.keys():
                cache_timeout = caches.get(f"{mimetype[0].split('/')[0]}/*")
            if cache_timeout is not None:
                if cache_timeout == 0:
                    extra_args["CacheControl"] = f"max-age={cache_timeout}, private"
                else:
                    extra_args["CacheControl"] = f"max-age={cache_timeout}, public"

            s3.meta.client.upload_fileobj(
                local_file,
                bucket_name,
                key_name,
                ExtraArgs=extra_args,
            )
    else:
        if s3_obj and s3_obj.metadata.get("d3ploy-hash") == local_md5:
            alert(f"Skipped {file_name}: already up-to-date")
    if bar:
        bar.update()
    return (key_name.lstrip("/"), updated)


def get_confirmation(message: str) -> bool:  # pragma: no cover
    confirm = input(f"{message} [yN]: ")

    return confirm.lower() in ["y", "yes"]


# this where the actual removal happens, called by sync_files
def delete_file(
    key_name: str,
    bucket_name: str,
    s3: AWSServiceResource,
    needs_confirmation: bool = False,
    bar: typing.Optional[tqdm] = None,
    dry_run: bool = False,
) -> int:
    if killswitch.is_set():
        return 0
    deleted = 0
    if needs_confirmation:
        confirmed = get_confirmation(
            f"{chr(10) if bar else ''}Remove {bucket_name}/{key_name.lstrip('/')}"
        )
    else:
        confirmed = True
    if confirmed:
        deleted += 1
        if not dry_run:
            s3.Object(bucket_name, key_name).delete()
    else:
        alert(
            f"{chr(10) if bar and not needs_confirmation else ''}Skipping removal of "
            f"{bucket_name}/{key_name.lstrip('/')}",
        )
    if bar:
        bar.update()
    return deleted


def determine_files_to_sync(
    local_path: typing.Union[pathlib.Path, str],
    excludes: typing.Optional[typing.Union[typing.Collection, str]] = None,
    gitignore: bool = False,
) -> typing.List[pathlib.Path]:
    if excludes is None:
        excludes = []
    if isinstance(excludes, str):
        excludes = [excludes]
    excludes.append(".gitignore")
    if not isinstance(local_path, pathlib.Path):
        local_path = pathlib.Path(local_path)
    gitignore_patterns = list(map(pathspec.patterns.GitWildMatchPattern, excludes))
    svc_directories = [".git", ".svn"]
    if gitignore:
        gitignores = []
        if pathlib.Path(".gitignore").exists():
            gitignores.append(".gitignore")
        for root, dir_names, file_names in os.walk(local_path):
            for dir_name in dir_names:
                if dir_name in svc_directories:
                    continue
                dir_name = os.path.join(root, dir_name)
                gitignore_path = os.path.join(dir_name, ".gitignore")
                if os.path.exists(gitignore_path):
                    gitignores.append(gitignore_path)
            for file_name in file_names:
                if file_name == ".gitignore":
                    gitignore_path = os.path.join(root, file_name)
                    gitignores.append(gitignore_path)
        for gitignore_file in gitignores:
            with open(gitignore_file) as f:
                spec = pathspec.PathSpec.from_lines("gitwildmatch", f)
                gitignore_patterns += [x for x in spec.patterns if x.regex]
        if not gitignores:
            alert(
                "--gitignore option set, but no .gitignore files were found",
                color=colorama.Fore.RED,
            )
    gitignore_spec = pathspec.PathSpec(gitignore_patterns)

    files = []
    if local_path.is_dir():
        for root, dir_names, file_names in os.walk(local_path):
            for file_name in file_names:
                file_name = pathlib.Path(root) / file_name
                if not gitignore_spec.match_file(file_name):
                    files.append(file_name)
            for svc_directory in svc_directories:
                if svc_directory in dir_names:
                    dir_names.remove(svc_directory)
    elif local_path.is_file() or local_path.is_symlink():
        if not gitignore_spec.match_file(local_path):
            files.append(local_path)
    return files


def invalidate_cloudfront(
    cloudfront_id: typing.Union[typing.Collection[str], str],
    env: str,
    dry_run: bool = False,
) -> typing.List[str]:
    output = []
    if not isinstance(cloudfront_id, list):
        cloudfront_id = [cloudfront_id]
    for cf_id in cloudfront_id:
        if dry_run:
            alert(
                f"CloudFront distribution {cf_id} invalidation would be requested",
                color=colorama.Fore.GREEN,
            )
        else:
            cloudfront = boto3.client("cloudfront")
            # we don't specify the individual paths because that's more
            # costly monetarily speaking
            response = cloudfront.create_invalidation(
                DistributionId=cf_id,
                InvalidationBatch={
                    "Paths": {"Quantity": 1, "Items": ["/*"]},
                    "CallerReference": uuid.uuid4().hex,
                },
            )
            alert(
                f"CloudFront distribution {cf_id} invalidation requested",
                color=colorama.Fore.GREEN,
            )
            output.append(response.get("Invalidation", {}).get("Id"))
    return [x for x in output if x]


def sync_files(
    env: str,
    bucket_name: typing.Optional[str] = None,
    local_path: typing.Optional[typing.Union[str, pathlib.Path]] = ".",
    bucket_path: typing.Optional[str] = "/",
    excludes: typing.Collection[str] = [],
    acl: typing.Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
    charset: typing.Optional[str] = None,
    gitignore: bool = False,
    processes: int = 1,
    delete: bool = False,
    confirm: bool = False,
    cloudfront_id: typing.Optional[typing.Union[typing.Collection[str], str]] = None,
    caches: typing.Optional[typing.Dict[str, int]] = None,
) -> typing.Dict[str, int]:
    alert(f'Using settings for "{env}" environment')

    if cloudfront_id is None:
        cloudfront_id = []

    if caches is None:
        caches = {}

    if not isinstance(local_path, pathlib.Path):
        local_path = pathlib.Path(local_path)

    if not bucket_name:
        alert(
            f'A bucket to upload to was not specified for "{env}" environment',
            os.EX_NOINPUT,
        )

    s3 = boto3.resource("s3")

    # test the bucket connection
    try:
        s3.meta.client.head_bucket(Bucket=bucket_name)
        bucket = s3.Bucket(bucket_name)
    except botocore.exceptions.ClientError as e:  # pragma: no cover
        if e.response["Error"]["Code"] == "403":
            alert(
                (
                    f'Bucket "{bucket_name}" could not be retrieved with the specified '
                    f"credentials. Tried Access Key ID "
                    f"{boto3.Session().get_credentials().access_key}"
                ),
                os.EX_NOUSER,
            )
        else:
            raise e

    files = determine_files_to_sync(local_path, excludes, gitignore=gitignore)
    deleted = 0
    key_names = []
    updated = 0
    with get_progress_bar(
        desc=f"{colorama.Fore.GREEN}Updating {env}{colorama.Style.RESET_ALL}",
        total=len(files),
    ) as bar:
        with futures.ThreadPoolExecutor(max_workers=processes) as executor:
            jobs = []
            for fn in files:
                job = executor.submit(
                    upload_file,
                    *(fn, bucket_name, s3, bucket_path, local_path),
                    **{
                        "acl": acl,
                        "force": force,
                        "dry_run": dry_run,
                        "charset": charset,
                        "caches": caches,
                        "bar": bar,
                    },
                )
                jobs.append(job)
            for job in futures.as_completed(jobs):
                key_names.append(job.result())
            executor.shutdown(wait=True)

    updated = sum([i[1] for i in key_names])
    key_names = [i[0] for i in key_names if i[0]]

    if delete and not killswitch.is_set():
        to_remove = [
            key.key
            for key in bucket.objects.filter(Prefix=bucket_path.lstrip("/"))
            if key.key.lstrip("/") not in key_names
        ]
        if len(to_remove):
            with get_progress_bar(
                desc=f"{colorama.Fore.RED}Cleaning {env}{colorama.Style.RESET_ALL}",
                total=len(to_remove),
                colour="RED",
            ) as bar:
                deleted = 0
                with futures.ThreadPoolExecutor(max_workers=processes) as executor:
                    jobs = []
                    for kn in to_remove:
                        job = executor.submit(
                            delete_file,
                            *(kn, bucket_name, s3),
                            **{
                                "needs_confirmation": confirm,
                                "bar": bar,
                                "dry_run": dry_run,
                            },
                        )
                        jobs.append(job)
                    for job in futures.as_completed(jobs):
                        deleted += job.result()
                    executor.shutdown(wait=True)

    verb = "would be" if dry_run else "were"
    outcome = {
        "uploaded": updated,
        "deleted": deleted,
        "invalidated": 0,
    }
    alert("")
    alert(
        (
            f"{updated:d} file{'' if updated == 1 else 's'} "
            f"{'was' if verb == 'were' and updated == 1 else verb} updated"
        ),
        color=colorama.Fore.GREEN,
    )
    if delete:
        alert(
            (
                f"{deleted:d} file{'' if deleted == 1 else 's'} "
                f"{'was' if verb == 'were' and deleted == 1 else verb} removed"
            ),
            color=colorama.Fore.RED,
        )
    if cloudfront_id and (updated or deleted):
        invalidations = invalidate_cloudfront(cloudfront_id, env, dry_run=dry_run)
        outcome["invalidated"] = len(invalidations)
    elif cloudfront_id:
        outcome["invalidated"] = 0
        alert("Cloudfront invalidation skipped because no files changed")
    return outcome


def processes_int(x: typing.Union[str, int, float]) -> int:
    x = int(x)
    if x < 1 or x > 50:
        raise argparse.ArgumentTypeError("An integer between 1 and 50 is required")
    return x


def cli():
    global QUIET
    if "-v" in sys.argv or "--version" in sys.argv:
        # do this here before any of the config checks are run
        alert(f"d3ploy {VERSION}", os.EX_OK, colorama.Fore.GREEN)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "environment",
        help="Which environment to deploy to",
        nargs="*",
        type=str,
        default=["default"],
    )
    parser.add_argument(
        "--bucket-name",
        help="The bucket to upload files to",
        type=str,
    )
    parser.add_argument(
        "--local-path",
        help="The local folder to upload files from",
        type=str,
    )
    parser.add_argument(
        "--bucket-path",
        help="The remote folder to upload files to",
        type=str,
    )
    parser.add_argument(
        "--exclude",
        help="A filename or pattern to ignore. Can be set multiple times.",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--acl",
        help="The ACL to apply to uploaded files.",
        type=str,
        default=None,
        choices=VALID_ACLS,
    )
    parser.add_argument(
        "-f",
        "--force",
        help="Upload all files whether they are currently up to date on S3 or not",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        help="Show which files would be updated without uploading to S3",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--charset",
        help="The charset header to add to text files",
        default=None,
    )
    parser.add_argument(
        "--gitignore",
        help="Add .gitignore rules to the exclude list",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-p",
        "--processes",
        help="The number of concurrent processes to use for uploading/deleting.",
        type=processes_int,
        default=10,
    )
    parser.add_argument(
        "--delete",
        help="Remove orphaned files from S3",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--confirm",
        help="Confirm each file before deleting. Only works when --delete is set.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--cloudfront-id",
        help=(
            "Specify one or more CloudFront distribution IDs to invalidate "
            "after updating."
        ),
        action="append",
        default=[],
    )
    parser.add_argument(
        "--all",
        help="Upload to all environments",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Print the script version and exit",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-c",
        "--config",
        help="path to config file. Defaults to .d3ploy.json in current directory.",
        type=str,
        default=".d3ploy.json",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        help="Suppress all output. Useful for automated usage.",
        action="store_true",
        default=False,
    )
    args, unknown = parser.parse_known_args()

    if args.quiet:
        QUIET = True

    if pathlib.Path("deploy.json").exists():
        alert(
            (
                "It looks like you have an old version of deploy.json in your project. "
                "Please visit https://github.com/dryan/d3ploy#readme for information "
                "on upgrading."
            ),
            os.EX_CONFIG,
        )

    # load the config file
    config = {}
    config_path = pathlib.Path(args.config)
    if config_path.exists():
        config = json.loads(config_path.read_text())
    else:
        alert(
            (
                f"Config file is missing. Looked for {args.config}. "
                f"See http://dryan.github.io/d3ploy for more information."
            ),
            os.EX_NOINPUT,
        )

    environments = [f"{item}" for item in config.get("environments", {}).keys()]
    defaults = config.get("defaults", {})

    # Check if no environments are configured in the file
    if not environments:
        alert(
            f"No environments found in config file: {args.config}",
            os.EX_NOINPUT,
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
            (
                f'environment{"" if len(invalid_environments) == 1 else "s"} '
                f'{", ".join(invalid_environments)} not found in config. '
                f'Choose from "{", ".join(environments)}"'
            ),
            os.EX_NOINPUT,
        )

    to_deploy = environments if args.all else args.environment

    for environ in to_deploy:
        alert(
            f"Uploading environment {to_deploy.index(environ) + 1:d} "
            f"of {len(to_deploy):d}"
        )
        environ_config = config["environments"][environ]
        if not environ_config.get("excludes", False):
            environ_config["excludes"] = []
        if not defaults.get("excludes", False):
            defaults["excludes"] = []
        excludes = []
        if args.exclude:
            excludes = args.exclude
        else:
            excludes = environ_config.get("exclude", []) + defaults.get("exclude", [])
        excludes.append(args.config)
        sync_files(
            environ,
            bucket_name=args.bucket_name
            or environ_config.get("bucket_name")
            or defaults.get("bucket_name"),
            local_path=args.local_path
            or environ_config.get("local_path")
            or defaults.get("local_path")
            or ".",
            bucket_path=args.bucket_path
            or environ_config.get("bucket_path")
            or defaults.get("bucket_path")
            or "/",
            excludes=excludes,
            acl=args.acl or environ_config.get("acl") or defaults.get("acl"),
            force=args.force or environ_config.get("force") or defaults.get("force"),
            dry_run=args.dry_run,
            charset=args.charset
            or environ_config.get("charset")
            or defaults.get("charset"),
            gitignore=args.gitignore
            or environ_config.get("gitignore")
            or defaults.get("gitignore"),
            processes=args.processes,
            delete=args.delete
            or environ_config.get("delete")
            or defaults.get("delete"),
            confirm=args.confirm,
            cloudfront_id=args.cloudfront_id
            or environ_config.get("cloudfront_id")
            or defaults.get("cloudfront_id")
            or [],
            caches=environ_config.get("caches", {}) or defaults.get("caches", {}),
        )
        display_output()


if __name__ == "__main__":  # pragma: no cover
    colorama_init()
    try:
        check_for_updates()
    except Exception as e:
        if os.environ.get("D3PLOY_DEBUG") == "True":
            raise e
    cli()
