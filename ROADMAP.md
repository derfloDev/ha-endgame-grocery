# ROADMAP

Goal: fix item deletion and add description field support for grocery items.

## Priority 1 — Fix item deletion (done)

Objective: correct the HA todo delete method name so delete requests actually reach the Endgame server.

- `async_delete_todo_item` (singular) in `todo.py` renamed to `async_delete_todo_items` (plural).
- Matching test call sites in `test_todo.py` updated.

## Priority 2 — Item description support

Objective: surface the new `description` field from the Endgame API in the HA todo integration.

- Read `description` from API item payloads and map it to `TodoItem.description`.
- Advertise `TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM` so HA enables description editing in the UI.
- Pass `description` when creating an item (`POST /lists/{id}/items`).
- Include `description` in a single combined PATCH call when name or description changes (`PATCH /lists/{id}/items/{id}`).
- `patch_item` in `api.py` uses a `_UNSET` sentinel so "not provided" is distinguishable from "explicitly cleared to null".
- All new behaviour is covered by unit tests.
