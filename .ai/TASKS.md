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
| T-001 | Rename `async_delete_todo_item` → `async_delete_todo_items` in `todo.py` and matching test call sites in `test_todo.py` | done | All unit tests pass; DELETE requests reach the Endgame server when an item is deleted via HA UI | `python -m unittest discover -s tests -p "test_*.py"` OK; `py_compile` OK via PowerShell file iteration | none |
| T-002 | Add `description` field support: read from API, map to `TodoItem.description`, pass on create and update; add `SET_DESCRIPTION_ON_ITEM` feature flag; sentinel-based `patch_item` | ready_for_implement | `todo_items` maps description; feature flag set; create/update pass description; description-only and clear-description updates work; all tests pass | n/a | implement |
