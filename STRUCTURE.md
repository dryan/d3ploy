# d3ploy Module Structure Plan

This document outlines the planned modular structure for d3ploy after refactoring from the monolithic `d3ploy.py` file.

## Overview

The new structure separates concerns into focused modules that are easier to test, maintain, and extend. Each module has a clear responsibility and well-defined interfaces.

## Module Organization

```
d3ploy/
├── __init__.py           # Package initialization, version export
├── __main__.py           # Briefcase entry point
├── compat.py            # Temporary compatibility layer (removed in Phase 3)
├── config/              # Configuration management
│   ├── __init__.py
│   ├── loader.py        # Load and parse config files
│   ├── migration.py     # Migrate old config formats
│   └── validator.py     # Validate config structure
├── aws/                 # AWS service operations
│   ├── __init__.py
│   ├── s3.py           # S3 operations (upload, delete, check)
│   └── cloudfront.py   # CloudFront invalidation
├── sync/                # File synchronization logic
│   ├── __init__.py
│   ├── discovery.py    # Find files to sync
│   ├── filters.py      # Exclude patterns, gitignore support
│   └── operations.py   # Upload/delete coordination
├── ui/                  # User interface (Textual)
│   ├── __init__.py
│   ├── app.py          # Main Textual application
│   ├── progress.py     # Progress bars and indicators
│   ├── output.py       # Output formatting and display
│   └── dialogs.py      # Confirmation dialogs
├── core/                # Core application logic
│   ├── __init__.py
│   ├── cli.py          # CLI argument parsing
│   ├── updates.py      # Version checking and notifications
│   └── signals.py      # Signal handling and shutdown
└── utils/               # Utility functions
    ├── __init__.py
    ├── files.py        # File operations and hashing
    └── mimetypes.py    # MIME type detection
```

## Module Responsibilities

### `d3ploy/config/`

**Purpose**: Handle all configuration-related operations.

**Responsibilities**:

- Load config from `d3ploy.json` or `.d3ploy.json`
- Parse and validate config structure
- Support environment variables
- Implement config versioning
- Migrate old config formats to new versions
- Priority system: CLI flags > env vars > config file > defaults

**Key Functions**:

- `load_config(path: Path) -> Config`: Load config from file
- `validate_config(data: dict) -> Config`: Validate and parse
- `migrate_config(old_config: dict) -> dict`: Upgrade old formats
- `get_environment(config: Config, name: str) -> Environment`: Get env settings

**Dependencies**: `pathlib`, `json`, `os` (for env vars)

---

### `d3ploy/aws/`

**Purpose**: Encapsulate all AWS service interactions.

#### `aws/s3.py`

**Responsibilities**:

- S3 resource initialization
- Bucket connection testing
- File upload operations
- File deletion operations
- Check if key exists in bucket
- MD5 hash comparison for file updates

**Key Functions**:

- `get_s3_resource() -> ServiceResource`: Initialize boto3 S3 resource
- `test_bucket_connection(bucket_name: str) -> bool`: Verify access
- `key_exists(bucket: Bucket, key: str) -> bool`: Check key existence
- `upload_file(file: Path, bucket: str, key: str, **options) -> bool`: Upload
- `delete_file(bucket: str, key: str) -> bool`: Delete from S3

**Dependencies**: `boto3`, `botocore`, `hashlib`

#### `aws/cloudfront.py`

**Responsibilities**:

- CloudFront client initialization
- Invalidation creation
- Handle multiple distribution IDs

**Key Functions**:

- `invalidate_distributions(distribution_ids: List[str], paths: List[str]) -> List[str]`: Create invalidations

**Dependencies**: `boto3`

---

### `d3ploy/sync/`

**Purpose**: Handle file synchronization logic.

#### `sync/discovery.py`

**Responsibilities**:

- Recursively find files to sync
- Apply exclude patterns
- Respect `.gitignore` rules
- Calculate file hashes

**Key Functions**:

