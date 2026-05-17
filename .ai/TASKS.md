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
| T-001 | HACS Scaffold & Manifest — `hacs.json` (root), `manifest.json`, `const.py`, stub `__init__.py` | done | `hacs.json` present in root with `render_readme: true`; `manifest.json` valid with `domain=endgame_grocery`, `homeassistant=2026.5.0`, `iot_class=cloud_polling`; `const.py` defines `DOMAIN`, `PLATFORMS`, `CONF_BASE_URL`, `CONF_API_KEY`, `DEFAULT_SCAN_INTERVAL=60s`; stub `__init__.py` exists | `python -m unittest discover -s tests -p "test_*.py"` PASS; `python -m compileall -q custom_components/endgame_grocery` PASS | none |
| T-002 | Async API Client — `api.py` with `aiohttp`, full error-mapping | done | `EndgameGroceryApiClient` class with all 6 methods (`get_lists`, `get_items`, `create_item`, `toggle_item`, `patch_item`, `delete_item`); exception hierarchy (`EndgameApiError`, `EndgameAuthError`, `EndgameForbiddenError`, `EndgameNotFoundError`, `EndgameConnectionError`); HTTP 401 → `EndgameAuthError`, network errors → `EndgameConnectionError`; session injected, never created internally | `python -m unittest discover -s tests -p "test_*.py"` PASS; `python -m py_compile` PASS via PowerShell file expansion for `custom_components/endgame_grocery/*.py` | none |
| T-003 | Config Flow — `config_flow.py`, `strings.json`, `translations/en.json` | done | Config flow prompts for `base_url` and `api_key`; validates credentials via live `GET /api/v1/lists`; bad key → `invalid_auth` error shown; bad URL → `cannot_connect` error shown; duplicate server → aborted; on success entry title is first list name or base URL; `strings.json` and `translations/en.json` present and matching | `python -m unittest discover -s tests -p "test_*.py"` PASS; `python -m py_compile` PASS via PowerShell file expansion for `custom_components/endgame_grocery/*.py` | none |
| T-004 | DataUpdateCoordinator & Entry Setup — full `__init__.py` | done | `async_setup_entry` uses `async_get_clientsession`, creates coordinator, calls `async_config_entry_first_refresh`, stores coordinator in `entry.runtime_data`, forwards setups to PLATFORMS; `async_unload_entry` unloads platforms; `EndgameGroceryCoordinator._async_update_data` fetches all lists then all items, returns `{list_id: {meta, items}}`; `EndgameAuthError` → `ConfigEntryAuthFailed`; `EndgameConnectionError` → `UpdateFailed` | `python -m unittest discover -s tests -p "test_*.py"` PASS; `python -m py_compile` PASS via PowerShell file expansion for `custom_components/endgame_grocery/*.py` | none |
| T-005 | Todo Platform Entity — `todo.py` | ready_for_implement | `async_setup_entry` creates one `EndgameGroceryTodoListEntity` per list in coordinator data; entity: `unique_id={entry_id}_{list_id}`, `has_entity_name=True`, `device_info` groups under one SERVICE device; `todo_items` maps `open→NEEDS_ACTION`, `done→COMPLETED`; `async_create_todo_item` calls `create_item` then refreshes; `async_update_todo_item` patches name if changed and toggles status if changed (sequential); `async_delete_todo_item` deletes all UIDs then refreshes | n/a | implement |
