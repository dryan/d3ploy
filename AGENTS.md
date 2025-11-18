# AGENTS.md - Development Preferences for d3ploy Briefcase Conversion

This file captures preferences and guidelines for AI agents working on the d3ploy project, specifically for converting it to a Briefcase console application.

## Project Context

- **Current State**: Python CLI tool that syncs files to AWS S3 with multiple environment support
- **Goal**: Convert to standalone Briefcase console app for distribution without dependency management
- **Repository**: <https://github.com/dryan/d3ploy>

## Questions for Project Owner

Please answer the following questions to help guide the development process:

### 1. **Target Platforms & Distribution**

- ✅ **Platforms**: All three (macOS, Windows, Linux)
- ✅ **Distribution**: GitHub releases + PyPI distribution
- ❓ **Architecture requirements**: Intel, ARM, universal binaries?

### 2. **User Experience & Interface**

- ✅ **Breaking changes allowed**: Yes, if they make sense
- ✅ **New features**: Will be added in future releases after this conversion
- ✅ **Interface improvements**: Open to modernizing the CLI experience

### 3. **Configuration & Data**

- ✅ **Config files**: Support both `d3ploy.json` and `.d3ploy.json` in project directory
- ✅ **App data**: Move cache, logs, temp files to standard app data locations
- ✅ **Configuration priority**: CLI flags > environment variables > config file > defaults

### 4. **Dependencies & Bundling**

- ✅ **Minimize dependencies**: Replace colorama with first-party code
- ✅ **Use Textual**: Use <https://textual.textualize.io/> instead of colorama + tqdm
- ✅ **boto3**: Keep for now, replace with custom AWS library in future
- ✅ **Final bundle preference**: Textual for modern TUI experience

### 5. **Development & Testing**

- ✅ **Unified approach**: Pip package distributes Briefcase binary (like ruff/uv)
- ✅ **Single codebase**: One version, different packaging approach
- ✅ **Distribution**: PyPI wheels with binaries + GitHub releases

### 6. **Maintenance & Updates**

- ✅ **Update source**: Continue using PyPI as version source of truth
- ✅ **Update notifications**: Follow Textual interface patterns
- ✅ **Breaking changes**: Release patch version warning about upcoming changes
- ✅ **Config migration**: Auto-detect and migrate old config versions
- ✅ **Config versioning**: Add version property to new config structure

### 7. **Code Organization**

- ✅ **Refactoring allowed**: Yes, prioritize maintainability and testability
- ✅ **Modular structure**: Break apart large d3ploy.py into focused modules
- ✅ **Separation of concerns**: UI, AWS ops, config, file operations in separate modules
- ✅ **Briefcase compatibility**: Structure code to work well with Briefcase and Textual

---

## Development Guidelines

Based on the responses above, here are the guidelines for this conversion:

### Architecture & Code Organization

- **Modular design**: Refactor the monolithic `d3ploy.py` into focused modules:
  - `config/` - Configuration loading, validation, and migration
  - `aws/` - S3 and CloudFront operations (keeping boto3 for now)
  - `ui/` - Textual-based interface components
  - `sync/` - File synchronization logic
  - `core/` - Main application logic and coordination
- **Testability**: Design for easy unit testing of individual components
- **Briefcase structure**: Follow Briefcase app conventions for entry points and packaging

### User Interface & Experience

- **Textual integration**: Replace colorama + tqdm with Textual for modern TUI experience
- **Breaking changes**: Document and implement sensible improvements to CLI
- **Error handling**: Improve error messages and user feedback with Textual's capabilities
- **Progress indication**: Use Textual's rich progress components

### Configuration & Data Management

- **Config files**: Support both `d3ploy.json` and `.d3ploy.json` in project directory
- **Config versioning**: Add `version` property to config structure for migration
- **Auto-migration**: Detect and automatically upgrade old config formats
- **Priority order**: CLI flags > environment variables > config file > defaults
- **App data**: Move cache, logs, temp files to platform-standard app data directories

### Dependencies & Bundling

- **Textual**: Primary UI framework replacing colorama and tqdm
- **boto3**: Keep for now, plan future replacement with custom AWS library
- **Minimize deps**: Replace other dependencies where practical
- **Bundle size**: Optimize for reasonable size while maintaining functionality

### Distribution & Updates

- **Unified approach**: Single codebase, PyPI distributes Briefcase binaries
- **Platform support**: macOS, Windows, Linux binaries
- **GitHub releases**: Direct binary downloads as alternative to PyPI
- **Update checking**: Continue using PyPI as source of truth
- **Breaking change warning**: Release patch version before major changes

### Release Process

- **Semantic versioning**: Continue current approach
- **Git workflow**: Create PR → merge to main → push git tag → GitHub Actions triggers release
- **PyPI automation**: GitHub Actions handles PyPI publishing on tag push  
- **Gitmoji**: Always use gitmoji for commit messages
- **Signed tags**: Always sign git tags for releases
- **Warning release**: Issue patch with breaking change notification
- **Config migration**: Ensure smooth transition for existing users
- **Testing**: Platform-specific testing for binary distributions
- **CI/CD**: Build binaries for all platforms in automated pipeline
