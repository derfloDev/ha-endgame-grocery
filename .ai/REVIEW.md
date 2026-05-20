# Review Log

Shared review log for the current cycle. Append a new task section when review starts for a new task. Within a task, append a new review round instead of replacing prior history.

## Task: T-001

### Review Round 1

Status: **PASS**

Reviewed: 2026-05-20

#### Findings

No blocking or major findings.

| Severity | Location | Description | Required Fix |
|----------|----------|-------------|--------------|
| nit | `.github/workflows/release.yml` line 36 | Comment accurately explains the HACS extraction behaviour; style is fine. | No |

#### Verification

##### Steps

1. Read `.ai/PLAN.md` to understand acceptance criteria.
2. Read `git diff HEAD` for all changed files (`release.yml`, `tests/test_release_workflow.py`).
3. Confirmed the `Build ZIP archive` step now `cd`s into `custom_components/endgame_grocery` and runs `zip -r ../../endgame_grocery.zip .`.
4. Confirmed test assertions were updated to match the new command and a `assertNotIn` guard was added to reject the old broken command.
5. Ran full test suite: `python -m unittest discover -s tests -p "test_*.py"` — **36 tests, OK**.
6. Ran syntax check: `python -m py_compile custom_components/endgame_grocery/*.py` — **SYNTAX OK**.
7. Simulated new ZIP structure in Python (mirrors `cd dir && zip -r ../../x.zip .`): all files (`__init__.py`, `manifest.json`, `api.py`, `config_flow.py`, `const.py`, `todo.py`, `strings.json`) land at the **archive root** — correct for HACS `zip_release: true`.
8. Simulated old ZIP structure for contrast: all files were nested under `endgame_grocery/` — confirmed that was the bug.

##### Findings

- Archive structure produced by the new command is correct: `__init__.py` and `manifest.json` appear at root, matching the HACS extraction expectation.
- Test suite covers the new command strings and explicitly rejects the old broken string.
- No other files were affected beyond scope.

##### Risks

- None. The change is limited to the CI workflow and its regression test. The integration source files are unchanged.

#### Open Questions

- None.

#### Verdict

`PASS`

---

## Task: T-002

### Review Round 1

Status: **PASS**

Reviewed: 2026-05-20

#### Findings

No blocking or major findings.

| Severity | Location | Description | Required Fix |
|----------|----------|-------------|--------------|
| nit | `tests/test_scaffold.py` line 47 | Implementation uses `re.compile(r"^\d+\.\d+\.\d+$")` where plan shows a bare string literal; both are accepted by `assertRegex` — functionally identical. | No |

#### Verification

##### Steps

1. Read `.ai/PLAN.md` acceptance criteria for T-002.
2. Read `git diff HEAD -- tests/test_scaffold.py` — exactly one test assertion changed: `assertEqual(manifest["version"], "0.1.0")` replaced with `assertRegex(...)` using `r"^\d+\.\d+\.\d+$"`.
3. Confirmed `import re` was added at the top of the file.
4. Ran full test suite: `python -m unittest discover -s tests -p "test_*.py"` — **36 tests, OK**.
5. Ran scaffold tests verbosely: `python -m unittest tests.test_scaffold -v` — all 4 scaffold tests pass including `test_manifest_json`.
6. Ran syntax check: `python -m py_compile custom_components/endgame_grocery/*.py` — **SYNTAX OK**.
7. Manually exercised the regex against the current manifest version (`"0.1.0"` → matches) and confirmed invalid formats (`"0.1"`, `"v0.1.0"`, `"0.1.0.1"`, `"latest"`, `"1"`) are all correctly rejected.
8. Confirmed no other files were changed beyond `tests/test_scaffold.py` — scope is exactly as planned.

##### Findings

- The regex correctly accepts any `X.Y.Z` semver string and rejects non-conforming values.
- The change does not lock CI to a specific version; future releases will pass without touching the test.
- No documentation or integration source files were incorrectly modified.

##### Risks

- None. Change is confined to a single test assertion; no production code is affected.

#### Open Questions

- None.

#### Verdict

`PASS`

---

## Task: T-003

### Review Round 1

Status: **PASS**

Reviewed: 2026-05-20

#### Findings

No blocking or major findings.

| Severity | Location | Description | Required Fix |
|----------|----------|-------------|--------------|
| minor | `.github/workflows/release.yml` | If a commit lands on `main` between tag creation and the workflow's `git push origin HEAD:main`, the push will fail as non-fast-forward. Acknowledged design trade-off in the plan (single maintainer, no concurrent release authors); logged for awareness. | No |
| nit | `.github/workflows/release.yml` line 15 | `actions/checkout@v4` uses default `fetch-depth: 1` (shallow clone). Correct for this push pattern; no impact on correctness. | No |

#### Verification

##### Steps

