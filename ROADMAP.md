# ROADMAP

Goal: release v0.1.2 as a hotfix that fixes the integration not loading after a HACS
update from v0.1.0 → v0.1.1.

## Priority 1

Objective: fix broken integration load caused by wrong ZIP structure in the release workflow.

- `zip_release: true` was added to `hacs.json` in v0.1.1, switching HACS from
  source-tarball downloads to a ZIP download.
- The ZIP is built with `endgame_grocery/` as a subdirectory inside the archive.
  HACS extracts ZIP contents directly into `custom_components/endgame_grocery/`,
  so files land one level too deep
  (`custom_components/endgame_grocery/endgame_grocery/__init__.py`).
  HA cannot find `__init__.py` at the expected location and silently skips the integration.
- Fix the release workflow to build the ZIP with integration files at the archive root
  (no `endgame_grocery/` subdirectory), so HACS installs them at the correct path.
- Note: manifest version stamping is already correct — the release workflow stamps the
  tag version into `manifest.json` before building the ZIP.

## Priority 2

Objective: prevent CI from silently accepting a stale manifest version.

- `test_manifest_json` hardcodes `"version": "0.1.0"` and therefore never catches
  version drift in the repository.
- Replace the hardcoded assertion with a semver-format check so the test stays
  meaningful as versions change.
