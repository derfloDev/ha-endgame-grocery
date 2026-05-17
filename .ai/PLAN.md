# Plan

Status: **ready_for_implement**

Goal: Build a production-ready Home Assistant custom integration for the Endgame Grocery app, installable via HACS, using the `todo` platform.

Source of truth: `ROADMAP.md`

---

## Scope

Five sequentially dependent tasks:

| Task | Files | Depends on |
|------|-------|------------|
| T-001 | `hacs.json`, `manifest.json`, `const.py`, stub `__init__.py` | — |
| T-002 | `api.py` | T-001 |
| T-003 | `config_flow.py`, `strings.json`, `translations/en.json` | T-002 |
| T-004 | `__init__.py` (full implementation) | T-002, T-003 |
| T-005 | `todo.py` | T-004 |

---

## Acceptance Criteria

- All five modules load in a Home Assistant dev container without import errors.
- `async_check_config` passes.
- Config flow rejects an invalid API key (shows `invalid_auth` error) and a bad URL (shows `cannot_connect` error).
- Each list returned by `GET /api/v1/lists` appears as a `todo.*` entity.
- Creating, toggling, renaming, and deleting items round-trips correctly against the live API.
- HACS action validation passes on the repository.

---

## Implementation Phases

### Phase 1 — T-001: HACS Scaffold & Manifest

**Purpose:** Establish the repository skeleton that HACS and Home Assistant require before any Python code is loaded.

#### `hacs.json` (repository root)

```json
{
  "name": "Endgame Grocery",
  "render_readme": true
}
```

#### `custom_components/endgame_grocery/manifest.json`

```json
{
  "domain": "endgame_grocery",
  "name": "Endgame Grocery",
  "version": "0.1.0",
  "codeowners": ["@DerFloDev"],
  "config_flow": true,
  "documentation": "https://github.com/DerFloDev/ha-endgame-grocery",
  "homeassistant": "2026.5.0",
  "iot_class": "cloud_polling",
  "requirements": []
}
```

**Notes:**
- `iot_class: cloud_polling` is correct — we poll an external HTTP API on a fixed interval.
- `requirements` is empty because `aiohttp` is bundled with Home Assistant and must **not** be listed here.

#### `custom_components/endgame_grocery/const.py`

```python
"""Constants for the Endgame Grocery integration."""
from datetime import timedelta

DOMAIN = "endgame_grocery"
PLATFORMS: list[str] = ["todo"]

CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
```

#### `custom_components/endgame_grocery/__init__.py` (stub — will be replaced in T-004)

```python
"""Endgame Grocery Home Assistant integration."""
```

---

### Phase 2 — T-002: Async API Client

**File:** `custom_components/endgame_grocery/api.py`

