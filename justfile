# D3ploy Development Tasks
# A justfile to replace our utility scripts with a modern task runner

# List available tasks
default:
    @just --list

# Check if versions match between pyproject.toml and __init__.py
check-versions:
    #!/usr/bin/env python3
    import pathlib
    import re
    import sys
    import os
    
    # Check __init__.py for version
    init_content = pathlib.Path("d3ploy/__init__.py").read_text()
    init_version = re.search(r'__version__ = "(.+)"', init_content)
    
    pyproject_content = pathlib.Path("pyproject.toml").read_text()
    pyproject_version = re.search(r'version = "(.+)"', pyproject_content)
    
    if not init_version:
        print("Could not find version in d3ploy/__init__.py", file=sys.stderr)
        sys.exit(os.EX_DATAERR)
    
    if not pyproject_version:
        print("Could not find version in pyproject.toml", file=sys.stderr)
        sys.exit(os.EX_DATAERR)
    
    d3ploy_ver = init_version.group(1)
    pyproject_ver = pyproject_version.group(1)
    
    if d3ploy_ver != pyproject_ver:
        print(f"Versions do not match: {d3ploy_ver} != {pyproject_ver}", file=sys.stderr)
        sys.exit(os.EX_DATAERR)
    
    print(f"✅ Versions match: {d3ploy_ver}")

# Bump version (major, minor, or patch)
bump-version version_type="patch" prerelease="false":
    #!/usr/bin/env python3
    import pathlib
    import re
    from packaging.version import Version, parse
    
    version_type = "{{version_type}}"
    prerelease = "{{prerelease}}" == "true"
    
    pyproject_content = pathlib.Path("pyproject.toml").read_text()
    pyproject_version = re.search(r'version = "(.+)"', pyproject_content).group(1)
    pyproject_version = parse(pyproject_version)
    new_version = Version(str(pyproject_version))
    
    match version_type:
        case "major":
            new_version = Version(f'{".".join([str(new_version.major + 1), "0", "0"])}')
        case "minor":
            new_version = Version(
                f'{".".join([str(new_version.major), str(new_version.minor + 1), "0"])}'
            )
        case "patch":
            if pyproject_version.pre and prerelease:
                new_version = Version(
                    f'{".".join([str(new_version.major), str(new_version.minor), str(new_version.micro)])}{new_version.pre[0]}{new_version.pre[1] + 1}'
                )
            else:
                new_version = Version(
                    f'{".".join([str(new_version.major), str(new_version.minor), str(new_version.micro + 1)])}'
                )
    
    if prerelease and not new_version.pre:
        new_version = Version(
            f"{new_version}{new_version.pre[0] or 'a' if new_version.pre else 'a'}{new_version.pre[1] + 1 if new_version.pre else 1}"
        )
    
    if new_version != pyproject_version:
        print(f"Updating version from {pyproject_version} to {new_version}")
        pyproject_content = re.sub(
            r'version = "(.+)"',
            f'version = "{new_version}"',
            pyproject_content,
        )
        pathlib.Path("pyproject.toml").write_text(pyproject_content)
        
        # Update __init__.py
        init_content = pathlib.Path("d3ploy/__init__.py").read_text()
        init_content = re.sub(
            r'__version__ = "(.+)"',
            f'__version__ = "{new_version}"',
            init_content,
        )
        pathlib.Path("d3ploy/__init__.py").write_text(init_content)
    else:
        print(f"Version unchanged: {pyproject_version}")

# Clean and build package
build:
    uv run python -m build
    @echo "✅ Package built"

# Upload package to PyPI
upload: build
    uv run twine upload dist/*
    rm -rf dist
    @echo "✅ Package uploaded to PyPI"

# Run tests
test:
    uv run pytest

# Run tests with coverage
test-coverage:
    uv run pytest --cov=d3ploy --cov-report=html --cov-report=term

# Run linting checks
lint:
    uv run ruff check .

# Fix linting issues
lint-fix:
    uv run ruff check --fix .

# Format code
format:
    uv run ruff format .

# Run type checking
typecheck:
    uv run ty check .

# Run all quality checks
check: lint typecheck test
    @echo "✅ All checks passed"

# Clean build artifacts
clean:
    rm -rf dist/
    rm -rf build/
    rm -rf *.egg-info/
    rm -rf .coverage
    rm -rf htmlcov/
    rm -rf .pytest_cache/
    rm -rf .ruff_cache/
    find . -type d -name __pycache__ -exec rm -rf {} +
    @echo "✅ Cleaned build artifacts"

# Install development dependencies
install:
    uv sync --all-extras
    @echo "✅ Development environment ready"

# Run the development version
run *ARGS:
    uv run python -m d3ploy {{ARGS}}

# Build Briefcase app (development)
briefcase-dev:
    uv run briefcase dev

# Build Briefcase app for distribution
briefcase-build:
    uv run briefcase build

# Package Briefcase app
briefcase-package:
    uv run briefcase package

# Full release workflow
release version_type="patch": (bump-version version_type) (check-versions) upload
    @echo "🚀 Released new {{version_type}} version"