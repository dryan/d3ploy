# Config Version Fixtures

This directory contains sample configuration files for each version of the d3ploy config schema.

## Purpose

These fixtures serve multiple purposes:

1. **Testing**: Ensure migration logic correctly handles all config versions
2. **Documentation**: Show the evolution of config structure over time
3. **Reference**: Provide examples for users upgrading from older versions

## Versions

### v0 (No version field)

- **File**: `v0-config.json`
- **Features**: Original config format with `environments` key
- **Notes**: No explicit version number

### v1 (Version field added)

- **File**: `v1-config.json`
- **Features**: Added `version: 1` field, still uses `environments` key
- **Migration**: v0 → v1 adds version field only

### v2 (Renamed environments to targets)

- **File**: `v2-config.json`
- **Features**: Uses `targets` instead of `environments`
- **Migration**: v1 → v2 renames `environments` → `targets`
- **Current**: This is the current version

## When Adding New Versions

**IMPORTANT**: When introducing a new config version:

1. Create a new `vN-config.json` file in this directory
2. Update this README with the new version's features
3. Add migration tests in `tests/test_config_phase3.py`
4. Update `CURRENT_VERSION` in `d3ploy/config/migration.py`
5. Add migration logic for vN-1 → vN
6. Test both CLI and TUI migration flows
7. Update user-facing documentation (README.md)

## Testing Usage

These fixtures can be loaded in tests:

```python
import json
from pathlib import Path

fixtures_dir = Path(__file__).parent / "fixtures" / "configs"
v0_config = json.loads((fixtures_dir / "v0-config.json").read_text())
```