**Design principles:**
- Never raises `aiohttp` exceptions to callers — all errors are translated to domain exceptions.
- The `aiohttp.ClientSession` is **injected** (provided by HA's `async_get_clientsession`), never created inside the client.
- All methods are `async`.
- Base URL is normalised on construction (trailing slash stripped).

#### Exception hierarchy (defined at the top of `api.py`)

```python
class EndgameApiError(Exception):
    """Base exception for all Endgame Grocery API errors."""

class EndgameAuthError(EndgameApiError):
    """Raised on HTTP 401 — maps to ConfigEntryAuthFailed in the coordinator."""

class EndgameForbiddenError(EndgameApiError):
    """Raised on HTTP 403 — API key owner cannot access the requested list."""

class EndgameNotFoundError(EndgameApiError):
    """Raised on HTTP 404 — list or item does not exist."""

class EndgameConnectionError(EndgameApiError):
    """Raised on network/connection failures — maps to UpdateFailed."""
```

#### Class `EndgameGroceryApiClient`

```python
import aiohttp
from .const import CONF_BASE_URL  # not needed here, just for reference

class EndgameGroceryApiClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        api_key: str,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
```

#### Private helper `_request`

```python
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
    ) -> dict | None:
        url = f"{self._base_url}/api/v1{path}"
        try:
            async with self._session.request(
                method, url, headers=self._headers, json=json
            ) as resp:
                if resp.status == 401:
                    raise EndgameAuthError("Invalid or missing API key")
                if resp.status == 403:
                    raise EndgameForbiddenError(f"Access denied to {path}")
                if resp.status == 404:
                    raise EndgameNotFoundError(f"Resource not found: {path}")
                if resp.status == 204:
                    return None
                resp.raise_for_status()
                return await resp.json()
        except EndgameApiError:
            raise  # pass through our own exceptions unchanged
        except aiohttp.ClientError as err:
            raise EndgameConnectionError(f"Connection error: {err}") from err
```

#### Public methods

```python
    async def get_lists(self) -> list[dict]:
        data = await self._request("GET", "/lists")
        return data["lists"]

    async def get_items(self, list_id: str) -> list[dict]:
        data = await self._request("GET", f"/lists/{list_id}/items")
        return data["items"]

    async def create_item(self, list_id: str, name: str) -> dict:
        data = await self._request(
            "POST", f"/lists/{list_id}/items", json={"name": name}
        )
        return data["item"]

    async def toggle_item(self, list_id: str, item_id: str) -> dict:
        data = await self._request(
            "POST", f"/lists/{list_id}/items/{item_id}/toggle"
        )
        return data["item"]

    async def patch_item(self, list_id: str, item_id: str, name: str) -> dict:
        data = await self._request(
            "PATCH", f"/lists/{list_id}/items/{item_id}", json={"name": name}
        )
        return data["item"]

    async def delete_item(self, list_id: str, item_id: str) -> None:
        await self._request("DELETE", f"/lists/{list_id}/items/{item_id}")
```

**Note:** The `PATCH /api/v1/lists/{listId}/items/{itemId}` endpoint is not yet in the OpenAPI spec but has been confirmed by the product owner. Assumed contract: request body `{"name": "string"}`, response `{"item": Item}` (HTTP 200), error codes 401/403/404.

---

### Phase 3 — T-003: Config Flow

**Files:**
- `custom_components/endgame_grocery/config_flow.py`
- `custom_components/endgame_grocery/strings.json`
- `custom_components/endgame_grocery/translations/en.json`

#### `config_flow.py`

```python
"""Config flow for Endgame Grocery."""
from __future__ import annotations

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EndgameGroceryApiClient, EndgameAuthError, EndgameConnectionError
from .const import DOMAIN, CONF_BASE_URL, CONF_API_KEY

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): str,
        vol.Required(CONF_API_KEY): str,
    }
)

class EndgameGroceryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Endgame Grocery config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            # Prevent duplicate entries for the same server.
            await self.async_set_unique_id(user_input[CONF_BASE_URL].rstrip("/"))
            self._abort_if_unique_id_configured()

            try:
                client = EndgameGroceryApiClient(
                    async_get_clientsession(self.hass),
                    user_input[CONF_BASE_URL],
                    user_input[CONF_API_KEY],
                )
                lists = await client.get_lists()
            except EndgameAuthError:
                errors["base"] = "invalid_auth"
            except EndgemeConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                # Use the first list name as the entry title; fall back to the host.
                title = lists[0]["name"] if lists else user_input[CONF_BASE_URL]
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
```

**Note:** `EndgemeConnectionError` in the `except` clause above is a typo in the pseudocode — the implementer must use the correct name `EndgameConnectionError`.

#### `strings.json`

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to Endgame Grocery",
        "data": {
          "base_url": "Base URL",
          "api_key": "API Key"
        },
        "data_description": {
          "base_url": "The base URL of your Endgame Grocery server, e.g. https://grocery.example.com",
          "api_key": "Your personal API key from the Endgame Grocery settings page"
        }
      }
    },
    "error": {
      "cannot_connect": "Cannot connect to the server. Check the URL and try again.",
      "invalid_auth": "Invalid API key. Generate a new one in the Endgame Grocery settings.",
      "unknown": "An unexpected error occurred."
    },
    "abort": {
      "already_configured": "This Endgame Grocery server is already configured."
    }
  }
}
```

#### `translations/en.json`

Must be an exact copy of `strings.json` (HA convention for English).

---

### Phase 4 — T-004: DataUpdateCoordinator & Entry Setup

**File:** `custom_components/endgame_grocery/__init__.py` (full replacement of stub)

```python
"""Endgame Grocery Home Assistant integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EndgameGroceryApiClient, EndgameAuthError, EndgameConnectionError
from .const import CONF_API_KEY, CONF_BASE_URL, DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

# Type alias for typed config entry access (Python 3.12 syntax, HA 2024.1+)
type EndgameGroceryConfigEntry = ConfigEntry[EndgameGroceryCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: EndgameGroceryConfigEntry
) -> bool:
    """Set up Endgame Grocery from a config entry."""
    session = async_get_clientsession(hass)
    client = EndgameGroceryApiClient(
        session,
        entry.data[CONF_BASE_URL],
        entry.data[CONF_API_KEY],
    )
    coordinator = EndgameGroceryCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EndgameGroceryConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class EndgameGroceryCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator that fetches all lists and their items every SCAN_INTERVAL."""

    config_entry: EndgameGroceryConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: EndgameGroceryApiClient,
        entry: EndgameGroceryConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch all lists and their items from the API.

        Returns:
            {
              "<list-uuid>": {
                "meta": {"id": "...", "name": "..."},
                "items": [{"id": "...", "name": "...", "status": "open|done"}, ...]
              }
            }
        """
        try:
            lists = await self.client.get_lists()
            data: dict[str, dict[str, Any]] = {}
            for lst in lists:
                items = await self.client.get_items(lst["id"])
                data[lst["id"]] = {"meta": lst, "items": items}
            return data
        except EndgameAuthError as err:
            raise ConfigEntryAuthFailed("API key rejected by server") from err
        except EndgameConnectionError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
```

**Key HA patterns used:**
- `entry.runtime_data` — stores coordinator on the config entry (HA 2024.1+ pattern, no `hass.data` dict needed).
- `async_config_entry_first_refresh()` — raises `ConfigEntryNotReady` if the first fetch fails, which HA retries automatically.
- `ConfigEntryAuthFailed` — HA triggers a re-auth flow automatically when this is raised.
- `config_entry=entry` passed to `DataUpdateCoordinator` — sets `coordinator.config_entry` automatically.

---

### Phase 5 — T-005: Todo Platform Entity

**File:** `custom_components/endgame_grocery/todo.py`

```python
"""Todo platform for Endgame Grocery."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from . import EndgameGroceryConfigEntry, EndgameGroceryCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EndgameGroceryConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Endgame Grocery todo entities from a config entry."""
    coordinator: EndgameGroceryCoordinator = entry.runtime_data
    async_add_entities(
        [
            EndgameGroceryTodoListEntity(coordinator, list_id)
            for list_id in coordinator.data
        ],
        update_before_add=True,
    )
