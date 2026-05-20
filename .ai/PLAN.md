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

---

### T-003 — commit manifest version back to main after release

**Problem**

The release workflow stamps the manifest version only inside the ZIP artifact.
The `manifest.json` in the repository stays permanently at `"0.1.0"`, so the repo
and the distributed ZIP are always out of sync. Anyone reading the source sees a
stale version; the test cannot validate the in-repo version either.

**Approach**

After the ZIP is built and the GitHub Release is created, the workflow configures git,
commits the stamped `manifest.json`, and pushes that commit to `main`.

- The commit must carry `[skip ci]` in its message so the push does not re-trigger
  the CI validation pipeline.
- The workflow already has `permissions: contents: write`, so no extra token is needed.

**Files to change**

| File | Change |
|------|--------|
| `.github/workflows/release.yml` | Add a git-config + commit + push step after the GitHub Release step |

**What to do — step by step**

Add the following step at the end of the `release` job, after `Create GitHub Release`:

```yaml
- name: Commit version bump back to main
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add custom_components/endgame_grocery/manifest.json
    git commit -m "chore(release): bump manifest version to ${{ steps.version.outputs.VERSION }} [skip ci]"
    git push origin HEAD:main
```

**Edge-case notes**

- `[skip ci]` prevents the CI workflow from running on the bot commit (GitHub Actions
  skips workflows when the commit message contains this token).
- The push targets `main` explicitly via `HEAD:main`; the workflow runs on a detached
  tag ref, so the explicit refspec is required.
- If a branch-protection rule requires PR reviews, the `github-actions[bot]` push will
  fail. In that case the workflow must be given bypass rights or the step must use a
  Personal Access Token. This project currently has no branch protection, so the default
  `GITHUB_TOKEN` is sufficient.

---

## Commit messages (for commit_task)

- T-001: `fix(release): correct ZIP structure so HACS installs integration at the right path`
- T-002: `test(scaffold): accept semver manifest versions in scaffold validation`
- T-003: `feat(release): commit stamped manifest version back to main after each release`
- T-004: `fix(release): fetch origin/main before back-merge to avoid push rejection`

---

### T-004 — fix back-merge push rejection

**Root cause**

The release workflow is triggered by a tag push and checks out the repository at
the tag ref (detached HEAD). After the tag is pushed, unrelated commits can land on
`main` (e.g. a PR merge). When the workflow later runs `git push origin HEAD:main`,
Git rejects it because `origin/main` is ahead of the local detached HEAD.

Observed error from the v0.1.2 run (26147018103):
```
! [rejected]  HEAD -> main (fetch first)
error: failed to push some refs to '...'
hint: Updates were rejected because the remote contains work that you do not have locally.
```

**Fix**

Replace the "Commit version bump back to main" step so it:
1. Fetches the current `origin/main`
2. Creates a local branch based on `origin/main`
3. Re-applies the version stamp to `manifest.json` on that branch
4. Commits and pushes — now guaranteed to be a fast-forward

```yaml
- name: Commit version bump back to main
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git fetch origin main
    git checkout -B chore/version-bump origin/main
    python - <<'EOF'
    import json
    from pathlib import Path
    manifest_path = Path("custom_components/endgame_grocery/manifest.json")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["version"] = "${{ steps.version.outputs.VERSION }}"
    manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    EOF
    git add custom_components/endgame_grocery/manifest.json
    git commit -m "chore(release): bump manifest version to ${{ steps.version.outputs.VERSION }} [skip ci]"
    git push origin HEAD:main
```

The version stamp is re-applied on this branch (the working tree reflects
`origin/main` after the checkout, not the tag). The push is now a fast-forward
onto the latest `main`.

**Files to change**

| File | Change |
|------|--------|
| `.github/workflows/release.yml` | Replace "Commit version bump back to main" step with the fetch+checkout+stamp+push version above |
| `tests/test_release_workflow.py` | Update the back-merge step assertion to expect `git fetch origin main` and `git checkout -B chore/version-bump origin/main` before the push |

## Validation

```
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile custom_components/endgame_grocery/*.py
```
