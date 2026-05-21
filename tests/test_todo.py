"""Validation tests for the Endgame Grocery todo platform."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class FakeHomeAssistant:
    """Minimal Home Assistant type placeholder."""


class FakeHomeAssistantError(Exception):
    """Stand-in for Home Assistant service-layer errors."""


class FakeAiohttpClientError(Exception):
    """Stand-in for aiohttp.ClientError."""


class FakeCoordinatorEntity:
    """Minimal CoordinatorEntity base class for unit tests."""

    def __init__(self, coordinator: object) -> None:
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        """Allow generic-style subscription."""
        return cls


class FakeTodoListEntity:
    """Minimal TodoListEntity base class for unit tests."""


class FakeTodoListEntityFeature:
    """Bit flags for supported todo entity features."""

    CREATE_TODO_ITEM = 1
    UPDATE_TODO_ITEM = 2
    DELETE_TODO_ITEM = 4


class FakeTodoItemStatus:
    """Stand-in enum values for Home Assistant todo item status."""

    NEEDS_ACTION = "needs_action"
    COMPLETED = "completed"


@dataclass
class FakeTodoItem:
    """Simple todo item container used by the entity tests."""

    summary: str | None = None
    status: str | None = None
    uid: str | None = None


class FakeDeviceEntryType:
    """Stand-in enum for Home Assistant device entry types."""

    SERVICE = "service"


class FakeDeviceInfo(dict):
    """Dictionary-like replacement for Home Assistant DeviceInfo."""


class FakeConfigEntry:
    """Minimal config entry used by the todo platform tests."""

    def __init__(self, entry_id: str = "entry-1") -> None:
        self.entry_id = entry_id
        self.runtime_data = None


class FakeClient:
    """Record todo platform API mutations."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object, ...]] = []
        self.raise_on_delete: Exception | None = None

    async def create_item(self, list_id: str, name: str | None) -> None:
        self.calls.append(("create_item", list_id, name))

    async def patch_item(self, list_id: str, item_id: str | None, name: str) -> None:
        self.calls.append(("patch_item", list_id, item_id, name))

    async def toggle_item(self, list_id: str, item_id: str | None) -> None:
        self.calls.append(("toggle_item", list_id, item_id))

    async def delete_item(self, list_id: str, item_id: str) -> None:
        if self.raise_on_delete is not None:
            raise self.raise_on_delete
        self.calls.append(("delete_item", list_id, item_id))


class FakeCoordinator:
    """Coordinator object with mutable data and refresh tracking."""

    def __init__(self, data: dict[str, dict[str, object]], entry_id: str = "entry-1"):
        self.data = data
        self.config_entry = FakeConfigEntry(entry_id)
        self.client = FakeClient()
        self.refresh_calls = 0

    async def async_request_refresh(self) -> None:
        self.refresh_calls += 1


