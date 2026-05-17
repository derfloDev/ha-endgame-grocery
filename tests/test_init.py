"""Validation tests for the Endgame Grocery integration setup."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class FakeConfigEntry:
    """Minimal config entry used for coordinator and setup tests."""

    def __init__(self, data: dict[str, str], entry_id: str = "entry-1") -> None:
        self.data = data
        self.entry_id = entry_id
        self.runtime_data = None

    def __class_getitem__(cls, item):
        """Allow generic-style use in type aliases."""
        return cls


class FakeConfigEntriesManager:
    """Track forwarded setups and unloads for a fake Home Assistant instance."""

    def __init__(self) -> None:
        self.forward_calls: list[tuple[FakeConfigEntry, list[str]]] = []
        self.unload_calls: list[tuple[FakeConfigEntry, list[str]]] = []

    async def async_forward_entry_setups(
        self,
        entry: FakeConfigEntry,
        platforms: list[str],
    ) -> None:
        """Record forwarded platform setups."""
        self.forward_calls.append((entry, platforms))

    async def async_unload_platforms(
        self,
        entry: FakeConfigEntry,
        platforms: list[str],
    ) -> bool:
        """Record unload requests and report success."""
        self.unload_calls.append((entry, platforms))
        return True


class FakeHomeAssistant:
    """Minimal Home Assistant container for config entry setup tests."""

    def __init__(self) -> None:
        self.config_entries = FakeConfigEntriesManager()


class FakeConfigEntryAuthFailed(Exception):
    """Stand-in for Home Assistant auth failures."""


class FakeUpdateFailed(Exception):
    """Stand-in for Home Assistant update failures."""


class FakeDataUpdateCoordinator:
    """Minimal DataUpdateCoordinator implementation for unit tests."""

    def __init__(
        self,
        hass: FakeHomeAssistant,
        logger: object,
        *,
        name: str,
        update_interval: object,
        config_entry: FakeConfigEntry,
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.config_entry = config_entry
        self.data = None
        self.first_refresh_calls = 0

    def __class_getitem__(cls, item):
        """Allow subscription syntax for generic annotations."""
        return cls

    async def async_config_entry_first_refresh(self) -> None:
        """Mimic HA's first refresh by storing fetched data."""
        self.first_refresh_calls += 1
        self.data = await self._async_update_data()


class FakeApiClient:
    """Configurable stand-in for the Endgame API client."""

    lists_response: list[dict[str, str]] = []
    items_by_list: dict[str, list[dict[str, str]]] = {}
    lists_error: Exception | None = None
    instances: list[FakeApiClient] = []

    def __init__(self, session: object, base_url: str, api_key: str) -> None:
        self.session = session
        self.base_url = base_url
        self.api_key = api_key
        self.get_items_calls: list[str] = []
        self.__class__.instances.append(self)

    async def get_lists(self) -> list[dict[str, str]]:
        """Return lists or raise the configured error."""
        if self.__class__.lists_error is not None:
            raise self.__class__.lists_error
        return self.__class__.lists_response

    async def get_items(self, list_id: str) -> list[dict[str, str]]:
        """Return items for the requested list."""
        self.get_items_calls.append(list_id)
        return self.__class__.items_by_list[list_id]


