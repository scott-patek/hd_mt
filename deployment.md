# Deployment and versioning

This document covers release automation, versioning, and local packaging commands.

## Workflows (GitHub Actions)

The repo uses three workflows:

- `.github/workflows/version-bump.yml` (manual): updates `APP_VERSION` in `app/metadata.py` and opens a PR.
- `.github/workflows/release-test.yml` (manual): builds prerelease macOS and Windows artifacts from any ref.
- `.github/workflows/release.yml` (tag-driven): builds and publishes production releases for `vX.Y.Z` tags.

## Version source of truth

`APP_VERSION` in `app/metadata.py` is the canonical release version.

## Production release flow

1. Run the Version Bump workflow with target `X.Y.Z`.
2. Merge the generated PR.
3. Create and push tag `vX.Y.Z` on `main`.
4. The release workflow validates:
- tag format is `vX.Y.Z`
- tag commit is on `main`
- tag version matches `APP_VERSION`
5. If validation passes, the workflow publishes:
- `half-deaf-mastering-tool-X.Y.Z-macos.dmg`
- `half-deaf-mastering-tool-X.Y.Z-windows-setup.exe`
- `SHA256SUMS.txt`

## Local packaging helpers

```bash
# Generate release metadata JSON
make release_metadata

# Build macOS app + DMG (macOS only)
make release_macos_dmg

# Build Windows installer EXE (Windows only)
make release_windows_installer
```

## Notes

- Validate release-test output before tagging production releases.
- Keep `APP_VERSION` and tag version in sync to avoid workflow failure.
