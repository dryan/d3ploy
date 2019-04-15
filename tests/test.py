import argparse
import json
import multiprocessing
import os
import re
import sys
import time
import unittest
import uuid
import warnings
from io import StringIO
from unittest.mock import Mock, patch

import boto3
import botocore

parent_dir = os.path.abspath(
    os.path.dirname(
        os.path.dirname(
            __file__
        )
    )
)
sys.path.append(
    os.path.join(
        parent_dir,
    )
)

from d3ploy import d3ploy  # noqa # isort:skip

TEST_BUCKET = os.getenv(
    'D3PLOY_TEST_BUCKET',
    'd3ploy-tests',
)
TEST_CLOUDFRONT_DISTRIBUTION = os.getenv(
    'D3PLOY_TEST_CLOUDFRONT_DISTRIBUTION',
    'ECVGU5V5GT5GO',
)
TEST_FILES = [
    'tests/files/.d3ploy.json',
    'tests/files/.empty-config.json',
    'tests/files/.test-d3ploy',
    'tests/files/css/sample.css',
    'tests/files/dont.ignoreme',
    'tests/files/fonts/open-sans.eot',
    'tests/files/fonts/open-sans.svg',
    'tests/files/fonts/open-sans.ttf',
    'tests/files/fonts/open-sans.woff',
    'tests/files/fonts/open-sans.woff2',
    'tests/files/html/index.html',
    'tests/files/img/32d08f4a5eb10332506ebedbb9bc7257.jpg',
    'tests/files/img/40bb78b1ac031125a6d8466b374962a8.jpg',
    'tests/files/img/6c853ed9dacd5716bc54eb59cec30889.png',
    'tests/files/img/6d939393058de0579fca1bbf10ecff25.gif',
    'tests/files/img/9540743374e1fdb273b6a6ca625eb7a3.png',
    'tests/files/img/c-m1-4bdd87fd0324f0a3d84d6905d17e1731.png',
    'tests/files/img/d22db5be7594c17a18a047ca9264ea0a.jpg',
    'tests/files/img/e6aa0c45a13dd7fc94f7b5451bd89bf4.gif',
    'tests/files/img/f617c7af7f36296a37ddb419b828099c.gif',
    'tests/files/img/http.svg',
    'tests/files/js/sample.js',
    'tests/files/sample.json',
    'tests/files/sample.xml',
]
TEST_FILES_WITH_IGNORED_FILES = TEST_FILES + [
    'tests/files/js/ignore.js',
    'tests/files/please.ignoreme',
    'tests/files/test.ignore',
]
TEST_FILES.sort()
TEST_FILES_WITH_IGNORED_FILES.sort()
TEST_MIMETYPES = [
    ('css/sample.css', 'text/css'),
    ('fonts/open-sans.eot', 'application/vnd.ms-fontobject'),
    ('fonts/open-sans.svg', 'image/svg+xml'),
    ('fonts/open-sans.ttf', 'font/ttf'),
    ('fonts/open-sans.woff', 'font/woff'),
    ('fonts/open-sans.woff2', 'font/woff2'),
    ('img/32d08f4a5eb10332506ebedbb9bc7257.jpg', 'image/jpeg'),
    ('img/6c853ed9dacd5716bc54eb59cec30889.png', 'image/png'),
    ('img/6d939393058de0579fca1bbf10ecff25.gif', 'image/gif'),
    ('img/http.svg', 'image/svg+xml'),
    ('html/index.html', 'text/html'),
    ('js/sample.js', 'text/javascript'),
    ('sample.json', 'application/json'),
    ('sample.xml', 'application/xml'),
]
ACL_GRANTS = {
    'private': [],
    'public-read': [{'Grantee': {'Type': 'Group', 'URI': 'http://acs.amazonaws.com/groups/global/AllUsers'}, 'Permission': 'READ'}],
    'public-read-write': [{'Grantee': {'Type': 'Group', 'URI': 'http://acs.amazonaws.com/groups/global/AllUsers'}, 'Permission': 'READ'}, {'Grantee': {'Type': 'Group', 'URI': 'http://acs.amazonaws.com/groups/global/AllUsers'}, 'Permission': 'WRITE'}],
    'authenticated-read': [{'Grantee': {'Type': 'Group', 'URI': 'http://acs.amazonaws.com/groups/global/AuthenticatedUsers'}, 'Permission': 'READ'}],
}
EXCLUDES = ['.gitignore', '.gitkeep']
CHARSETS = [None, 'UTF-8', 'ISO-8859-1', 'Windows-1251']


def s3_object_exists(bucket_name, key_name):
    warnings.simplefilter("ignore", ResourceWarning)
    s3 = boto3.resource('s3')
    s3_obj = s3.Object(bucket_name, key_name)
    try:
        s3_obj.load()
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            raise e
    return None


def relative_path(p):
    return os.path.relpath(
        os.path.join(
            parent_dir,
            'tests',
            p,
        )
    )


PREFIX_REGEX = re.compile(
    r'^{}'.format(
        relative_path(
            './files',
        ),
    ),
)


# we need to remove .DS_Store files before testing on macOS to keep tests consistent on other platforms
def clean_ds_store():
    for root, dir_names, file_names in os.walk(relative_path('./')):
        for fn in file_names:
            if fn == '.DS_Store':
                os.unlink(
                    os.path.join(
                        root,
                        fn
                    )
                )


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        clean_ds_store()
        super().setUp()


class S3BucketMixin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s3 = boto3.resource('s3')
        cls.bucket = cls.s3.Bucket(TEST_BUCKET)
        super().setUpClass()

    def setUp(self):
        self.bucket.objects.all().delete()  # clean out the bucket before each test
        super().setUp()

    @classmethod
    def tearDownClass(cls):
        cls.bucket.objects.all().delete()  # clean out the bucket after all tests
        super().tearDownClass()