1. Read `.ai/PLAN.md` T-003 scope: add a `Commit version bump back to main` step after `Create GitHub Release`; use `git config`, `git add`, `git commit -m "… [skip ci]"`, `git push origin HEAD:main`.
2. Read `git diff HEAD` for all changed files: `release.yml`, `tests/test_release_workflow.py`, `README.md`.
3. Confirmed the new step in `release.yml` (lines 45–52) matches the plan exactly, including commit message format with `[skip ci]` token and `HEAD:main` refspec.
4. Confirmed `permissions: contents: write` was already present at the workflow level — no new permission needed.
5. Read `ci.yml`: triggered on `push: branches: [main]`. The `[skip ci]` token in the bot commit message is the correct GitHub Actions mechanism to suppress this workflow on the back-merge push. ✅
6. Verified test assertions in `test_release_workflow.py` (lines 41–52): all 7 new assertions map 1-to-1 to the 7 new YAML lines; no over-fitting or under-fitting.
7. Ran full test suite: `python -m unittest discover -s tests -p "test_*.py"` — **36 tests, OK**.
8. Ran release workflow test verbosely: **1 test, OK**.
9. Ran syntax check: `python -m py_compile custom_components/endgame_grocery/*.py` — **SYNTAX OK**.
10. README paragraph updated accurately to describe the back-merge step.

##### Findings

- Workflow step is in the correct position (after `Create GitHub Release`), ensuring the ZIP artifact is already attached before the manifest commit is pushed.
- `[skip ci]` correctly suppresses `ci.yml` (the only branch-push-triggered workflow in the repo) on the bot commit.
- No integration source files were modified; all changes are confined to the workflow, its test, and the README.

##### Risks

- **Non-fast-forward push (minor):** If another commit reaches `main` after the release tag was cut but before the bot push completes, `git push origin HEAD:main` will be rejected. Mitigation: single-maintainer project; this scenario is unlikely in practice. Accepted risk per plan.
- **Shallow checkout:** `fetch-depth: 1` is the default; this is fine for the commit+push pattern used here.

#### Open Questions

- None.

#### Verdict

`PASS`

---

## Task: T-004

### Review Round 1

Status: **PASS**

Reviewed: 2026-05-20

#### Findings

No blocking or major findings.

| Severity | Location | Description | Required Fix |
|----------|----------|-------------|--------------|
| minor | `.github/workflows/release.yml` lines 61–62 | If `manifest.json` on `origin/main` already contains the release version (e.g. tag created from a pre-bumped commit), `git commit` will fail with "nothing to commit." Could be guarded with `git diff --quiet && echo "skip" \|\| git commit ...`. Unlikely in this project's flow but worth knowing. | No |

#### Verification

##### Steps

1. Read `.ai/PLAN.md` T-004 scope: replace the `Commit version bump back to main` step body with `git fetch origin main` → `git checkout -B chore/version-bump origin/main` → re-apply Python stamp → `git add` → `git commit [skip ci]` → `git push origin HEAD:main`.
2. Read `git diff HEAD` for all changed files: `release.yml`, `tests/test_release_workflow.py`, `README.md`.
3. Confirmed full `release.yml` (lines 45–63): step matches the plan's YAML block exactly — same commands, same order.
4. Confirmed re-stamp Python script is present between `git checkout` and `git add`, correctly re-applying the version to `origin/main`'s working tree (necessary since `git checkout -B origin/main` resets the working tree to main's state, discarding the tag-time stamp). ✅
5. Verified character-index ordering in the YAML: `git fetch` (1461) < `git checkout` (1493) < stamp (1788) < `git add` (1957) < `git push` (2137) — all in correct sequence. ✅
6. Confirmed `permissions: contents: write` still present — no new permission needed. ✅
7. Verified `[skip ci]` token preserved in commit message — still suppresses `ci.yml`. ✅
8. Reviewed new test assertions: `assertIn` for `git fetch origin main` and `git checkout -B chore/version-bump origin/main`; plus two `assertLess` ordering checks confirming fetch and checkout precede the `git add`. Ordering checks are a meaningful quality improvement over T-003's assertions. ✅
9. Ran full test suite: `python -m unittest discover -s tests -p "test_*.py"` — **36 tests, OK**.
10. Ran release workflow test verbosely: **1 test, OK**.
11. Ran syntax check: `python -m py_compile custom_components/endgame_grocery/*.py` — **SYNTAX OK**.
12. README updated to describe the fetch-before-push behaviour accurately.

##### Findings

- The fix directly addresses the observed v0.1.2 run failure: by branching from `origin/main` the push is always a fast-forward regardless of concurrent commits to main.
- The re-stamp inside the back-merge step is correctly placed and uses the same Python pattern as the earlier `Stamp version into manifest.json` step — consistent style.
- No integration source files were modified.

##### Risks

- **Empty-commit edge case (minor):** If `manifest.json` on main already holds the release version, `git commit` will fail. Not guarded; unlikely given normal tagging workflow.
- **Shallow clone:** `fetch-depth: 1` default; subsequent `git fetch origin main` is a full fetch of that ref and works correctly.

#### Open Questions

- None.

#### Verdict

`PASS`