class TestEndgameGroceryTodo(unittest.IsolatedAsyncioTestCase):
    """Verify T-005 todo entity behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        """Import the todo module with fake Home Assistant dependencies."""
        fake_todo = types.SimpleNamespace(
            TodoItem=FakeTodoItem,
            TodoItemStatus=FakeTodoItemStatus,
            TodoListEntity=FakeTodoListEntity,
            TodoListEntityFeature=FakeTodoListEntityFeature,
        )
        fake_core = types.SimpleNamespace(HomeAssistant=FakeHomeAssistant)
        fake_device_registry = types.SimpleNamespace(
            DeviceEntryType=FakeDeviceEntryType,
            DeviceInfo=FakeDeviceInfo,
        )
        fake_entity_platform = types.SimpleNamespace(AddEntitiesCallback=object)
        fake_update_coordinator = types.SimpleNamespace(
            CoordinatorEntity=FakeCoordinatorEntity
        )
        fake_aiohttp = types.SimpleNamespace(
            ClientError=FakeAiohttpClientError,
            ClientSession=object,
        )

        cls._module_patcher = patch.dict(
            sys.modules,
            {
                "aiohttp": fake_aiohttp,
                "homeassistant": types.ModuleType("homeassistant"),
                "homeassistant.components": types.ModuleType("homeassistant.components"),
                "homeassistant.components.todo": fake_todo,
                "homeassistant.core": fake_core,
                "homeassistant.exceptions": types.SimpleNamespace(
                    HomeAssistantError=FakeHomeAssistantError
                ),
                "homeassistant.helpers": types.ModuleType("homeassistant.helpers"),
                "homeassistant.helpers.device_registry": fake_device_registry,
                "homeassistant.helpers.entity_platform": fake_entity_platform,
                "homeassistant.helpers.update_coordinator": fake_update_coordinator,
            },
        )
        cls._module_patcher.start()
        sys.modules.pop("custom_components.endgame_grocery.api", None)
        sys.modules.pop("custom_components.endgame_grocery.todo", None)
        cls.todo = importlib.import_module("custom_components.endgame_grocery.todo")

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up fake dependency modules."""
        sys.modules.pop("custom_components.endgame_grocery.api", None)
        sys.modules.pop("custom_components.endgame_grocery.todo", None)
        cls._module_patcher.stop()

    def _build_coordinator(self) -> FakeCoordinator:
        """Create coordinator data with two grocery lists."""
        return FakeCoordinator(
            {
                "list-1": {
                    "meta": {"id": "list-1", "name": "Weekly Shopping"},
                    "items": [
                        {"id": "item-1", "name": "Milk", "status": "open"},
                        {"id": "item-2", "name": "Eggs", "status": "done"},
                    ],
                },
                "list-2": {
                    "meta": {"id": "list-2", "name": "Hardware Store"},
                    "items": [],
                },
            }
        )

    async def test_setup_entry_creates_one_entity_per_list(self) -> None:
        """Setup should create one todo entity per list in coordinator data."""
        coordinator = self._build_coordinator()
        entry = coordinator.config_entry
        entry.runtime_data = coordinator
        added: list[object] = []
        update_before_add_flags: list[bool] = []

        def async_add_entities(entities: list[object], update_before_add: bool) -> None:
            added.extend(entities)
            update_before_add_flags.append(update_before_add)

        await self.todo.async_setup_entry(FakeHomeAssistant(), entry, async_add_entities)

        self.assertEqual(len(added), 2)
        self.assertEqual(update_before_add_flags, [True])
        self.assertEqual({entity._list_id for entity in added}, {"list-1", "list-2"})

    async def test_entity_exposes_ids_features_and_device_info(self) -> None:
        """The entity should expose the planned HA identity metadata."""
        entity = self.todo.EndgameGroceryTodoListEntity(self._build_coordinator(), "list-1")

        self.assertTrue(entity._attr_has_entity_name)
        self.assertEqual(entity._attr_unique_id, "entry-1_list-1")
        self.assertEqual(entity._attr_name, "Weekly Shopping")
        self.assertEqual(
            entity._attr_supported_features,
            FakeTodoListEntityFeature.CREATE_TODO_ITEM
            | FakeTodoListEntityFeature.UPDATE_TODO_ITEM
            | FakeTodoListEntityFeature.DELETE_TODO_ITEM,
        )
        self.assertEqual(
            entity.device_info,
            {
                "identifiers": {("endgame_grocery", "entry-1")},
                "name": "Endgame Grocery",
                "manufacturer": "Endgame Grocery",
                "entry_type": "service",
            },
        )

    async def test_todo_items_map_open_and_done_statuses(self) -> None:
        """API item status values should map to Home Assistant todo statuses."""
        entity = self.todo.EndgameGroceryTodoListEntity(self._build_coordinator(), "list-1")

        items = entity.todo_items

        self.assertEqual(
            items,
            [
                FakeTodoItem(
                    uid="item-1",
                    summary="Milk",
                    status=FakeTodoItemStatus.NEEDS_ACTION,
                ),
                FakeTodoItem(
                    uid="item-2",
                    summary="Eggs",
                    status=FakeTodoItemStatus.COMPLETED,
                ),
            ],
        )

    async def test_create_todo_item_calls_api_and_refresh(self) -> None:
        """Creating an item should POST to the API and request a refresh."""
        coordinator = self._build_coordinator()
        entity = self.todo.EndgameGroceryTodoListEntity(coordinator, "list-1")

        await entity.async_create_todo_item(FakeTodoItem(summary="Bread"))

        self.assertEqual(coordinator.client.calls, [("create_item", "list-1", "Bread")])
        self.assertEqual(coordinator.refresh_calls, 1)

    async def test_update_todo_item_patches_and_toggles_sequentially(self) -> None:
        """Renames and status changes should issue both API calls sequentially."""
        coordinator = self._build_coordinator()
        entity = self.todo.EndgameGroceryTodoListEntity(coordinator, "list-1")

        await entity.async_update_todo_item(
            FakeTodoItem(
                uid="item-1",
                summary="Oat Milk",
                status=FakeTodoItemStatus.COMPLETED,
            )
        )

        self.assertEqual(
            coordinator.client.calls,
            [
                ("patch_item", "list-1", "item-1", "Oat Milk"),
                ("toggle_item", "list-1", "item-1"),
            ],
        )
        self.assertEqual(coordinator.refresh_calls, 1)

    async def test_update_todo_item_skips_unchanged_fields(self) -> None:
        """No API mutation should run when summary and status are unchanged."""
        coordinator = self._build_coordinator()
        entity = self.todo.EndgameGroceryTodoListEntity(coordinator, "list-1")

        await entity.async_update_todo_item(
            FakeTodoItem(
                uid="item-1",
                summary="Milk",
                status=FakeTodoItemStatus.NEEDS_ACTION,
            )
        )

        self.assertEqual(coordinator.client.calls, [])
        self.assertEqual(coordinator.refresh_calls, 1)

    async def test_update_todo_item_missing_item_logs_and_returns(self) -> None:
        """Missing items should be ignored without API calls or refresh."""
        coordinator = self._build_coordinator()
        entity = self.todo.EndgameGroceryTodoListEntity(coordinator, "list-1")

        with self.assertLogs("custom_components.endgame_grocery.todo", level="WARNING") as logs:
            await entity.async_update_todo_item(
                FakeTodoItem(
                    uid="missing-item",
                    summary="Does not matter",
                    status=FakeTodoItemStatus.COMPLETED,
                )
            )

        self.assertIn("missing-item", logs.output[0])
        self.assertEqual(coordinator.client.calls, [])
        self.assertEqual(coordinator.refresh_calls, 0)

    async def test_delete_todo_item_deletes_all_uids_then_refreshes(self) -> None:
        """Deleting items should call the API once per uid, then refresh."""
        coordinator = self._build_coordinator()
        entity = self.todo.EndgameGroceryTodoListEntity(coordinator, "list-1")

        await entity.async_delete_todo_item(["item-1", "item-2"])

        self.assertEqual(
            coordinator.client.calls,
            [
                ("delete_item", "list-1", "item-1"),
                ("delete_item", "list-1", "item-2"),
            ],
        )
        self.assertEqual(coordinator.refresh_calls, 1)

    async def test_delete_todo_item_raises_ha_error_on_api_failure(self) -> None:
        """Delete failures should surface as HomeAssistantError and skip refresh."""
        from custom_components.endgame_grocery.api import EndgameConnectionError

        coordinator = self._build_coordinator()
        coordinator.client.raise_on_delete = EndgameConnectionError("timeout")
        entity = self.todo.EndgameGroceryTodoListEntity(coordinator, "list-1")

        with self.assertLogs("custom_components.endgame_grocery.todo", level="ERROR") as logs:
            with self.assertRaises(FakeHomeAssistantError):
                await entity.async_delete_todo_item(["item-1"])

        self.assertIn("Failed to delete item(s) from list list-1", logs.output[0])
        self.assertEqual(coordinator.refresh_calls, 0)


if __name__ == "__main__":
    unittest.main()