class TestFileMixin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_file_name = os.path.join(
            relative_path('./files/txt'),
            'test-{}.txt'.format(
                uuid.uuid4().hex
            ),
        )
        cls.destroy_test_file()
        super().setUpClass()

    def setUp(self):
        self.destroy_test_file()
        super().setUp()

    def tearDown(self):
        self.destroy_test_file()
        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        cls.destroy_test_file()
        super().tearDownClass()

    def create_test_file(self):
        with open(self.test_file_name, 'w') as f:
            f.write(uuid.uuid4().hex + '\n')
            f.flush()
            f.close()

    @classmethod
    def destroy_test_file(cls):
        if os.path.exists(cls.test_file_name):
            os.remove(cls.test_file_name)


class MockBuffer:
    value = ''

    def write(self, string):
        self.value += string

    def flush(self):
        pass

    def __repr__(self):
        return self.value


class MockSyncFiles(Mock):

    def __call__(self, env, **kwargs):
        self.configure_mock(env=env)
        print(kwargs)
        self.configure_mock(**kwargs)


class AlertTestCase(BaseTestCase):
    def test_non_error_alerts(self):
        for color in [d3ploy.DEFAULT_COLOR, d3ploy.ALERT_COLOR, d3ploy.ERROR_COLOR, d3ploy.OK_COLOR]:
            with patch('sys.stdout', new=MockBuffer()) as std_out:
                d3ploy.alert(
                    'Testing alert colors',
                    color=color,
                )
                self.assertEqual(
                    std_out.value,
                    '{}Testing alert colors{}\n'.format(
                        color,
                        d3ploy.DEFAULT_COLOR,
                    ),
                )

    def test_non_error_alerts_quieted(self):
        d3ploy.QUIET = True
        with patch('sys.stdout', new=MockBuffer()) as std_out:
            d3ploy.alert(
                'Testing alert colors',
            )
            self.assertEqual(
                std_out.value,
                '',
            )
        d3ploy.QUIET = False

    def test_error_alerts(self):
        with patch('sys.stdout', new=MockBuffer()) as std_out:
            with self.assertRaises(SystemExit) as exception:
                d3ploy.alert(
                    'Testing alert colors',
                    error_code=os.EX_OK,
                )
                self.assertEqual(
                    exception.exception.code,
                    os.EX_OK,
                )
            self.assertEqual(
                std_out.value,
                '{}Testing alert colors{}\n'.format(
                    d3ploy.DEFAULT_COLOR,
                    d3ploy.DEFAULT_COLOR,
                ),
                msg='Testing error code {}'.format(os.EX_OK),
            )
        for error_code in [os.EX_NOINPUT, os.EX_NOUSER, os.EX_CONFIG, os.EX_UNAVAILABLE]:
            with patch('sys.stderr', new=MockBuffer()) as std_err:
                with self.assertRaises(SystemExit) as exception:
                    d3ploy.alert(
                        'Testing alert colors',
                        error_code=error_code,
                    )
                    self.assertEqual(
                        exception.exception.code,
                        error_code,
                    )
                self.assertEqual(
                    std_err.value,
                    '{}Testing alert colors{}\n'.format(
                        d3ploy.ERROR_COLOR,
                        d3ploy.DEFAULT_COLOR,
                    ),
                    msg='Testing error code {}'.format(error_code),
                )

    def test_error_alerts_with_color(self):
        for color in [d3ploy.DEFAULT_COLOR, d3ploy.ALERT_COLOR, d3ploy.ERROR_COLOR, d3ploy.OK_COLOR]:
            with patch('sys.stderr', new=MockBuffer()) as std_err:
                with self.assertRaises(SystemExit) as exception:
                    d3ploy.alert(
                        'Testing alert colors',
                        error_code=os.EX_NOINPUT,
                        color=color,
                    )
                    self.assertEqual(
                        exception.exception.code,
                        os.EX_NOINPUT,
                    )
                self.assertEqual(
                    std_err.value,
                    '{}Testing alert colors{}\n'.format(
                        color,
                        d3ploy.DEFAULT_COLOR,
                    ),
                )


class ProgressBarTestCase(BaseTestCase, S3BucketMixin):
    def test_progress_setup(self):
        try:
            import progressbar
        except ImportError:
            progressbar = None
        bar = d3ploy.progress_setup(num_files=10)
        print(bar)
        if progressbar:
            self.assertIsInstance(
                bar,
                progressbar.ProgressBar,
            )
        else:
            self.assertIsNone(bar)

    def test_progress_setup_quiet(self):
        try:
            import progressbar
        except ImportError:
            progressbar = None
        d3ploy.QUIET = True
        bar = d3ploy.progress_setup(num_files=10)
        self.assertIsNone(bar)
        d3ploy.QUIET = False

    def test_progress_update(self):
        bar = d3ploy.progress_setup(num_files=10)
        if bar is not None:
            current_value = bar.value + 0
            d3ploy.progress_update(
                bar,
                1,
            )
            self.assertEqual(
                current_value + 1,
                bar.value,
            )

    def test_delete_file_bar_update(self):
        bar = d3ploy.progress_setup(num_files=10)
        if bar is not None:
            current_value = bar.value + 0
            d3ploy.delete_file(
                'test.txt',
                self.bucket.name,
                self.s3,
                needs_confirmation=False,
                bar=bar,
            )
            self.assertEqual(
                current_value + 1,
                bar.value,
            )


class DetermineFilesToSyncTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None

    def test_no_gitignore(self):
        files_list = d3ploy.determine_files_to_sync(
            relative_path('./files'),
            EXCLUDES,
            gitignore=False,
        )
        files_list.sort()
        self.assertListEqual(files_list, TEST_FILES_WITH_IGNORED_FILES)

    def test_with_gitignore(self):
        files_list = d3ploy.determine_files_to_sync(
            relative_path('./files'),
            EXCLUDES,
            gitignore=True,
        )
        files_list.sort()
        self.assertListEqual(files_list, TEST_FILES)

    def test_single_file_path_no_gitignore(self):
        files_list = d3ploy.determine_files_to_sync(
            relative_path('./files/test.ignore'),
            EXCLUDES,
            gitignore=False,
        )
        self.assertListEqual(
            files_list,
            [relative_path('./files/test.ignore')],
        )

    def test_single_file_path_with_gitignore(self):
        files_list = d3ploy.determine_files_to_sync(
            relative_path('./files/test.ignore'),
            EXCLUDES,
            gitignore=True,
        )
        self.assertListEqual(
            files_list,
            [],
        )

    def test_ignored_paths_list(self):
        files_list = d3ploy.determine_files_to_sync(
            relative_path('./files'),
            EXCLUDES + ['index.html'],
        )
        expected = [
            x for x in TEST_FILES_WITH_IGNORED_FILES if not x.endswith('index.html')]
        expected.sort()
        files_list.sort()
        self.assertListEqual(
            files_list,
            expected,
        )

    def test_ignored_paths_string(self):
        files_list = d3ploy.determine_files_to_sync(
            relative_path('./files'),
            'index.html',
        )
        self.assertNotIn(
            relative_path('./files/html/index.html'),
            files_list,
        )

    def test_gitignore_files_not_found(self):
        cwd = '{}'.format(os.getcwd())
        os.chdir(relative_path('./files/txt'))
        with patch('sys.stdout', new=MockBuffer()) as std_out:
            d3ploy.determine_files_to_sync(
                relative_path('./files/txt'),
                EXCLUDES,
                gitignore=True,
            )
            self.assertIn(
                'no .gitignore files were found',
                std_out.value,
            )
        os.chdir(cwd)


class CheckForUpdatesTestCase(BaseTestCase, TestFileMixin):
    def setUp(self):
        time.sleep(0.5)
        super().setUp()

    def test_no_existing_file(self):
        result = d3ploy.check_for_updates(
            self.test_file_name,
        )
        self.assertFalse(
            result,
            msg='check_for_updates returns False when there isn\'t a previous check file',
        )

    def test_existing_recent_check(self):
        with open(self.test_file_name, 'w') as f:
            f.write('{:d}'.format(int(time.time()) - 300))
            f.flush()
            f.close()
        result = d3ploy.check_for_updates(
            self.test_file_name,
        )
        self.assertIsNone(
            result,
            msg='check_for_updates returns None when there has been a recent check',
        )

    def test_existing_old_check(self):
        with open(self.test_file_name, 'w') as f:
            f.write('{:d}'.format(int(time.time()) - 100000))
            f.flush()
            f.close()
        result = d3ploy.check_for_updates(
            self.test_file_name,
        )
        self.assertIn(
            result,
            [True, False],
            msg='check_for_updates returns True or False when there hasn\'t been a recent check',
        )

    def test_new_version_available(self):
        result = d3ploy.check_for_updates(
            self.test_file_name,
            '0.0.0',
        )
        self.assertTrue(
            result,
            msg='check_for_updates returns True when a newer version is on pypi.org',
        )


