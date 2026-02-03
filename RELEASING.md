# Creating a Release

This guide explains how to create a new release of Backlogia with desktop application builds.

## Automatic Release Process

The GitHub Actions workflows will automatically build executables for Windows, macOS, and Linux when you create a git tag.

### Steps

1. **Update version in CHANGELOG.md**
   ```bash
   # Edit CHANGELOG.md
   # Change [Unreleased] to [1.0.0] - 2026-02-03
   ```

2. **Commit changes**
   ```bash
   git add CHANGELOG.md
   git commit -m "Release v1.0.0"
   git push origin feat-autonomous-program
   ```

3. **Create and push a tag**
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0 - Desktop Edition"
   git push origin v1.0.0
   ```

4. **GitHub Actions will automatically:**
   - Build executables for Windows, macOS, and Linux
   - Create a GitHub Release
   - Upload all build artifacts

5. **Edit the release on GitHub**
   - Go to https://github.com/sam1am/backlogia/releases
   - Find your new release
   - Edit the description using `.github/RELEASE_TEMPLATE.md` as a guide
   - Update {VERSION} placeholders
   - Publish the release

## Manual Build (for testing)

To build locally without creating a release:

```bash
# Windows
python build.py
cd dist
Compress-Archive -Path Backlogia -DestinationPath Backlogia-Windows.zip

# macOS/Linux
python build.py
cd dist
tar -czf Backlogia-$(uname -s).tar.gz Backlogia
```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality (backward compatible)
- **PATCH** version: Bug fixes (backward compatible)

Examples:
- `v1.0.0` - First desktop release
- `v1.1.0` - Add system tray feature
- `v1.1.1` - Fix startup bug

## Checklist Before Release

- [ ] All tests pass locally (`python test_desktop.py`)
- [ ] CHANGELOG.md updated with changes
- [ ] README.md updated if needed
- [ ] Version number follows semver
- [ ] Desktop app tested on target platform
- [ ] No sensitive data in commits (API keys, passwords)

## Troubleshooting

**Build fails on GitHub Actions:**
- Check the Actions tab for error logs
- Verify all dependencies are in requirements.txt
- Test build locally first

**Missing dependencies:**
- Update requirements.txt or requirements-build.txt
- Commit and push changes before tagging

**Release not created:**
- Verify tag starts with `v` (e.g., `v1.0.0`)
- Check GitHub Actions permissions in repository settings
- Ensure `GITHUB_TOKEN` has write permissions