class TestEndgameGroceryInit(unittest.IsolatedAsyncioTestCase):
    """Verify T-004 entry setup and coordinator behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        """Import the integration module with fake HA dependencies."""
        fake_config_entries = types.SimpleNamespace(ConfigEntry=FakeConfigEntry)
        fake_core = types.SimpleNamespace(HomeAssistant=FakeHomeAssistant)
        fake_exceptions = types.SimpleNamespace(
            ConfigEntryAuthFailed=FakeConfigEntryAuthFailed
        )

        cls._session_sentinel = object()
        fake_aiohttp_client = types.SimpleNamespace(
            async_get_clientsession=lambda hass: cls._session_sentinel
        )
        fake_update_coordinator = types.SimpleNamespace(
            DataUpdateCoordinator=FakeDataUpdateCoordinator,
            UpdateFailed=FakeUpdateFailed,
        )

        fake_api = types.SimpleNamespace(
            EndgameGroceryApiClient=FakeApiClient,
            EndgameAuthError=type("EndgameAuthError", (Exception,), {}),
            EndgameConnectionError=type("EndgameConnectionError", (Exception,), {}),
        )

        cls._module_patcher = patch.dict(
            sys.modules,
            {
                "homeassistant": types.ModuleType("homeassistant"),
                "homeassistant.config_entries": fake_config_entries,
                "homeassistant.core": fake_core,
                "homeassistant.exceptions": fake_exceptions,
                "homeassistant.helpers": types.ModuleType("homeassistant.helpers"),
                "homeassistant.helpers.aiohttp_client": fake_aiohttp_client,
                "homeassistant.helpers.update_coordinator": fake_update_coordinator,
                "custom_components.endgame_grocery.api": fake_api,
            },
        )
        cls._module_patcher.start()
        sys.modules.pop("custom_components.endgame_grocery", None)
        cls.integration = importlib.import_module("custom_components.endgame_grocery")
        cls.EndgameAuthError = fake_api.EndgameAuthError
        cls.EndgameConnectionError = fake_api.EndgameConnectionError

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up fake dependency modules."""
        sys.modules.pop("custom_components.endgame_grocery", None)
        cls._module_patcher.stop()

    def setUp(self) -> None:
        """Reset fake API state before each test."""
        FakeApiClient.lists_response = []
        FakeApiClient.items_by_list = {}
        FakeApiClient.lists_error = None
        FakeApiClient.instances = []

    async def test_setup_entry_creates_coordinator_and_forwards_platforms(self) -> None:
        """Entry setup should refresh once and store the coordinator on the entry."""
        hass = FakeHomeAssistant()
        entry = FakeConfigEntry(
            {"base_url": "https://grocery.example.com", "api_key": "secret-key"}
        )
        FakeApiClient.lists_response = [{"id": "list-1", "name": "Weekly Shopping"}]
        FakeApiClient.items_by_list = {
            "list-1": [{"id": "item-1", "name": "Milk", "status": "open"}]
        }

        result = await self.integration.async_setup_entry(hass, entry)

        self.assertTrue(result)
        self.assertIsNotNone(entry.runtime_data)
        self.assertEqual(entry.runtime_data.first_refresh_calls, 1)
        self.assertEqual(
            hass.config_entries.forward_calls,
            [(entry, ["todo"])],
        )
        self.assertIs(FakeApiClient.instances[0].session, self._session_sentinel)
        self.assertEqual(FakeApiClient.instances[0].base_url, "https://grocery.example.com")
        self.assertEqual(FakeApiClient.instances[0].api_key, "secret-key")

    async def test_unload_entry_unloads_platforms(self) -> None:
        """Entry unload should unload all declared platforms."""
        hass = FakeHomeAssistant()
        entry = FakeConfigEntry(
            {"base_url": "https://grocery.example.com", "api_key": "secret-key"}
        )

        result = await self.integration.async_unload_entry(hass, entry)

        self.assertTrue(result)
        self.assertEqual(
            hass.config_entries.unload_calls,
            [(entry, ["todo"])],
        )

    async def test_coordinator_updates_all_lists_and_items(self) -> None:
        """The coordinator should aggregate each list with its fetched items."""
        hass = FakeHomeAssistant()
        entry = FakeConfigEntry(
            {"base_url": "https://grocery.example.com", "api_key": "secret-key"}
        )
        client = FakeApiClient(object(), "https://grocery.example.com", "secret-key")
        FakeApiClient.lists_response = [
            {"id": "list-1", "name": "Weekly Shopping"},
            {"id": "list-2", "name": "Hardware Store"},
        ]
        FakeApiClient.items_by_list = {
            "list-1": [{"id": "item-1", "name": "Milk", "status": "open"}],
            "list-2": [{"id": "item-2", "name": "Batteries", "status": "done"}],
        }

        coordinator = self.integration.EndgameGroceryCoordinator(hass, client, entry)
        data = await coordinator._async_update_data()

        self.assertEqual(
            data,
            {
                "list-1": {
                    "meta": {"id": "list-1", "name": "Weekly Shopping"},
                    "items": [{"id": "item-1", "name": "Milk", "status": "open"}],
                },
                "list-2": {
                    "meta": {"id": "list-2", "name": "Hardware Store"},
                    "items": [
                        {"id": "item-2", "name": "Batteries", "status": "done"}
                    ],
                },
            },
        )
        self.assertEqual(client.get_items_calls, ["list-1", "list-2"])

    async def test_coordinator_maps_auth_errors_to_config_entry_auth_failed(
        self,
    ) -> None:
        """Auth errors should trigger Home Assistant reauthentication handling."""
        hass = FakeHomeAssistant()
        entry = FakeConfigEntry(
            {"base_url": "https://grocery.example.com", "api_key": "secret-key"}
        )
        client = FakeApiClient(object(), "https://grocery.example.com", "secret-key")
        FakeApiClient.lists_error = self.EndgameAuthError("bad key")

        coordinator = self.integration.EndgameGroceryCoordinator(hass, client, entry)

        with self.assertRaises(FakeConfigEntryAuthFailed):
            await coordinator._async_update_data()

    async def test_coordinator_maps_connection_errors_to_update_failed(self) -> None:
        """Connection errors should be wrapped as update failures."""
        hass = FakeHomeAssistant()
        entry = FakeConfigEntry(
            {"base_url": "https://grocery.example.com", "api_key": "secret-key"}
        )
        client = FakeApiClient(object(), "https://grocery.example.com", "secret-key")
        FakeApiClient.lists_error = self.EndgameConnectionError("offline")

        coordinator = self.integration.EndgameGroceryCoordinator(hass, client, entry)

        with self.assertRaises(FakeUpdateFailed):
            await coordinator._async_update_data()


if __name__ == "__main__":
    unittest.main()
