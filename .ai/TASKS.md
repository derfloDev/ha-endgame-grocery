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
| T-001 | Fix `todo/remove_item` "unknown error" — add exception handling in `async_delete_todo_item` and harden `_request` for empty-body 2xx | done | (1) `async_delete_todo_item` raises `HomeAssistantError` on `EndgameApiError` and logs at ERROR; (2) `_request` returns `None` for 200 with empty body; (3) all existing tests pass; (4) two new tests cover the fixed paths | `python -m unittest discover -s tests -p "test_*.py"` passed; `python -m py_compile` passed for `custom_components/endgame_grocery/*.py` | none |
