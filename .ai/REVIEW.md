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