- `discover_files(path: Path, excludes: List[str], gitignore: bool) -> List[Path]`: Find all files
- `should_exclude(file: Path, patterns: pathspec.PathSpec) -> bool`: Check exclusion
- `get_file_hash(file: Path) -> str`: Calculate MD5 hash

**Dependencies**: `pathlib`, `pathspec`, `hashlib`

#### `sync/filters.py`

**Responsibilities**:

- Build exclude patterns from config and CLI
- Load and parse `.gitignore` files
- Create `pathspec` objects for filtering

**Key Functions**:

- `build_exclude_patterns(excludes: List[str], gitignore: bool) -> pathspec.PathSpec`: Build filter
- `load_gitignore(path: Path) -> List[str]`: Parse gitignore

**Dependencies**: `pathspec`, `pathlib`

#### `sync/operations.py`

**Responsibilities**:

- Coordinate upload/delete operations
- Manage thread pool for concurrent operations
- Track success/failure counts
- Call UI progress updates

**Key Functions**:

- `sync_environment(env: Environment, files: List[Path], **options) -> SyncResult`: Main sync logic
- `upload_batch(files: List[Path], **options) -> int`: Upload with threading
- `delete_orphans(bucket: str, local_files: List[Path], **options) -> int`: Clean S3

**Dependencies**: `concurrent.futures`, `aws/s3.py`, `sync/discovery.py`, `ui/progress.py`

---

### `d3ploy/ui/`

**Purpose**: Provide user interface using Textual.

#### `ui/app.py`

**Responsibilities**:

- Main Textual application class
- Application lifecycle management
- Screen layout and composition

**Key Functions**:

- `D3ployApp(App)`: Main application class
- `run_sync(env: str, **options)`: Execute sync with UI

**Dependencies**: `textual`

#### `ui/progress.py`

**Responsibilities**:

- Progress bar displays
- Status indicators
- Real-time updates during sync

**Key Functions**:

- `ProgressDisplay(Widget)`: Custom progress widget
- `update_progress(current: int, total: int, desc: str)`: Update display

**Dependencies**: `textual`, `rich`

#### `ui/output.py`

**Responsibilities**:

- Format and display messages
- Color coding for different message types
- Quiet mode support
- Error highlighting

**Key Functions**:

- `display_message(text: str, level: MessageLevel)`: Show message
- `display_error(text: str, exit_code: int)`: Show error and exit

**Dependencies**: `textual`, `rich`

#### `ui/dialogs.py`

**Responsibilities**:

- Confirmation dialogs (for delete operations)
- User input prompts
- Modal overlays

**Key Functions**:

- `confirm_delete(file: str) -> bool`: Ask for delete confirmation
- `show_dialog(title: str, message: str) -> bool`: Generic dialog

**Dependencies**: `textual`

---

### `d3ploy/core/`

**Purpose**: Core application coordination and logic.

#### `core/cli.py`

**Responsibilities**:

- Parse command-line arguments
- Merge CLI args with config
- Validate argument combinations
- Entry point for CLI execution

**Key Functions**:

- `parse_args() -> argparse.Namespace`: Parse CLI arguments
- `cli()`: Main CLI entry point (called from `__main__.py`)
- `merge_config_and_args(config: Config, args: Namespace) -> RuntimeConfig`: Combine sources

**Dependencies**: `argparse`, `config/`, `core/updates.py`, `sync/operations.py`

#### `core/updates.py`

**Responsibilities**:

- Check PyPI for updates
- Display update notifications
- Rate-limit update checks (daily)
- Store last check timestamp

**Key Functions**:

- `check_for_updates(version: str) -> Optional[str]`: Check if update available
- `display_update_notification(new_version: str)`: Show update message
- `get_last_check_time() -> int`: Get timestamp of last check
- `save_check_time(timestamp: int)`: Save check timestamp

**Dependencies**: `urllib`, `json`, `packaging.version`, `pathlib`, `platformdirs`

#### `core/signals.py`

**Responsibilities**:

- Handle SIGINT/SIGTERM gracefully
- Coordinate shutdown across threads
- Clean exit codes

**Key Functions**:

