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