class UploadFileTestCase(
    BaseTestCase,
    S3BucketMixin,
    TestFileMixin,
):
    def test_bucket_path(self):
        for prefix in ['test', 'testing']:
            result = d3ploy.upload_file(
                relative_path('./files/css/sample.css'),
                self.bucket.name,
                self.s3,
                prefix,
                PREFIX_REGEX,
            )
            self.assertEqual(
                result[0],
                '{}/css/sample.css'.format(prefix),
                msg='upload_file returns the correct path',
            )
            self.assertEqual(
                result[1],
                1,
                msg='upload_file returns the correct status',
            )

    def test_acls(self):
        for acl in d3ploy.VALID_ACLS:
            result = d3ploy.upload_file(
                relative_path('./files/css/sample.css'),
                self.bucket.name,
                self.s3,
                'test-acl-{}'.format(acl),
                PREFIX_REGEX,
                acl=acl,
            )
            object_acl = self.s3.ObjectAcl(
                self.bucket.name,
                result[0],
            )
            grants = []
            for grant in object_acl.grants:
                if grant.get('Grantee', {}).get('Type') == 'CanonicalUser':
                    continue  # skip the individual user permissions
                grants.append(grant)
            self.assertListEqual(
                grants,
                ACL_GRANTS.get(acl),
                msg='upload_file sets the correct ACL grants for ACL {}'.format(
                    acl
                ),
            )

    def test_force_update_file(self):
        result_1 = d3ploy.upload_file(
            relative_path('./files/css/sample.css'),
            self.bucket.name,
            self.s3,
            'test-force-upload',
            PREFIX_REGEX,
        )
        result_2 = d3ploy.upload_file(
            relative_path('./files/css/sample.css'),
            self.bucket.name,
            self.s3,
            'test-force-upload',
            PREFIX_REGEX,
            force=True,
        )
        self.assertTrue(
            result_2[1] > 0,
            msg='upload_file force=True overwrites existing file',
        )

    def test_md5_hashing(self):
        with open(self.test_file_name, 'w') as f:
            f.write(uuid.uuid4().hex)
            f.write('\n')
            f.flush()
        result_1 = d3ploy.upload_file(
            self.test_file_name,
            self.bucket.name,
            self.s3,
            'test-md5-hashing',
            PREFIX_REGEX,
        )
        s3_object_1_hash = self.s3.Object(
            self.bucket.name,
            result_1[0],
        ).metadata.get('d3ploy-hash')
        self.assertEqual(
            result_1[1],
            1,
            msg='upload_file correctly uploads a new file',
        )
        result_2 = d3ploy.upload_file(
            self.test_file_name,
            self.bucket.name,
            self.s3,
            'test-md5-hashing',
            PREFIX_REGEX,
        )
        s3_object_2_hash = self.s3.Object(
            self.bucket.name,
            result_2[0],
        ).metadata.get('d3ploy-hash')
        self.assertEqual(
            result_2[1],
            0,
            msg='upload_file correctly doesn\'t upload an unchanged file',
        )
        self.assertEqual(
            s3_object_1_hash,
            s3_object_2_hash,
            msg='upload_file hashes match for original and unchanged file',
        )
        with open(self.test_file_name, 'w') as f:
            f.write(uuid.uuid4().hex)
            f.write('\n')
            f.flush()
        result_3 = d3ploy.upload_file(
            self.test_file_name,
            self.bucket.name,
            self.s3,
            'test-md5-hashing',
            PREFIX_REGEX,
        )
        s3_object_3_hash = self.s3.Object(
            self.bucket.name,
            result_3[0],
        ).metadata.get('d3ploy-hash')
        self.assertEqual(
            result_3[1],
            1,
            msg='upload_file correctly uploads a changed file',
        )
        self.assertNotEqual(
            s3_object_1_hash,
            s3_object_3_hash,
            msg='upload_file hashes do not match for original and changed file',
        )

    def test_dry_run(self):
        result = d3ploy.upload_file(
            relative_path('./files/css/sample.css'),
            self.bucket.name,
            self.s3,
            'test-dry-run',
            PREFIX_REGEX,
            dry_run=True,
        )
        self.assertEqual(
            result[1],
            1,
        )
        self.assertFalse(
            s3_object_exists(
                self.bucket.name,
                result[0],
            ),
            msg='upload_file dry_run=True does not upload the file'
        )

    def test_charset(self):
        for charset in CHARSETS:
            result = d3ploy.upload_file(
                relative_path('./files/html/index.html'),
                self.bucket.name,
                self.s3,
                'test-charset-{}'.format(charset),
                PREFIX_REGEX,
                charset=charset,
            )
            s3_obj = self.s3.Object(
                self.bucket.name,
                result[0],
            )
            if charset:
                self.assertEqual(
                    s3_obj.content_type,
                    'text/html;charset={}'.format(charset),
                )
            else:
                self.assertEqual(
                    s3_obj.content_type,
                    'text/html',
                )

    def test_caches(self):
        for expiration in [0, 86400, 86400 * 30, 86400 * 365]:
            response = d3ploy.upload_file(
                relative_path('./files/css/sample.css'),
                self.bucket.name,
                self.s3,
                'test-cache-{:d}'.format(expiration),
                PREFIX_REGEX,
                caches={
                    'text/css': expiration,
                }
            )
            s3_obj = self.s3.Object(
                self.bucket.name,
                response[0],
            )
            self.assertEqual(
                s3_obj.cache_control,
                'max-age={:d}, public'.format(expiration),
                msg='upload_file sets proper cache-control header for max-age={:d}'.format(
                    expiration),
            )

    def test_mimetypes(self):
        for check in TEST_MIMETYPES:
            result = d3ploy.upload_file(
                relative_path(
                    os.path.join('./files', check[0]),
                ),
                self.bucket.name,
                self.s3,
                'test-mimetypes',
                PREFIX_REGEX,
            )
            try:
                s3_object = self.s3.Object(
                    self.bucket.name,
                    result[0],
                )
            except Exception as e:
                print(result)
                raise e
            self.assertEqual(
                s3_object.content_type,
                check[1],
                msg='upload_file sets the correct mimetype for {} files'.format(
                    check[0].split('.')[-1],
                ),
            )

    @patch('d3ploy.d3ploy.killswitch.is_set', return_value=True)
    def test_upload_with_killswitch_flipped(self, *args):
        result = d3ploy.upload_file(
            relative_path('./files/css/sample.css'),
            self.bucket.name,
            self.s3,
            'test-upload-killswitch',
            PREFIX_REGEX,
        )
        self.assertTupleEqual(
            result,
            ('tests/files/css/sample.css', 0),
            msg='delete_file returns 0 when killswitch.is_set is True',
        )


class DeleteFileTestCase(
    BaseTestCase,
    S3BucketMixin,
    TestFileMixin,
):
    def setUp(self):
        super().setUp()
        self.create_test_file()
        upload_result = d3ploy.upload_file(
            self.test_file_name,
            self.bucket.name,
            self.s3,
            'test-delete-dry-run',
            PREFIX_REGEX,
        )
        self.assertEqual(
            upload_result[1],
            1,
            msg='delete_file uploading file worked',
        )
        self.assertTrue(
            s3_object_exists(
                self.bucket.name,
                upload_result[0],
            ),
            msg='delete_file uploading file worked',
        )
        self.uploaded_file = upload_result[0]

    def tearDown(self):
        if s3_object_exists(self.bucket.name, self.uploaded_file):
            self.s3.Object(
                self.bucket.name,
                self.uploaded_file,
            ).delete()

    def test_dry_run(self, *args):
        result = d3ploy.delete_file(
            self.uploaded_file,
            self.bucket.name,
            self.s3,
            dry_run=True,
        )
        self.assertEqual(
            result,
            1,
            msg='delete_file dry_run=True returns 1',
        )
        self.assertTrue(
            s3_object_exists(
                self.bucket.name,
                self.uploaded_file,
            ),
            msg='delete_file dry_run=True did not delete the file',
        )

    def test_deletion(self):
        result = d3ploy.delete_file(
            self.uploaded_file,
            self.bucket.name,
            self.s3,
        )
        self.assertEqual(
            result,
            1,
            msg='delete_file returns 1',
        )
        self.assertFalse(
            s3_object_exists(
                self.bucket.name,
                self.uploaded_file,
            ),
            msg='delete_file did delete the file',
        )

    @patch('d3ploy.d3ploy.get_confirmation', return_value=True)
    def test_confirmation_affirmative(self, *args):
        result = d3ploy.delete_file(
            self.uploaded_file,
            self.bucket.name,
            self.s3,
            needs_confirmation=True,
        )
        self.assertEqual(
            result,
            1,
            msg='delete_file needs_confirmation=True returns 1 when get_confirmation is True',
        )
        self.assertFalse(
            s3_object_exists(
                self.bucket.name,
                self.uploaded_file,
            ),
            msg='delete_file needs_confirmation=True did delete the file when get_confirmation is True',
        )

    @patch('d3ploy.d3ploy.get_confirmation', return_value=False)
    def test_confirmation_negative(self, *args):
        result = d3ploy.delete_file(
            self.uploaded_file,
            self.bucket.name,
            self.s3,
            needs_confirmation=True,
        )
        self.assertEqual(
            result,
            0,
            msg='delete_file needs_confirmation=True returns 0 when get_confirmation is False',
        )
        self.assertTrue(
            s3_object_exists(
                self.bucket.name,
                self.uploaded_file,
            ),
            msg='delete_file needs_confirmation=True did not delete the file when get_confirmation is True',
        )

    @patch('d3ploy.d3ploy.killswitch.is_set', return_value=True)
    def test_deletion_with_killswitch_flipped(self, *args):
        result = d3ploy.delete_file(
            self.uploaded_file,
            self.bucket.name,
            self.s3,
        )
        self.assertEqual(
            result,
            0,
            msg='delete_file returns 0 when killswitch.is_set is True',
        )


