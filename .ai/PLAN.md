# Plan

Status: **ready**

Goal: release v0.1.2 — hotfix for the ZIP structure bug that prevents the integration
from loading after a HACS update to v0.1.1.

## Root-Cause Analysis

### What was already working
The release workflow already stamps the manifest version correctly:
```yaml
- name: Stamp version into manifest.json
  run: |
    python - <<'EOF'
    data["version"] = "${{ steps.version.outputs.VERSION }}"
    ...
    EOF
```
The manifest inside the distributed ZIP has the correct version. This is NOT the root
cause of the regression.

### Actual root cause — ZIP structure
`hacs.json` gained `"zip_release": true` in commit `6da18a7` (included in v0.1.1).
This changed how HACS downloads the integration: instead of the GitHub source tarball,
it now downloads `endgame_grocery.zip`.

The current build command:
```bash
cd custom_components
zip -r ../endgame_grocery.zip endgame_grocery/
```
produces an archive whose top-level entry is the directory `endgame_grocery/`:
```
endgame_grocery/
  __init__.py
  manifest.json
  api.py
  config_flow.py
  const.py
  todo.py
```

HACS with `zip_release` extracts the ZIP **directly** into
`custom_components/endgame_grocery/`. The result is:
```
custom_components/endgame_grocery/endgame_grocery/__init__.py   ← one level too deep
```

Home Assistant looks for `custom_components/endgame_grocery/__init__.py` and finds
nothing, so the integration is silently skipped on startup.

### Secondary issue — hardcoded version in test
`test_manifest_json` asserts `manifest["version"] == "0.1.0"` unconditionally, so
CI never fails when the in-repo manifest drifts from the expected version.

---

## Scope

### T-001 — fix ZIP build command in release workflow

**Files to change**

| File | Change |
|------|--------|
| `.github/workflows/release.yml` | Change ZIP build step to produce files at archive root |

**What to do**

Replace the `Build ZIP archive` step:

```yaml
# BEFORE (wrong — files nested inside endgame_grocery/)
- name: Build ZIP archive
  run: |
    cd custom_components
    zip -r ../endgame_grocery.zip endgame_grocery/

# AFTER (correct — files at archive root)
- name: Build ZIP archive
  run: |
    cd custom_components/endgame_grocery
    zip -r ../../endgame_grocery.zip .
```

The resulting archive structure will be:
```
__init__.py
manifest.json
api.py
config_flow.py
const.py
todo.py
```

HACS extracts these directly into `custom_components/endgame_grocery/` → correct.

**No change to manifest stamping** — it runs before the ZIP build and remains correct.

---

### T-002 — replace hardcoded version assertion in scaffold test

**Files to change**

| File | Change |
|------|--------|
| `tests/test_scaffold.py` | Replace `assertEqual(manifest["version"], "0.1.0")` with a semver-format check |

**What to do**

Replace the exact-version assertion with a regex check that validates semver format
without locking to a specific value:

```python
import re

# replace:
self.assertEqual(manifest["version"], "0.1.0")

# with:
self.assertRegex(
    manifest["version"],
    r"^\d+\.\d+\.\d+$",
    "manifest version must be a valid semver string",
)
```

---

## Acceptance Criteria

- The ZIP built by the release workflow contains `__init__.py` and `manifest.json`
  at the archive root (verifiable with `unzip -l endgame_grocery.zip`).
- `test_manifest_json` passes without asserting a specific version number.
- All other existing tests continue to pass.
- Syntax check passes for all integration modules.

## Commit message (for commit_task)

```
fix(release): correct ZIP structure so HACS installs integration at the right path
```

## Validation

```
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile custom_components/endgame_grocery/*.py
```
