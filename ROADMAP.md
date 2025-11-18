# D3ploy Briefcase Conversion Roadmap

This roadmap outlines the complete conversion of d3ploy from a traditional Python package to a Briefcase console application with Textual interface.

## Phase 1: Breaking Change Warning Release

### 1.1 Current Version Patch Release

- [x] Update update notification text to warn about upcoming major changes
- [x] Test warning message displays correctly
- [x] Release patch version (4.4.3) to PyPI
- [ ] Monitor user feedback and questions
- [ ] Document migration timeline and what's changing

### 1.2 User Communication

- [ ] Update GitHub README with migration notice
- [ ] Create GitHub issue/discussion about upcoming changes
- [ ] Provide clear timeline for new version
- [ ] Document what will break and how to prepare

## Phase 2: Project Setup & Foundation

### 2.1 Python Version Updates

- [ ] Remove Python 3.9 support (no longer maintained per Python devguide)
- [ ] Update supported versions in pyproject.toml classifiers
- [ ] Update CI/CD testing matrix to remove 3.9
- [ ] Update documentation with new minimum Python version

### 2.2 Briefcase Configuration

- [x] Create initial `briefcase.toml` configuration
- [ ] Install Briefcase and verify setup
- [ ] Test basic Briefcase build process
- [ ] Configure platform-specific settings

### 2.3 Dependencies & Environment

- [ ] Add Textual to dependencies
- [ ] Update `pyproject.toml` with new dependency structure
- [ ] Remove colorama and tqdm from requirements
- [ ] Test dependency resolution

### 2.4 Project Structure Planning

- [ ] Design new modular package structure
- [ ] Plan module responsibilities and interfaces
- [ ] Create placeholder modules and __init__.py files

## Phase 3: Code Refactoring & Modularization

### 3.1 Configuration System

- [ ] Create `d3ploy/config/` module
- [ ] Implement config versioning system
- [ ] Add support for both `d3ploy.json` and `.d3ploy.json`
- [ ] Implement environment variable support
- [ ] Create config migration logic for old formats
- [ ] Add priority system: CLI flags > env vars > config file > defaults

### 2.2 AWS Operations Module

- [ ] Create `d3ploy/aws/` module
- [ ] Extract S3 operations from main file
- [ ] Extract CloudFront operations from main file
- [ ] Maintain boto3 compatibility
- [ ] Add proper error handling and retries

### 2.3 File Synchronization Module

- [ ] Create `d3ploy/sync/` module
- [ ] Extract file discovery logic
- [ ] Extract upload/download logic
- [ ] Extract deletion logic
- [ ] Implement pathspec-based filtering
- [ ] Add gitignore support

### 2.4 Core Application Logic

- [ ] Create `d3ploy/core/` module
- [ ] Extract main application coordination logic
- [ ] Implement proper signal handling
- [ ] Add graceful shutdown mechanisms

## Phase 3: Textual Interface Implementation

### 3.1 Basic UI Components

- [ ] Create `d3ploy/ui/` module
- [ ] Design Textual application structure
- [ ] Implement progress bars to replace tqdm
- [ ] Create status display components
- [ ] Add colored output to replace colorama

### 3.2 Interactive Features

- [ ] Implement confirmation dialogs
- [ ] Add real-time progress updates
- [ ] Create error display components
- [ ] Add update notification UI

### 3.3 CLI Integration

- [ ] Maintain command-line argument compatibility
- [ ] Integrate Textual with argparse
- [ ] Implement quiet mode for automated usage
- [ ] Add proper exit codes and error handling

## Phase 4: Data Management & Standards

### 4.1 App Data Directories

- [ ] Implement platform-specific app data paths
- [ ] Move cache files to standard locations
- [ ] Move log files to standard locations
- [ ] Move temporary files to standard locations
- [ ] Maintain backward compatibility for existing users

### 4.2 Update System Enhancement

- [ ] Modify update checker for new architecture
- [ ] Implement Textual-based update notifications
- [ ] Add breaking change warning system
- [ ] Test PyPI version checking

## Phase 5: Testing & Quality Assurance

### 5.1 Unit Testing

- [ ] Create tests for config module
- [ ] Create tests for AWS operations module
- [ ] Create tests for sync module
- [ ] Create tests for core logic
- [ ] Create tests for UI components (where applicable)
- [ ] Ensure 100% test coverage maintenance

### 5.2 Integration Testing

- [ ] Test Briefcase build process
- [ ] Test cross-platform compatibility
- [ ] Test config migration scenarios
- [ ] Test environment variable handling
- [ ] Test real AWS operations (with mocking)

### 5.3 Performance Testing

- [ ] Benchmark new vs old performance
- [ ] Test memory usage of bundled app
- [ ] Test startup time
- [ ] Test large file synchronization

## Phase 6: Briefcase Build & Distribution

### 6.1 Build Configuration

- [ ] Finalize Briefcase configuration for all platforms
- [ ] Configure app icons and metadata
- [ ] Set up code signing (if needed)
- [ ] Test builds on all target platforms

### 6.2 Distribution Setup

- [ ] Configure GitHub Actions for automated builds
- [ ] Set up PyPI wheel distribution with binaries
- [ ] Configure GitHub releases for direct downloads
- [ ] Test installation from both sources

### 6.3 Documentation Updates

- [ ] Update README.md for new installation methods
- [ ] Update configuration documentation
- [ ] Add migration guide from old version
- [ ] Document new features and breaking changes

## Phase 7: Release Preparation

### 7.1 Breaking Change Warning Release

- [ ] Create patch release (e.g., 4.4.3) with breaking change warning
- [ ] Update existing users about upcoming changes
- [ ] Provide timeline for new version release
- [ ] Ensure clear migration path documentation

### 7.2 Final Release

- [ ] Complete all testing and validation
- [ ] Prepare release notes with full changelog
- [ ] Tag new major version release
- [ ] Deploy to PyPI and GitHub releases
- [ ] Monitor for issues and provide support

## Phase 8: Post-Release

### 8.1 User Support

- [ ] Monitor for bug reports
- [ ] Help users with migration issues
- [ ] Address any platform-specific problems
- [ ] Collect feedback for future improvements

### 8.2 Future Planning

- [ ] Plan custom AWS library to replace boto3
- [ ] Evaluate additional Textual features to implement
- [ ] Consider new features for next release
- [ ] Document lessons learned

---

## Current Status: Phase 2.1 - Python Version Updates

__Next Steps:__

1. Remove Python 3.9 support from pyproject.toml and testing
2. Update version requirements to Python 3.10+ minimum
3. Install Briefcase and verify setup

__Blockers:__ None currently identified

__Notes:__

- Keep AGENTS.md updated with any preference changes
- Each phase should be tested before moving to the next
- Breaking change warning gives users time to prepare