- `setup_signal_handlers()`: Register handlers
- `handle_shutdown(signum, frame)`: Graceful shutdown
- `shutdown_requested() -> bool`: Check if shutdown pending

**Dependencies**: `signal`, `sys`, `threading`

---

### `d3ploy/utils/`

**Purpose**: Shared utility functions.

#### `utils/files.py`

**Responsibilities**:

- File hash calculation
- File size formatting
- Path manipulation helpers

**Key Functions**:

- `calculate_md5(file: Path) -> str`: Get MD5 hash
- `format_size(bytes: int) -> str`: Human-readable size
- `normalize_path(path: Path) -> Path`: Normalize path separators

**Dependencies**: `hashlib`, `pathlib`

#### `utils/mimetypes.py`

**Responsibilities**:

- Extended MIME type detection
- Custom MIME type mappings
- Content-Type header generation

**Key Functions**:

- `register_custom_types()`: Add custom MIME types
- `get_content_type(file: Path, charset: Optional[str]) -> str`: Full Content-Type header

**Dependencies**: `mimetypes`, `pathlib`

---

## Data Models

These will be defined using `dataclasses` for type safety:

```python
@dataclass
class Environment:
    """Represents a deployment environment configuration"""
    name: str
    bucket_name: str
    local_path: Path
    bucket_path: str
    excludes: List[str]
    acl: Optional[str]
    cloudfront_ids: List[str]

@dataclass
class Config:
    """Main configuration object"""
    version: int  # Config format version
    environments: Dict[str, Environment]
    defaults: Environment

@dataclass
class SyncResult:
    """Result of a sync operation"""
    uploaded: int
    deleted: int
    skipped: int
    errors: int
    invalidations: List[str]
```

## Migration Strategy

1. **Phase 3.1**: Create module structure and move configuration code

   - Create `config/` module with placeholder functions
   - Extract config loading logic from `cli()`
   - Test that config loading still works

2. **Phase 3.2**: Extract AWS operations

   - Create `aws/` module
   - Move S3 functions to `aws/s3.py`
   - Move CloudFront functions to `aws/cloudfront.py`
   - Update imports in main file

3. **Phase 3.3**: Extract sync operations

   - Create `sync/` module
   - Move file discovery to `sync/discovery.py`
   - Move filtering logic to `sync/filters.py`
   - Move sync coordination to `sync/operations.py`

4. **Phase 3.4**: Implement Textual UI

   - Create `ui/` module
   - Replace compat.py with real Textual widgets
   - Implement progress bars and output
   - Add confirmation dialogs

5. **Phase 3.5**: Extract core logic

   - Create `core/` module
   - Move CLI parsing to `core/cli.py`
   - Move update checking to `core/updates.py`
   - Add signal handling in `core/signals.py`

6. **Phase 3.6**: Create utilities

   - Create `utils/` module
   - Extract file utilities
   - Extract MIME type handling

7. **Phase 3.7**: Final cleanup
   - Remove `d3ploy/d3ploy.py` monolith
   - Remove `compat.py`
   - Update all imports
   - Comprehensive testing

## Testing Strategy

Each module should have corresponding test files:

```
tests/
├── test_config_loader.py
├── test_config_migration.py
├── test_aws_s3.py
├── test_aws_cloudfront.py
├── test_sync_discovery.py
├── test_sync_filters.py
├── test_sync_operations.py
├── test_ui_progress.py
├── test_core_cli.py
├── test_core_updates.py
└── test_utils.py
```

## Benefits of This Structure

1. **Testability**: Each module can be tested in isolation
2. **Maintainability**: Clear separation of concerns
3. **Reusability**: Components can be used independently
4. **Type Safety**: Clear interfaces with type hints
5. **Extensibility**: Easy to add new features to specific modules
6. **Documentation**: Self-documenting through module organization
7. **Briefcase Compatible**: Proper package structure for bundling

## Backward Compatibility

- The `cli()` function in `core/cli.py` will maintain the same behavior
- Config file format will be backward compatible (with migration)
- Command-line arguments remain unchanged
- `__main__.py` entry point ensures proper execution in both modes
