# ROADMAP

Goal: fix the "unknown error" that appears in Home Assistant when a user deletes a grocery item via `todo/remove_item`.

## Priority 1

Objective: make `async_delete_todo_item` fail-safe and surfaceable.

- `async_delete_todo_item` catches `EndgameApiError`, logs the failure, and raises `HomeAssistantError` so HA can display a meaningful message instead of "unknown error".
- `_request` in the API client handles 2xx responses that carry no JSON body (e.g. an empty 200) without raising, making the delete path robust against minor API variations.
- New unit tests cover the exception-path for delete (both the todo entity and the API client layer).
