# ROADMAP

Goal: Build and publish a production-ready Home Assistant custom integration for the Endgame Grocery app, installable via HACS.

## Priority 1 — Core Integration (HACS-ready, todo platform)

Objective: Deliver a fully functional HA custom component under `custom_components/endgame_grocery/` that surfaces every accessible Endgame Grocery list as a `todo` entity in Home Assistant.

### Planned outcomes

- **HACS scaffold**: `hacs.json` in the repository root and a valid `manifest.json` so the integration is discoverable and installable via HACS.
- **Constants module** (`const.py`): single source of truth for domain, platform names, config-entry keys, and the default polling interval.
- **Async API client** (`api.py`): thin `aiohttp`-based wrapper that translates HTTP errors (401 → `ConfigEntryAuthFailed`, connection errors → `CannotConnect`, 403/404 → domain-specific exceptions) so callers never handle raw HTTP status codes.
- **Config Flow** (`config_flow.py`): UI-driven setup that prompts for Base URL and API Key, validates the credentials with a live `GET /api/v1/lists` call before accepting, and stores the entry with a meaningful title (first list name or the host name).
- **DataUpdateCoordinator** (`__init__.py`): polls `GET /api/v1/lists` and `GET /api/v1/lists/{id}/items` for all lists on a configurable interval (default: `SCAN_INTERVAL` from `const.py`), stores results as `{list_id: {"meta": List, "items": [Item]}}`.
- **Todo platform** (`todo.py`): one `EndgameGroceryTodoListEntity` per list; implements:
  - `async_get_items` — maps `open` → `TodoItemStatus.NEEDS_ACTION`, `done` → `TodoItemStatus.COMPLETED`.
  - `async_create_todo_item` — `POST /api/v1/lists/{id}/items`.
  - `async_update_todo_item` — uses `PATCH /api/v1/lists/{id}/items/{itemId}` (body: `{"name": "…"}`) for renames; uses `POST /api/v1/lists/{id}/items/{itemId}/toggle` for status changes; both changes in one call are handled by issuing both requests sequentially.
  - `async_delete_todo_item` — `DELETE /api/v1/lists/{id}/items/{itemId}`.
- **Strings & translations** (`strings.json`, `translations/en.json`): HA-compliant UI labels for the config flow.

### Acceptance criteria

- Integration loads without errors in HA dev environment (`check_config` passes).
- Config flow rejects bad credentials before creating an entry.
- Each list appears as a `todo.` entity with live items.
- Create, toggle, and delete operations round-trip correctly against the live API.
- HACS validation (`hacs-action`) passes on the repository.

### Resolved decisions

| Decision | Resolution |
|---|---|
| Default polling interval | **60 seconds** |
| HA minimum version | **2026.5** |
| Item rename | **PATCH `/api/v1/lists/{id}/items/{itemId}`** (body `{"name":"…"}`); status change via `/toggle`; both in one `async_update_todo_item` call → sequential requests |
| `render_readme` in `hacs.json` | **`true`** |

### API surface (complete)

| Method | Path | Used by |
|---|---|---|
| `GET` | `/api/v1/lists` | Coordinator, Config Flow validation |
| `GET` | `/api/v1/lists/{id}/items` | Coordinator |
| `POST` | `/api/v1/lists/{id}/items` | `async_create_todo_item` |
| `POST` | `/api/v1/lists/{id}/items/{itemId}/toggle` | `async_update_todo_item` (status) |
| `PATCH` | `/api/v1/lists/{id}/items/{itemId}` | `async_update_todo_item` (rename) |
| `DELETE` | `/api/v1/lists/{id}/items/{itemId}` | `async_delete_todo_item` |
