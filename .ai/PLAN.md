# Plan

Status: **ready_for_implement**

Goal: Publish the Endgame Grocery integration with HACS version selection, a CI pipeline, and a production-quality README.

Source of truth: `ROADMAP.md` (Priority 2 section)

---

## Scope

Three independent tasks that can be implemented sequentially:

| Task | Files | Depends on |
|------|-------|------------|
| T-006 | `.github/workflows/ci.yml` | — |
| T-007 | `.github/workflows/release.yml` | — |
| T-008 | `README.md`, `custom_components/endgame_grocery/images/icon.png` | T-007 (badge URL uses repo release data) |

---

## Acceptance Criteria

- CI workflow runs and passes on every PR/push to `main` (syntax + tests + HACS Action).
- Pushing a `v*.*.*` tag creates a GitHub Release with a `endgame_grocery.zip` asset containing the component. The version in the bundled `manifest.json` matches the tag.
- README renders on GitHub: logo and CI badge visible, HACS install badge present, installation steps accurate, AI-workflow section removed.
- `custom_components/endgame_grocery/images/icon.png` exists and is a valid PNG (copy of `assets/endgame_grocery_logo.png`).

---

## Implementation Phases

### Phase 1 — T-006: CI Pipeline

**File:** `.github/workflows/ci.yml`

**Trigger:** `push` to `main` or any `feature/**` branch; `pull_request` targeting `main`.

**Jobs:**

#### `validate` job (ubuntu-latest, Python 3.12)

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.12"
  - name: Syntax check
    run: python -m py_compile custom_components/endgame_grocery/api.py custom_components/endgame_grocery/config_flow.py custom_components/endgame_grocery/const.py custom_components/endgame_grocery/__init__.py custom_components/endgame_grocery/todo.py
  - name: Unit tests
    run: python -m unittest discover -s tests -p "test_*.py" -v
```

#### `hacs` job (ubuntu-latest)

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: hacs/action@main
    with:
      category: integration
```

Both jobs must pass for the workflow to succeed. They run in parallel (no `needs` dependency between them).

**Notes:**
- `hacs/action@main` is the official HACS validation action; it checks `hacs.json`, `manifest.json`, and general integration structure.
- Python version pinned to `3.12` to match the syntax used in the integration (`type` statement, `list[str]` built-in generics).

---

### Phase 2 — T-007: Release Workflow

**File:** `.github/workflows/release.yml`

**Trigger:** `push` with tag pattern `v*.*.*`.

**Job:** `release` (ubuntu-latest)

```yaml
steps:
  - uses: actions/checkout@v4

  - name: Extract version from tag
    id: version
    run: echo "VERSION=${GITHUB_REF_NAME#v}" >> "$GITHUB_OUTPUT"

  - name: Stamp version into manifest.json
    run: |
      python - <<'EOF'
      import json, pathlib
      p = pathlib.Path("custom_components/endgame_grocery/manifest.json")
      data = json.loads(p.read_text())
      data["version"] = "${{ steps.version.outputs.VERSION }}"
      p.write_text(json.dumps(data, indent=2) + "\n")
      EOF

  - name: Build ZIP archive
    run: |
      cd custom_components
      zip -r ../endgame_grocery.zip endgame_grocery/

  - name: Create GitHub Release
    uses: softprops/action-gh-release@v2
    with:
      files: endgame_grocery.zip
      generate_release_notes: true
```

**Key design decisions:**
- Version is stamped into `manifest.json` inside the workspace **before** zipping — only the release artifact is affected, no commit is created.
- `softprops/action-gh-release@v2` is the de-facto standard action for creating GitHub releases.
- `generate_release_notes: true` auto-generates release notes from commits since the last tag.
- The ZIP contains only `custom_components/endgame_grocery/` so HACS can install directly into `custom_components/`.

**Tag convention (document in README):**
```
git tag v0.1.0
git push origin v0.1.0
```

---

### Phase 3 — T-008: README Overhaul & Logo

#### `custom_components/endgame_grocery/images/icon.png`

Binary copy of `assets/endgame_grocery_logo.png`. This path is the standard location HA and HACS use to display the integration icon in the UI.

#### `README.md` — complete rewrite

Replace the entire file. Structure:

```
<p align="center">
  <img src="assets/endgame_grocery_logo.png" alt="Endgame Grocery" width="150">
</p>

<h1 align="center">Endgame Grocery — Home Assistant Integration</h1>

<p align="center">
  <a href="https://github.com/DerFloDev/ha-endgame-grocery/actions/workflows/ci.yml">
    <img src="https://github.com/DerFloDev/ha-endgame-grocery/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=DerFloDev&repository=ha-endgame-grocery&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS">
  </a>
</p>
```

Sections:
1. **Overview** — one paragraph explaining what Endgame Grocery is and what the integration does (surfaces shopping lists as `todo` entities).
2. **Features** — bullet list: live sync, create/rename/toggle/delete items, per-list todo entities, configurable poll interval.
3. **Prerequisites** — Endgame Grocery server running, API key obtained from Settings, Home Assistant ≥ 2026.5, HACS installed (for HACS install path).
4. **Installation via HACS (Recommended)** — numbered steps:
   1. Open HACS → Integrations → three-dot menu → Custom repositories.
   2. Add `https://github.com/DerFloDev/ha-endgame-grocery` as an Integration.
   3. Search for "Endgame Grocery" → Download.
   4. Restart Home Assistant.
5. **Manual Installation** — numbered steps:
   1. Download the latest release ZIP from GitHub Releases.
   2. Extract `endgame_grocery/` into `<config>/custom_components/`.
   3. Restart Home Assistant.
6. **Configuration** — numbered steps (UI flow):
   1. Settings → Devices & Services → Add Integration → "Endgame Grocery".
   2. Enter Base URL (e.g. `https://grocery.example.com`).
   3. Enter API Key.
   4. Submit — entities appear automatically.
7. **Usage** — brief: entities named after lists, visible in Lovelace Todo card, full CRUD.
8. **Troubleshooting** — table:
   | Symptom | Cause | Fix |
   | `invalid_auth` error | Wrong or expired API key | Regenerate in Endgame Grocery Settings |
   | `cannot_connect` error | Wrong Base URL or server unreachable | Check URL and network |
   | New lists not appearing | Entities created at setup time | Reload the integration |
9. **Release & versioning** — one paragraph on the tag convention (`git tag v0.2.0 && git push origin v0.2.0`) for contributors.
10. **License** — placeholder (MIT, to be added by maintainer).

**Constraints:**
- Remove the entire "AI Workflow" section — it is internal tooling, not relevant to end users.
- All image paths must use the raw GitHub path format (`assets/endgame_grocery_logo.png`) so they render both locally and on GitHub.
- Badge URLs must use the exact repository path `DerFloDev/ha-endgame-grocery`.

---

## Validation

```bash
# After T-006/T-007: verify workflow YAML syntax
python -m py_compile  # not applicable for YAML; rely on GitHub Actions lint
# Locally: yamllint .github/workflows/ci.yml .github/workflows/release.yml

# After T-008: existing test suite must still pass
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile custom_components/endgame_grocery/api.py custom_components/endgame_grocery/config_flow.py custom_components/endgame_grocery/const.py custom_components/endgame_grocery/__init__.py custom_components/endgame_grocery/todo.py

# Verify icon exists and is a valid PNG (non-zero size)
python -c "import struct, pathlib; data = pathlib.Path('custom_components/endgame_grocery/images/icon.png').read_bytes(); assert data[:8] == b'\x89PNG\r\n\x1a\n', 'Not a PNG'"
```
