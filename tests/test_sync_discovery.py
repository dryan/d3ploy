"""
Tests for file discovery and sync determination.
"""

import hashlib
from pathlib import Path

from d3ploy.sync import discovery

# Test paths
TESTS_DIR = Path(__file__).parent
FILES_DIR = TESTS_DIR / "files"
PARENT_DIR = TESTS_DIR.parent

# Match the original test excludes - only .gitignore and .gitkeep
EXCLUDES = [".gitignore", ".gitkeep"]

TEST_FILES = [
    Path("tests/files/.d3ploy.json"),  # Config files included by default
    Path("tests/files/.empty-config.json"),
    Path("tests/files/.test-d3ploy"),
    Path("tests/files/css/sample.css"),
    Path("tests/files/dont.ignoreme"),
    Path("tests/files/fonts/open-sans.eot"),
    Path("tests/files/fonts/open-sans.svg"),
    Path("tests/files/fonts/open-sans.ttf"),
    Path("tests/files/fonts/open-sans.woff"),
    Path("tests/files/fonts/open-sans.woff2"),
    Path("tests/files/html/index.html"),
    Path("tests/files/img/32d08f4a5eb10332506ebedbb9bc7257.jpg"),
    Path("tests/files/img/40bb78b1ac031125a6d8466b374962a8.jpg"),
    Path("tests/files/img/6c853ed9dacd5716bc54eb59cec30889.png"),
    Path("tests/files/img/6d939393058de0579fca1bbf10ecff25.gif"),
    Path("tests/files/img/9540743374e1fdb273b6a6ca625eb7a3.png"),
    Path("tests/files/img/c-m1-4bdd87fd0324f0a3d84d6905d17e1731.png"),
    Path("tests/files/img/d22db5be7594c17a18a047ca9264ea0a.jpg"),
    Path("tests/files/img/e6aa0c45a13dd7fc94f7b5451bd89bf4.gif"),
    Path("tests/files/img/f617c7af7f36296a37ddb419b828099c.gif"),
    Path("tests/files/img/http.svg"),
    Path("tests/files/js/sample.js"),
    Path("tests/files/js/sample.mjs"),
    Path("tests/files/sample.json"),
    Path("tests/files/sample.xml"),
]

TEST_FILES_WITH_IGNORED = TEST_FILES + [
    Path("tests/files/js/ignore.js"),
    Path("tests/files/please.ignoreme"),
    Path("tests/files/test.ignore"),
]


def test_no_excludes():
    """Test file discovery with no exclusion patterns."""
    files_list = discovery.discover_files(
        FILES_DIR / "txt",
        excludes=None,
        gitignore=False,
    )
    files_list = [x.relative_to(PARENT_DIR) for x in files_list]
    files_list.sort()
    assert files_list == [Path("tests/files/txt/.gitkeep")]


def test_no_gitignore():
    """Test file discovery without gitignore processing."""
    files_list = discovery.discover_files(
        FILES_DIR,
        excludes=EXCLUDES,
        gitignore=False,
    )
    files_list = [x.relative_to(PARENT_DIR) for x in files_list]
    files_list.sort()
    expected = sorted(TEST_FILES_WITH_IGNORED)
    assert files_list == expected


def test_with_gitignore():
    """Test file discovery with gitignore processing."""
    files_list = discovery.discover_files(
        FILES_DIR,
        excludes=EXCLUDES,
        gitignore=True,
    )
    files_list = [x.relative_to(PARENT_DIR) for x in files_list]
    files_list.sort()
    assert files_list == sorted(TEST_FILES)


def test_single_file_path_no_gitignore():
    """Test discovering a single file without gitignore."""
    files_list = discovery.discover_files(
        FILES_DIR / "test.ignore",
        excludes=EXCLUDES,
        gitignore=False,
    )
    files_list = [x.relative_to(PARENT_DIR) for x in files_list]
    assert files_list == [Path("tests/files/test.ignore")]


def test_single_file_path_with_gitignore():
    """Test discovering a single file with gitignore (file is ignored)."""
    files_list = discovery.discover_files(
        FILES_DIR / "test.ignore",
        excludes=EXCLUDES,
        gitignore=True,
    )
    assert files_list == []


def test_ignored_paths_list():
    """Test file discovery with additional exclusion patterns."""
    files_list = discovery.discover_files(
        FILES_DIR,
        excludes=EXCLUDES + ["index.html"],
    )
    files_list = [x.relative_to(PARENT_DIR) for x in files_list]
    expected = [x for x in TEST_FILES_WITH_IGNORED if not x.match("*/index.html")]
    expected.sort()
    files_list.sort()
    assert files_list == expected


def test_ignored_paths_string():
    """Test file discovery with string exclusion pattern."""
    files_list = discovery.discover_files(
        FILES_DIR,
        excludes="index.html",
    )
    assert FILES_DIR / "html" / "index.html" not in files_list


def test_ignored_paths_string_with_str_path():
    """Test file discovery with string path and exclusion."""
    files_list = discovery.discover_files(
        str(FILES_DIR),
        excludes="index.html",
    )
    assert FILES_DIR / "html" / "index.html" not in files_list


def test_gitignore_files_not_found(capsys, monkeypatch):
    """Test warning when no .gitignore files are found."""
    # Change to txt directory which has no .gitignore
    monkeypatch.chdir(FILES_DIR / "txt")

    discovery.discover_files(
        FILES_DIR / "txt",
        excludes=EXCLUDES,
        gitignore=True,
    )

    # Capture output
    captured = capsys.readouterr()
    # Check for warning message (Rich outputs to stderr for warnings)
    output = captured.out + captured.err
    assert "no .gitignore files were found" in output.lower()


def test_config_file_exclusion():
    """Test that specific config file is excluded when config_file parameter
    is provided."""
    # Without config_file parameter, .d3ploy.json should be included
    files_without_exclusion = discovery.discover_files(
        FILES_DIR,
        excludes=EXCLUDES,
        gitignore=False,
    )
    assert FILES_DIR / ".d3ploy.json" in files_without_exclusion

    # With config_file parameter, .d3ploy.json should be excluded
    files_with_exclusion = discovery.discover_files(
        FILES_DIR,
        excludes=EXCLUDES,
        gitignore=False,
        config_file=FILES_DIR / ".d3ploy.json",
    )
    assert FILES_DIR / ".d3ploy.json" not in files_with_exclusion

    # But other config files should still be included
    assert FILES_DIR / ".empty-config.json" in files_with_exclusion


def test_get_file_hash():
    """Test MD5 hash calculation for a file."""
    # Create a temporary file with known content
    test_file = FILES_DIR / "sample.json"

    # Calculate hash using the function
    result_hash = discovery.get_file_hash(test_file)

    # Verify it's a valid MD5 hex string
    assert len(result_hash) == 32
    assert all(c in "0123456789abcdef" for c in result_hash)

    # Verify it matches manual calculation
    expected_md5 = hashlib.md5()
    with Path(test_file).open("rb") as f:
        expected_md5.update(f.read())
    expected_hash = expected_md5.hexdigest()

    assert result_hash == expected_hash