```

#### Class `EndgameGroceryTodoListEntity`

```python
class EndgameGroceryTodoListEntity(
    CoordinatorEntity["EndgameGroceryCoordinator"], TodoListEntity
):
    """A todo list entity representing one Endgame Grocery list."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(
        self,
        coordinator: EndgameGroceryCoordinator,
        list_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._list_id = list_id
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{list_id}"
        self._attr_name = coordinator.data[list_id]["meta"]["name"]

    @property
    def device_info(self) -> DeviceInfo:
        """Group all lists under a single Endgame Grocery device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name="Endgame Grocery",
            manufacturer="Endgame Grocery",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return the current items in this list, mapped from API status to HA status."""
        raw_items = (
            self.coordinator.data.get(self._list_id, {}).get("items", [])
        )
        return [
            TodoItem(
                uid=item["id"],
                summary=item["name"],
                status=(
                    TodoItemStatus.NEEDS_ACTION
                    if item["status"] == "open"
                    else TodoItemStatus.COMPLETED
                ),
            )
            for item in raw_items
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a new item via POST /api/v1/lists/{id}/items."""
        await self.coordinator.client.create_item(self._list_id, item.summary)
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an item — rename via PATCH and/or toggle status via /toggle.

        Both operations are issued sequentially when both fields changed.
        Comparing against current coordinator state avoids unnecessary API calls.
        """
        current_items = (
            self.coordinator.data.get(self._list_id, {}).get("items", [])
        )
        current = next(
            (i for i in current_items if i["id"] == item.uid), None
        )
        if current is None:
            _LOGGER.warning(
                "Item %s not found in list %s, skipping update",
                item.uid,
                self._list_id,
            )
            return

        # Step 1: rename if summary differs.
        if item.summary is not None and item.summary != current["name"]:
            await self.coordinator.client.patch_item(
                self._list_id, item.uid, item.summary
            )

        # Step 2: toggle if status differs.
        if item.status is not None:
            desired_raw = (
                "open" if item.status == TodoItemStatus.NEEDS_ACTION else "done"
            )
            if desired_raw != current["status"]:
                await self.coordinator.client.toggle_item(self._list_id, item.uid)

        await self.coordinator.async_request_refresh()

    async def async_delete_todo_item(self, uids: list[str]) -> None:
        """Delete one or more items via DELETE /api/v1/lists/{id}/items/{itemId}."""
        for uid in uids:
            await self.coordinator.client.delete_item(self._list_id, uid)
        await self.coordinator.async_request_refresh()
```

**Key patterns:**
- `CoordinatorEntity` base class — `async_write_ha_state()` is called automatically when coordinator data changes.
- `update_before_add=True` — entities write state once before being added to HA's state machine.
- `TYPE_CHECKING` import guard — avoids circular import at runtime while keeping full type safety.
- `device_info` with `DeviceEntryType.SERVICE` — groups all list entities under one logical "Endgame Grocery" device per config entry.
- `async_request_refresh()` after every mutating call — keeps the state machine in sync immediately without waiting for the next poll.

**Known limitation (V1):** If new lists are added to the Endgame Grocery app after the integration is set up, the user must reload the integration (Config Entries → Reload) to get new entities. Dynamic entity discovery is out of scope for this cycle.

---

## Validation

No automated test suite is defined for this project yet. The implementer must perform manual validation:

```bash
# 1. Verify Python syntax for all modules
python -m py_compile custom_components/endgame_grocery/*.py

# 2. Verify there are no obvious import cycles
python -c "import custom_components.endgame_grocery"

# 3. HACS action — run locally if hacs-action is available,
#    or verify via GitHub Actions after push
```

HA runtime validation requires a dev container or live HA instance — the implementer should:
1. Copy the `custom_components/endgame_grocery/` folder into a test HA instance.
2. Restart HA and verify no errors in the log.
3. Add the integration via UI and confirm entities appear.
4. Test create, toggle, rename, and delete from the HA lovelace todo card.
