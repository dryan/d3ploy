# D3ploy Distribution Guide

This document describes how to build and distribute d3ploy using both traditional PyPI packages and Briefcase installers.

## Distribution Methods

d3ploy is distributed in two ways:

1. **PyPI packages** - Traditional Python package installation via pip/uv/pipx
2. **Briefcase installers** - Platform-specific standalone installers via GitHub releases

Both methods use the same codebase and version numbering.

## Building Briefcase Installers

### Prerequisites

- Install Briefcase: `uv add --dev briefcase`
- Ensure all dependencies are up to date: `uv sync`

### macOS

#### Building

```bash
# Create the app structure
uv run briefcase create macOS app

# Build the app
uv run briefcase build macOS app

# Package for distribution
uv run briefcase package macOS app --adhoc-sign
```

#### Code Signing

For development and testing, use ad-hoc signing:

```bash
uv run briefcase package macOS app --adhoc-sign
```

For distribution, you need an Apple Developer account and certificate:

1. Obtain an Apple Developer Certificate from https://developer.apple.com
2. Install the certificate in your keychain
3. Sign with your developer identity:
   ```bash
   uv run briefcase package macOS app
   ```
4. When prompted, select your developer identity from the list

**Note**: Ad-hoc signed apps will only run on the machine where they were built. For distribution to other users, you must use a proper Apple Developer certificate.

#### Output

- **App bundle**: `build/d3ploy/macos/app/D3ploy.app`
- **PKG installer**: `dist/D3ploy-{version}.pkg`

### Linux

#### Building

```bash
# Create the app structure
uv run briefcase create linux app

# Build the app
uv run briefcase build linux app

# Package for distribution
uv run briefcase package linux app --adhoc-sign
```

#### Code Signing

Linux apps can be built without signing for most distributions. For commercial distribution:

- **AppImage**: No signing required, but checksums should be provided
- **Flatpak**: Sign with GPG key for official repositories
- **Snap**: Sign with Snapcraft account credentials

For now, we use ad-hoc signing which is sufficient for most Linux distributions.

#### Output

Briefcase can generate multiple formats:
- **AppImage**: Single-file executable
- **System package**: `.deb` or `.rpm` depending on the system

### Windows

#### Building

```bash
# Create the app structure
uv run briefcase create windows app

# Build the app
uv run briefcase build windows app

# Package for distribution
uv run briefcase package windows app
```

#### Code Signing

For Windows distribution:

1. Obtain a code signing certificate from a trusted CA
2. Install the certificate on your Windows machine
3. Briefcase will automatically detect and use the certificate

Without a certificate, Windows will show warnings when users try to run the app.

**Note**: For open-source projects, consider:
- Using SignPath (free for open-source): https://signpath.io
- Azure Code Signing certificate service
- Self-signed certificates for testing only (not recommended for distribution)

#### Output

- **Installer**: `dist/D3ploy-{version}.msi`

## Platform-Specific Architectures

### macOS

Briefcase automatically creates universal binaries that support both:
- **ARM64** (Apple Silicon: M1, M2, M3, etc.)
- **x86_64** (Intel Macs)

### Linux

Build separate installers for:
- **x86_64** (64-bit Intel/AMD)
- **ARM64** (ARM-based systems like Raspberry Pi)

### Windows

Build separate installers for:
- **x86_64** (64-bit Windows)
- **ARM64** (Windows on ARM)

## GitHub Actions Automation

The repository includes GitHub Actions workflows that automatically build installers for all platforms when a new tag is pushed:

```yaml
# .github/workflows/build-installers.yml
# Builds macOS, Linux, and Windows installers
# Uploads to GitHub releases
```

## PyPI Distribution

Traditional Python package distribution continues as before:

```bash
# Build wheels
uv build

# Upload to PyPI (automated via GitHub Actions)
uv publish
```

## Installation Methods

### For Users

**PyPI (Traditional Python)**:
```bash
# Using pip
pip install d3ploy

# Using uv
uv tool install d3ploy

# Using pipx
pipx install d3ploy
```

**Briefcase Installers**:
1. Download the appropriate installer from GitHub releases
2. macOS: Double-click the `.pkg` file and follow the installer
3. Linux: Make the AppImage executable and run, or install the system package
4. Windows: Double-click the `.msi` file and follow the installer

## Testing Distribution

Before releasing:

1. Test PyPI package in a clean virtual environment
2. Test Briefcase installer on each target platform
3. Verify both installation methods produce the same functionality
4. Check that update checking works correctly from both sources

## Version Source of Truth

PyPI remains the source of truth for version information and update checking. The app checks PyPI for new versions regardless of installation method.
