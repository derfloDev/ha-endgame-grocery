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
| T-001 | Add `CONF_SCAN_INTERVAL` constant; extend config-flow user step with scan_interval field (10–600 s, default 60, validation error outside range); add OptionsFlowHandler; update strings.json and translations/en.json | done | Initial setup form shows scan_interval field with default 60; submitting out-of-range value yields `invalid_scan_interval` error; options flow pre-fills and saves interval; strings.json == en.json; py_compile passes | `python -m py_compile custom_components/endgame_grocery/const.py` OK; `python -m py_compile custom_components/endgame_grocery/config_flow.py` OK; `python -m unittest tests.test_config_flow` OK; `python -m unittest discover -s tests -p "test_*.py"` OK | none |
| T-002 | Wire scan_interval into EndgameGroceryCoordinator (options → data → default); register async_reload_entry as options update listener; add/update tests in test_init.py and test_config_flow.py | ready_for_implement | Coordinator uses value from entry.options when present; falls back to entry.data then default 60 s; saving new interval in options triggers coordinator reload; all unittest tests pass | n/a | implement |
