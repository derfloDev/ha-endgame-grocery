# PLAN

Status: **ready_for_implement**

---

## Task T-001 — Fix HA todo delete method name (done)

See previous HANDOFF entries. Implemented and ready to commit.

---

## Task T-002 — Item description support

### Context

The Endgame API now returns an optional `description` field on every `Item` object
(see `v1.yaml` → `components/schemas/Item`). The `POST` and `PATCH` item endpoints
also accept `description`. HA's `TodoListEntity` supports a matching `description`
field on `TodoItem` and the `SET_DESCRIPTION_ON_ITEM` feature flag.

### Acceptance Criteria

1. `todo_items` maps `item["description"]` (may be `None`) to `TodoItem.description`.
2. `_attr_supported_features` includes `TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM`.
3. `async_create_todo_item` passes `item.description` to the API.
4. `async_update_todo_item` issues a single combined PATCH when name **or** description
   changes; the call includes the effective value of both fields.
5. Description can be cleared (set to `None`) via an update without also changing the name.
6. All unit tests pass; `py_compile` reports no errors.

### Design Decisions

- **Sentinel for `patch_item`:** A module-level `_UNSET = object()` sentinel in `api.py`
  lets callers omit description from the PATCH body entirely (backward-compatible default)
  while still allowing an explicit `description=None` to send `null` and clear the field.
- **Single PATCH call:** Whenever name OR description changes, one PATCH is issued carrying
  the effective name (updated or current) and the new description value. No separate
  description-only call.

### Implementation Steps (TDD order)

#### Step 1 — `tests/test_api.py` — extend coverage

Add or update tests for:
- `patch_item` with description provided → body contains `description`
- `patch_item` without description → body does NOT contain `description` key
- `patch_item` with `description=None` → body contains `"description": null`
- `create_item` with description → body contains `description`
- `create_item` without description → body does NOT contain `description` key

#### Step 2 — `api.py` — add sentinel and extend signatures

```python
# Module level
_UNSET = object()
```

`create_item`:
```python
async def create_item(self, list_id: str, name: str, *, description: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"name": name}
    if description is not None:
        body["description"] = description
    data = await self._request("POST", f"/lists/{list_id}/items", json=body)
    return data["item"]
```

`patch_item`:
```python
async def patch_item(
    self,
    list_id: str,
    item_id: str,
    name: str,
    *,
    description: str | None = _UNSET,  # type: ignore[assignment]
) -> dict[str, Any]:
    body: dict[str, Any] = {"name": name}
    if description is not _UNSET:
        body["description"] = description
    data = await self._request("PATCH", f"/lists/{list_id}/items/{item_id}", json=body)
    return data["item"]
```

#### Step 3 — `tests/test_todo.py` — extend coverage

- Add `SET_DESCRIPTION_ON_ITEM = 8` to `FakeTodoListEntityFeature`.
- Add `description` field to `FakeTodoItem` (default `None`).
- Update `FakeClient.create_item` and `patch_item` signatures to accept `description`.
- Update `test_entity_exposes_ids_features_and_device_info` to assert `SET_DESCRIPTION_ON_ITEM` in supported features.
- Update `test_todo_items_map_open_and_done_statuses` to assert `description` is mapped.
- Update `test_create_todo_item_calls_api_and_refresh` to pass and assert `description`.
- Add `test_create_todo_item_with_description` — creates item with description, assert call includes it.
- Update `test_update_todo_item_patches_and_toggles_sequentially` — patch call now includes `description` kwarg.
- Add `test_update_todo_item_patches_description_only` — only description changed, PATCH issued with current name and new description.
- Add `test_update_todo_item_clears_description` — description changed to None, PATCH issued with `description=None`.
- Update `test_update_todo_item_skips_unchanged_fields` — no PATCH when neither name nor description changed.
- Update coordinator fixture data to include `"description"` on items (e.g. `"description": "2% fat"` on item-1, `None` on item-2).

#### Step 4 — `todo.py` — wire up description

`todo_items` property:
```python
TodoItem(
    uid=item["id"],
    summary=item["name"],
    description=item.get("description"),
    status=...,
)
```

`_attr_supported_features`:
```python
_attr_supported_features = (
    TodoListEntityFeature.CREATE_TODO_ITEM
    | TodoListEntityFeature.UPDATE_TODO_ITEM
    | TodoListEntityFeature.DELETE_TODO_ITEM
    | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
)
```

`async_create_todo_item`:
```python
await self.coordinator.client.create_item(
    self._list_id, item.summary, description=item.description
)
```

`async_update_todo_item` — replace the name-only patch block with:
```python
current_desc = current.get("description")
name_changed = item.summary is not None and item.summary != current["name"]
desc_changed = item.description != current_desc

if name_changed or desc_changed:
    effective_name = item.summary if item.summary is not None else current["name"]
    await self.coordinator.client.patch_item(
        self._list_id,
        item.uid,
        effective_name,
        description=item.description,
    )
```

#### Step 5 — Validate

```
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile custom_components/endgame_grocery/*.py
```

Both must exit 0.

### Files to Change

| File | Change |
|------|--------|
| `custom_components/endgame_grocery/api.py` | Add `_UNSET` sentinel; extend `create_item` and `patch_item` signatures |
| `custom_components/endgame_grocery/todo.py` | Add `SET_DESCRIPTION_ON_ITEM` feature; map description in `todo_items`; pass description in create and combined-patch update |
| `tests/test_api.py` | Tests for `patch_item` and `create_item` description behaviour |
| `tests/test_todo.py` | Extend fake classes; add and update tests for description create/read/update/clear |

### Out of Scope

- Description on list objects (only items have description per the API spec)
- Any UI / config-flow changes
- Server-side changes