class InvalidateCloudfrontTestCase(BaseTestCase):
    def test_dry_run(self):
        response = d3ploy.invalidate_cloudfront(
            TEST_CLOUDFRONT_DISTRIBUTION,
            'test',
            dry_run=True,
        )
        self.assertListEqual(
            response,
            [],
            msg='invalidate_cloudfront dry_run=True does not send API calls',
        )

    def test_invalidation(self):
        response = d3ploy.invalidate_cloudfront(
            TEST_CLOUDFRONT_DISTRIBUTION,
            'test',
        )
        self.assertEqual(
            len(response),
            1,
            msg='invalidate_cloudfront returns 1 invalidation ID',
        )


class SyncFilesTestCase(
    BaseTestCase,
    S3BucketMixin,
    TestFileMixin,
):
    def test_bucket_path(self):
        for prefix in ['test', 'testing']:
            d3ploy.sync_files(
                'test',
                local_path=relative_path('./files/css'),
                bucket_name=self.bucket.name,
                bucket_path='sync_files/{}'.format(prefix),
                excludes=EXCLUDES,
            )
            self.assertTrue(
                s3_object_exists(
                    self.bucket.name,
                    'sync_files/{}/sample.css'.format(prefix),
                ),
                msg='sync_files puts files in the correct bucket path',
            )

    def test_acls(self):
        for acl in d3ploy.VALID_ACLS:
            d3ploy.sync_files(
                'test',
                local_path=relative_path('./files/css'),
                bucket_name=self.bucket.name,
                bucket_path='sync_files/test-acl-{}'.format(acl),
                excludes=EXCLUDES,
                acl=acl,
            )
            object_acl = self.s3.ObjectAcl(
                self.bucket.name,
                'sync_files/test-acl-{}/sample.css'.format(acl),
            )
            grants = []
            for grant in object_acl.grants:
                if grant.get('Grantee', {}).get('Type') == 'CanonicalUser':
                    continue  # skip the individual user permissions
                grants.append(grant)
            self.assertListEqual(
                grants,
                ACL_GRANTS.get(acl),
                msg='sync_files sets the correct ACL grants for ACL {}'.format(
                    acl
                ),
            )

    def test_md5_hashing(self):
        with open(self.test_file_name, 'w') as f:
            f.write(uuid.uuid4().hex)
            f.write('\n')
            f.flush()
        d3ploy.sync_files(
            'test',
            local_path=relative_path('./files/txt'),
            bucket_name=self.bucket.name,
            bucket_path='sync_files/test-md5-hashing',
            excludes=EXCLUDES,
        )
        s3_object_1_hash = self.s3.Object(
            self.bucket.name,
            'sync_files/test-md5-hashing/{}'.format(
                os.path.basename(self.test_file_name),
            ),
        ).metadata.get('d3ploy-hash')
        d3ploy.sync_files(
            'test',
            local_path=relative_path('./files/txt'),
            bucket_name=self.bucket.name,
            bucket_path='sync_files/test-md5-hashing',
            excludes=EXCLUDES,
        )
        s3_object_2_hash = self.s3.Object(
            self.bucket.name,
            'sync_files/test-md5-hashing/{}'.format(
                os.path.basename(self.test_file_name),
            ),
        ).metadata.get('d3ploy-hash')
        self.assertEqual(
            s3_object_1_hash,
            s3_object_2_hash,
            msg='sync_files hashes match for original and unchanged file',
        )
        with open(self.test_file_name, 'w') as f:
            f.write(uuid.uuid4().hex)
            f.write('\n')
            f.flush()
        d3ploy.sync_files(
            'test',
            local_path=relative_path('./files/txt'),
            bucket_name=self.bucket.name,
            bucket_path='sync_files/test-md5-hashing',
            excludes=EXCLUDES,
        )
        s3_object_3_hash = self.s3.Object(
            self.bucket.name,
            'sync_files/test-md5-hashing/{}'.format(
                os.path.basename(self.test_file_name),
            ),
        ).metadata.get('d3ploy-hash')
        self.assertNotEqual(
            s3_object_1_hash,
            s3_object_3_hash,
            msg='sync_files hashes do not match for original and changed file',
        )

    def test_dry_run(self):
        d3ploy.sync_files(
            'test',
            local_path=relative_path('./files/css'),
            bucket_name=self.bucket.name,
            bucket_path='sync_files/test-dry-run',
            excludes=EXCLUDES,
            dry_run=True,
        )
        self.assertFalse(
            s3_object_exists(
                self.bucket.name,
                'sync_files/test-dry-run/sample.css',
            ),
            msg='sync_files dry_run=True does not upload the file'
        )

    def test_charset(self):
        for charset in [None, 'UTF-8', 'ISO-8859-1', 'Windows-1251']:
            d3ploy.sync_files(
                'test',
                excludes=EXCLUDES,
                local_path=relative_path('./files/html'),
                bucket_name=self.bucket.name,
                bucket_path='sync_files/test-charset-{}'.format(
                    charset or 'none',
                ),
                charset=charset,
            )
            s3_obj = self.s3.Object(
                self.bucket.name,
                'sync_files/test-charset-{}/index.html'.format(
                    charset or 'none'
                ),
            )
            if charset:
                self.assertEqual(
                    s3_obj.content_type,
                    'text/html;charset={}'.format(charset),
                )
            else:
                self.assertEqual(
                    s3_obj.content_type,
                    'text/html',
                )

    def test_caches(self):
        for expiration in [0, 86400, 86400 * 30, 86400 * 365]:
            d3ploy.sync_files(
                'test',
                local_path=relative_path('./files/css'),
                bucket_name=self.bucket.name,
                bucket_path='sync_files/test-cache-{:d}'.format(expiration),
                excludes=EXCLUDES,
                caches={
                    'text/css': expiration,
                }
            )
            s3_obj = self.s3.Object(
                self.bucket.name,
                'sync_files/test-cache-{:d}/sample.css'.format(expiration),
            )
            self.assertEqual(
                s3_obj.cache_control,
                'max-age={:d}, public'.format(expiration),
                msg='sync_files sets proper cache-control header for max-age={:d}'.format(
                    expiration),
            )

    def test_mimetypes(self):
        d3ploy.sync_files(
            'test',
            local_path=relative_path('./files'),
            bucket_name=self.bucket.name,
            bucket_path='sync_files/test-mimetypes',
            excludes=EXCLUDES,
        )
        for check in TEST_MIMETYPES:
            s3_object = self.s3.Object(
                self.bucket.name,
                'sync_files/test-mimetypes/{}'.format(check[0]),
            )
            self.assertEqual(
                s3_object.content_type,
                check[1],
                msg='sync_files sets the correct mimetype for {} files'.format(
                    check[0].split('.')[-1],
                ),
            )

    def test_multiple_processes(self):
        d3ploy.sync_files(
            'test',
            local_path=relative_path('./files'),
            bucket_name=self.bucket.name,
            bucket_path='sync_files/test-multiple-processes',
            excludes=EXCLUDES,
            processes=10,
            gitignore=True,
        )
        passed = 0
        for fn in TEST_FILES:
            if s3_object_exists(self.bucket.name, 'sync_files/test-multiple-processes/{}'.format(fn.replace('tests/files/', ''))):
                passed += 1
        self.assertEqual(
            passed,
            len(TEST_FILES),
        )

    def test_deleting_files(self):
        self.create_test_file()
        self.assertTrue(os.path.exists(self.test_file_name))
        uploaded_file = d3ploy.upload_file(
            self.test_file_name,
            self.bucket.name,
            self.s3,
            'sync_files/test-deleting',
            PREFIX_REGEX,
        )
        self.destroy_test_file()
        self.assertFalse(os.path.exists(self.test_file_name))
        self.assertTrue(
            s3_object_exists(
                self.bucket.name,
                uploaded_file[0],
            )
        )
        d3ploy.sync_files(
            'test',
            local_path=relative_path('./files'),
            bucket_name=self.bucket.name,
            bucket_path='sync_files/test-deleting',
            excludes=EXCLUDES,
            processes=10,
            gitignore=True,
            delete=True,
        )
        self.assertFalse(
            s3_object_exists(
                self.bucket.name,
                uploaded_file[0],
            )
        )

    def test_deleting_files_single_process(self):
        self.create_test_file()
        self.assertTrue(os.path.exists(self.test_file_name))
        uploaded_file = d3ploy.upload_file(
            self.test_file_name,
            self.bucket.name,
            self.s3,
            'sync_files/test-deleting-single-process',
            PREFIX_REGEX,
        )
        self.destroy_test_file()
        self.assertFalse(os.path.exists(self.test_file_name))
        self.assertTrue(
            s3_object_exists(
                self.bucket.name,
                uploaded_file[0],
            )
        )
        outcome = d3ploy.sync_files(
            'test',
            local_path=relative_path('./files'),
            bucket_name=self.bucket.name,
            bucket_path='sync_files/test-deleting-single-process',
            excludes=EXCLUDES,
            processes=1,
            gitignore=True,
            delete=True,
        )
        self.assertFalse(
            s3_object_exists(
                self.bucket.name,
                uploaded_file[0],
            )
        )
        self.assertGreaterEqual(
            outcome['deleted'],
            1,
        )

    @patch('d3ploy.d3ploy.get_confirmation', return_value=True)
    def test_deleting_files_with_confirmation(self, *args):
        self.create_test_file()
        self.assertTrue(os.path.exists(self.test_file_name))
        uploaded_file = d3ploy.upload_file(
            self.test_file_name,
            self.bucket.name,
            self.s3,
            'sync_files/test-deleting',
            PREFIX_REGEX,
        )
        self.destroy_test_file()
        self.assertTrue(
            s3_object_exists(
                self.bucket.name,
                uploaded_file[0],
            )
        )
        d3ploy.sync_files(
            'test',
            local_path=relative_path('./files'),
            bucket_name=self.bucket.name,
            bucket_path='sync_files/test-deleting',
            excludes=EXCLUDES,
            processes=10,
            gitignore=True,
            delete=True,
            confirm=True,
        )
        self.assertFalse(
            s3_object_exists(
                self.bucket.name,
                uploaded_file[0],
            )
        )

    @patch('d3ploy.d3ploy.get_confirmation', return_value=False)
    def test_deleting_files_with_confirmation_denied(self, *args):
        self.create_test_file()
        self.assertTrue(os.path.exists(self.test_file_name))
        uploaded_file = d3ploy.upload_file(
            self.test_file_name,
            self.bucket.name,
            self.s3,
            'sync_files/test-deleting',
            PREFIX_REGEX,
        )
        self.assertTrue(
            s3_object_exists(
                self.bucket.name,
                uploaded_file[0],
            )
        )
        self.destroy_test_file()
        d3ploy.sync_files(
            'test',
            local_path=relative_path('./files'),
            bucket_name=self.bucket.name,
            bucket_path='sync_files/test-deleting',
            excludes=EXCLUDES,
            processes=10,
            gitignore=True,
            delete=True,
            confirm=True,
        )
        self.assertTrue(
            s3_object_exists(
                self.bucket.name,
                uploaded_file[0],
            )
        )

    def test_no_bucket_name(self):
        with self.assertRaises(SystemExit) as exception:
            d3ploy.sync_files(
                'test',
            )
            self.assertEqual(
                exception.exception.code,
                os.EX_NOINPUT,
            )

    def test_cloudfront_id(self):
        for distro_ids in [[TEST_CLOUDFRONT_DISTRIBUTION], []]:
            outcome = d3ploy.sync_files(
                'test',
                local_path=relative_path('./files/html'),
                bucket_name=self.bucket.name,
                bucket_path='sync_files/test-cloudfront-id',
                excludes=EXCLUDES,
                cloudfront_id=distro_ids,
            )
            self.assertEqual(
                outcome['invalidated'],
                len(distro_ids),
            )


class CLITestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        cls.cwd = os.getcwd()

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.cwd)

    def setUp(self):
        super().setUp()
        os.chdir(relative_path('./files'))
        self.patcher = patch('d3ploy.d3ploy.sync_files', new=MockSyncFiles())
        self.sync_files = self.patcher.start()

    def tearDown(self):
        super().tearDown()
        self.patcher.stop()

    def test_version(self):
        for testargs in [['-v'], ['--version']]:
            with patch.object(sys, 'argv', ['d3ploy'] + testargs):
                with patch('sys.stdout', new=MockBuffer()) as std_out:
                    with self.assertRaises(SystemExit) as exception:
                        d3ploy.cli()
                        self.assertEqual(
                            exception.exception.code,
                            os.EX_OK,
                        )
                        output = std_out.value.replace(
                            'checking for update', '')
                        output = output.split('\n')
                        output = [x.strip() for x in output if x]
                        output = '\n'.join(output)
                        self.assertEqual(
                            output,
                            'd3ploy {}'.format(d3ploy.VERSION),
                        )

    def test_environment_argument(self):
        with patch.object(sys, 'argv', ['d3ploy', 'test']):
            d3ploy.cli()
            self.assertEqual(
                self.sync_files.env,
                'test',
            )

        with patch.object(sys, 'argv', ['d3ploy', 'test', 'prod']):
            d3ploy.cli()
            self.assertEqual(
                self.sync_files.env,
                'prod',
            )

        with patch.object(sys, 'argv', ['d3ploy']):
            with self.assertRaises(SystemExit) as exception:
                d3ploy.cli()
                self.assertEqual(
                    exception.exception.code,
                    os.EX_NOINPUT,
                )

    def test_bucket_name(self):
        # test passing the variable to the cli
        with patch.object(sys, 'argv', ['d3ploy', 'test', '--bucket-name', TEST_BUCKET + '-foo']):
            d3ploy.cli()
            self.assertEqual(
                self.sync_files.bucket_name,
                TEST_BUCKET + '-foo',
            )

        # test getting the variable from the config file
        with patch.object(sys, 'argv', ['d3ploy', 'test']):
            d3ploy.cli()
            self.assertEqual(
                self.sync_files.bucket_name,
                TEST_BUCKET,
            )

    def test_local_path(self):
        # test passing the variable to the cli
        with patch.object(sys, 'argv', ['d3ploy', 'test', '--local-path', './tests/']):
            d3ploy.cli()
            self.assertEqual(
                self.sync_files.local_path,
                './tests/',
            )

        # test getting the variable from the config file
        with patch.object(sys, 'argv', ['d3ploy', 'test']):
            d3ploy.cli()
            self.assertEqual(
                self.sync_files.local_path,
                '.',
            )

    def test_bucket_path(self):
        # test passing the variable to the cli
        with patch.object(sys, 'argv', ['d3ploy', 'test', '--bucket-path', '/tests/']):
            d3ploy.cli()
            self.assertEqual(
                self.sync_files.bucket_path,
                '/tests/',
            )

        # test getting the variable from the config file
        with patch.object(sys, 'argv', ['d3ploy', 'test']):
            d3ploy.cli()
            self.assertEqual(
                self.sync_files.bucket_path,
                '/test/',
            )

    def test_exclude(self):
        # test passing the variable to the cli
        with patch.object(sys, 'argv', ['d3ploy', 'test', '--exclude', '.gitkeep']):
            d3ploy.cli()
            self.sync_files.excludes.sort()
            expected = [
                '.gitkeep',
                '.d3ploy.json',
            ]
            expected.sort()
            self.assertListEqual(
                self.sync_files.excludes,
                expected,
            )

        # test passing multiple variables to the cli
        with patch.object(sys, 'argv', ['d3ploy', 'test', '--exclude', '.gitkeep', '--exclude', 'foo']):
            d3ploy.cli()
            self.sync_files.excludes.sort()
            expected = [
                '.gitkeep',
                'foo',
                '.d3ploy.json',
            ]
            expected.sort()
            self.assertListEqual(
                self.sync_files.excludes,
                expected,
            )

        # test getting the variable from the config file
        with patch.object(sys, 'argv', ['d3ploy', 'prod']):
            d3ploy.cli()
            self.sync_files.excludes.sort()
            expected = [
                '.gitignore',
                '.gitkeep',
                '.d3ploy.json',
            ]
            expected.sort()
            self.assertEqual(
                self.sync_files.excludes,
                expected,
            )

    def test_acl(self):
        # test passing the variable to the cli
        for acl in d3ploy.VALID_ACLS:
            with patch.object(sys, 'argv', ['d3ploy', 'test', '--acl', acl]):
                d3ploy.cli()
                self.assertEqual(
                    self.sync_files.acl,
                    acl,
                )

        # test passing no variable to the cli
        with patch.object(sys, 'argv', ['d3ploy', 'test']):
            d3ploy.cli()
            self.assertEqual(
                self.sync_files.acl,
                'public-read',
            )

    def test_force(self):
        for testargs in [['-f'], ['--force'], []]:
            with patch.object(sys, 'argv', ['d3ploy', 'test'] + testargs):
                d3ploy.cli()
                if testargs:
                    self.assertTrue(
                        self.sync_files.force,
                    )
                else:
                    self.assertFalse(
                        self.sync_files.force,
                    )

    def test_dry_run(self):
        for testargs in [['-n'], ['--dry-run'], []]:
            with patch.object(sys, 'argv', ['d3ploy', 'test'] + testargs):
                d3ploy.cli()
                if testargs:
                    self.assertTrue(
                        self.sync_files.dry_run,
                    )
                else:
                    self.assertFalse(
                        self.sync_files.dry_run,
                    )

    def test_charset(self):
        for charset in CHARSETS:
            with patch.object(sys, 'argv', ['d3ploy', 'test', '--charset', charset]):
                d3ploy.cli()
                if charset:
                    self.assertEqual(
                        self.sync_files.charset,
                        charset,
                    )
                else:
                    self.assertFalse(
                        self.sync_files.charset,
                    )

    def test_gitignore(self):
        for testargs in [['--gitignore'], []]:
            with patch.object(sys, 'argv', ['d3ploy', 'test'] + testargs):
                d3ploy.cli()
                if testargs:
                    self.assertTrue(
                        self.sync_files.gitignore,
                    )
                else:
                    self.assertFalse(
                        self.sync_files.gitignore,
                    )

    def test_processes(self):
        for testargs in [['-p'], ['--processes']]:
            for count in [1, 5, 10]:
                with patch.object(sys, 'argv', ['d3ploy', 'test'] + testargs + [str(count)]):
                    d3ploy.cli()
                    self.assertEqual(
                        self.sync_files.processes,
                        count,
                    )

        with patch.object(sys, 'argv', ['d3ploy', 'test']):
            d3ploy.cli()
            self.assertEqual(
                self.sync_files.processes,
                10,
            )

    def test_delete(self):
        for testargs in [['--delete'], []]:
            with patch.object(sys, 'argv', ['d3ploy', 'test'] + testargs):
                d3ploy.cli()
                if testargs:
                    self.assertTrue(
                        self.sync_files.delete,
                    )
                else:
                    self.assertFalse(
                        self.sync_files.delete,
                    )

    def test_confirm(self):
        for testargs in [['--confirm'], []]:
            with patch.object(sys, 'argv', ['d3ploy', 'test'] + testargs):
                d3ploy.cli()
                if testargs:
                    self.assertTrue(
                        self.sync_files.confirm,
                    )
                else:
                    self.assertFalse(
                        self.sync_files.confirm,
                    )

    def test_cloudfront_id(self):
        for distro_ids in [[TEST_CLOUDFRONT_DISTRIBUTION], [], [TEST_CLOUDFRONT_DISTRIBUTION, TEST_CLOUDFRONT_DISTRIBUTION + '1']]:
            distro_ids.sort()
            testargs = []
            for distro_id in distro_ids:
                testargs.append('--cloudfront-id')
                testargs.append(distro_id)
            with patch.object(sys, 'argv', ['d3ploy', 'test'] + testargs):
                d3ploy.cli()
                self.sync_files.cloudfront_id.sort()
                self.assertListEqual(
                    self.sync_files.cloudfront_id,
                    distro_ids,
                )

    def test_all(self):
        with patch.object(sys, 'argv', ['d3ploy', '--all']):
            d3ploy.cli()
            self.assertIn(
                self.sync_files.env,
                ['test', 'prod'],
            )

    def test_config(self):
        # test that a non default config file location works
        with patch.object(sys, 'argv', ['d3ploy', 'prod', '-c', '.test-d3ploy']):
            d3ploy.cli()
            self.assertEqual(
                self.sync_files.bucket_path,
                '/alt-config/',
            )

        # test that a non existant config file raises an error
        with patch.object(sys, 'argv', ['d3ploy', 'test', '-c', '.test-d3ploy.json']):
            with self.assertRaises(SystemExit) as exception:
                d3ploy.cli()
                self.assertEqual(
                    exception.exception.code,
                    os.EX_NOINPUT,
                )

        # test that an empty config file raises an error
        with patch.object(sys, 'argv', ['d3ploy', 'test', '-c', '.empty-config.json']):
            with self.assertRaises(SystemExit) as exception:
                d3ploy.cli()
                self.assertEqual(
                    exception.exception.code,
                    os.EX_NOINPUT,
                )

    def test_quiet(self):
        with patch.object(sys, 'argv', ['d3ploy', 'test']):
            d3ploy.QUIET = False
            d3ploy.cli()
            self.assertFalse(
                d3ploy.QUIET,
            )

        with patch.object(sys, 'argv', ['d3ploy', 'test', '-q']):
            d3ploy.QUIET = False
            d3ploy.cli()
            self.assertTrue(
                d3ploy.QUIET,
            )

        with patch.object(sys, 'argv', ['d3ploy', 'test', '--quiet']):
            d3ploy.QUIET = False
            d3ploy.cli()
            self.assertTrue(
                d3ploy.QUIET,
            )

        d3ploy.QUIET = False

    def test_old_config_check(self):
        with open('deploy.json', 'w') as f:
            f.write('\n')
            f.flush()
        with self.assertRaises(SystemExit) as exception:
            d3ploy.cli()
            self.assertTrue(
                exception.exception.code,
                os.EX_CONFIG,
            )
        os.unlink('deploy.json')

    def test_positive_int(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            d3ploy.processes_int(0)
        with self.assertRaises(argparse.ArgumentTypeError):
            d3ploy.processes_int(-10)
        self.assertEqual(
            d3ploy.processes_int(1),
            1,
        )
        self.assertEqual(
            d3ploy.processes_int(10),
            10,
        )
        self.assertEqual(
            d3ploy.processes_int(50),
            50,
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            d3ploy.processes_int(51)


if __name__ == '__main__':
    unittest.main(
        buffer=True,
        verbosity=2,
    )
