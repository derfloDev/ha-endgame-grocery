# Plan

Status: **ready_for_implement**

Goal: fix the `todo/remove_item` "unknown error" in Home Assistant when deleting a grocery item.

## Root Cause

`async_delete_todo_item` in `todo.py` has no exception handling.
Any `EndgameApiError` (e.g. 404 if the item was already removed, or a network blip) propagates
unhandled to HA, which shows "unknown error" instead of a meaningful message.

Secondary hardening: `_request` in `api.py` calls `response.json()` on every non-204 success
response. A 200 with an empty body (some API variants) raises `ValueError`/`ContentTypeError` that
would escape the existing `aiohttp.ClientError` guard and reach HA as another "unknown error".

## Scope

| # | File | Change |
|---|------|--------|
| 1 | `custom_components/endgame_grocery/todo.py` | Add `HomeAssistantError` import; add `EndgameApiError` import; wrap the delete loop in `try/except EndgameApiError` → log + raise `HomeAssistantError` |
| 2 | `custom_components/endgame_grocery/api.py` | Replace `return await response.json()` with `return await response.json(content_type=None)` inside a `try/except ValueError` that returns `None` for empty/non-JSON bodies |
| 3 | `tests/test_todo.py` | Add `FakeHomeAssistantError`; add `homeassistant.exceptions` to the mock dict; add test `test_delete_todo_item_raises_ha_error_on_api_failure` |
| 4 | `tests/test_api.py` | Add test `test_delete_200_empty_body_returns_none` — 200 with empty body should return `None`, not raise |

## Acceptance Criteria

- `async_delete_todo_item` raises `HomeAssistantError` (not a raw `EndgameApiError`) when the API
  call fails, and logs the failure at `ERROR` level via `_LOGGER.exception`.
- `_request` returns `None` for a 200 response with an empty body on DELETE instead of raising.
- All existing tests continue to pass.
- Two new tests (one per layer) verify the fixed behaviour.

## Implementation Steps

### Step 1 — `api.py`: harden `_request` for empty-body 2xx

Replace:
```python
response.raise_for_status()
return await response.json()
```
With:
```python
response.raise_for_status()
try:
    return await response.json(content_type=None)
except ValueError:
    return None
```

`content_type=None` skips aiohttp's Content-Type check; `ValueError` covers
`json.JSONDecodeError` for empty or non-JSON bodies.

### Step 2 — `todo.py`: add imports

Add to the `homeassistant` import block:
```python
from homeassistant.exceptions import HomeAssistantError
```

Add to the `.api` import (TYPE_CHECKING guard is already there; add a runtime import):
```python
from .api import EndgameApiError
```

### Step 3 — `todo.py`: wrap delete loop

Replace the body of `async_delete_todo_item`:
```python
async def async_delete_todo_item(self, uids: list[str]) -> None:
    """Delete one or more list items and refresh coordinator data."""
    try:
        for uid in uids:
            await self.coordinator.client.delete_item(self._list_id, uid)
    except EndgameApiError as err:
        _LOGGER.exception(
            "Failed to delete item(s) from list %s: %s",
            self._list_id,
            err,
        )
        raise HomeAssistantError(
            f"Could not delete item from list {self._list_id}: {err}"
        ) from err
    await self.coordinator.async_request_refresh()
```

### Step 4 — `tests/test_todo.py`: extend fake HA modules and add failure test

1. Add `class FakeHomeAssistantError(Exception): ...` near the other fake classes.
2. Add `"homeassistant.exceptions": types.SimpleNamespace(HomeAssistantError=FakeHomeAssistantError)` to the `patch.dict` in `setUpClass`.
3. Add a `FakeClientWithError` helper (or re-use `FakeClient` with a configurable raise).
4. Add test:

```python
async def test_delete_todo_item_raises_ha_error_on_api_failure(self) -> None:
    """An API error during delete should surface as HomeAssistantError."""
    from custom_components.endgame_grocery.api import EndgameConnectionError

    coordinator = self._build_coordinator()
    coordinator.client.raise_on_delete = EndgameConnectionError("timeout")
    entity = self.todo.EndgameGroceryTodoListEntity(coordinator, "list-1")

    with self.assertRaises(FakeHomeAssistantError):
        await entity.async_delete_todo_item(["item-1"])

    self.assertEqual(coordinator.refresh_calls, 0)
```

Extend `FakeClient.delete_item` to honour an optional `raise_on_delete` attribute:
```python
async def delete_item(self, list_id: str, item_id: str) -> None:
    if raise := getattr(self, "raise_on_delete", None):
        raise raise_on_delete  # noqa: F821  (walrus pattern)
    self.calls.append(("delete_item", list_id, item_id))
```

### Step 5 — `tests/test_api.py`: add empty-body test

```python
async def test_delete_200_empty_body_returns_none(self) -> None:
    """A 200 response with no JSON body should return None, not raise."""
    # FakeResponse.json() raises ValueError when payload is None and accessed raw
    # We simulate this by making json() raise ValueError
    session = FakeSession([FakeResponse(status=200, payload=None)])
    # patch json() to raise ValueError (empty body)
    ...
    result = await client.delete_item("list-1", "item-4")
    self.assertIsNone(result)
```

Note: because `FakeResponse.json()` returns `{}` by default (not empty), the implementer must
adjust `FakeResponse` so that passing `payload=None` causes `json()` to raise `ValueError`, or
add a new `raise_json` flag. Either approach is acceptable as long as the test exercises the new
`except ValueError` branch in `_request`.

## Validation

```
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile custom_components/endgame_grocery/*.py
```

Both commands must exit 0 before the task is marked `ready_for_review`.
