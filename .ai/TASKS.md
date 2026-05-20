# TASKS

Use this board to coordinate handoff between planner, implementer, and reviewer.

Status values:
- `in_planning`
- `ready_for_implement`
- `in_implementation`
- `ready_for_review`
- `in_review`
- `ready_to_commit`
- `changes_requested`
- `done`

Command expectations:
- planner moves tasks into `in_planning` and `ready_for_implement`
- implementer moves tasks into `in_implementation`, `ready_for_review`, and `done`, and resumes work from `changes_requested` and `ready_to_commit`
- reviewer moves tasks into `in_review`, `ready_to_commit`, or `changes_requested`
- `status_cycle` should report deterministic task status, current owner role, and next recommended action based on this board

| Task ID | Scope | Status | Acceptance Criteria | Evidence | Next Role |
| --- | --- | --- | --- | --- | --- |
| T-001 | Fix ZIP build command in release workflow so HACS installs files at the correct path | done | `unzip -l endgame_grocery.zip` shows `__init__.py` and `manifest.json` at archive root; all tests pass | Workflow test updated; local archive inspection confirmed root-level `__init__.py` and `manifest.json`; full test suite and syntax check passed | none |
| T-002 | Replace hardcoded `"0.1.0"` version assertion in `test_manifest_json` with semver-format check | ready_for_implement | `test_manifest_json` passes without asserting a specific version; all other tests pass | n/a | implement |
