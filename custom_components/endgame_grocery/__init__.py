"""Endgame Grocery Home Assistant integration."""

from __future__ import annotations

import logging
from typing import Any

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.exceptions import ConfigEntryAuthFailed
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.helpers.update_coordinator import (
        DataUpdateCoordinator,
        UpdateFailed,
    )
except (ImportError, ModuleNotFoundError):  # pragma: no cover - local test fallback
    class ConfigEntry:
        """Fallback config entry type for local test imports."""

        def __class_getitem__(cls, item):
            return cls

    class HomeAssistant:
        """Fallback Home Assistant type for local test imports."""

    class ConfigEntryAuthFailed(Exception):
        """Fallback auth exception for local test imports."""

    class UpdateFailed(Exception):
        """Fallback update exception for local test imports."""

    class DataUpdateCoordinator:
        """Fallback coordinator base for local test imports."""

        def __class_getitem__(cls, item):
            return cls

    def async_get_clientsession(hass: HomeAssistant) -> None:
        """Fallback aiohttp session getter for local test imports."""
        raise RuntimeError("Home Assistant runtime is not available")

from .const import CONF_API_KEY, CONF_BASE_URL, DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS

try:
    from .api import EndgameAuthError, EndgameConnectionError, EndgameGroceryApiClient
except (ImportError, ModuleNotFoundError):  # pragma: no cover - local test fallback
    class EndgameAuthError(Exception):
        """Fallback API auth error for local test imports."""

    class EndgameConnectionError(Exception):
        """Fallback API connection error for local test imports."""

    class EndgameGroceryApiClient:
        """Fallback API client type for local test imports."""

_LOGGER = logging.getLogger(__name__)

type EndgameGroceryConfigEntry = ConfigEntry[EndgameGroceryCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EndgameGroceryConfigEntry,
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
    hass: HomeAssistant,
    entry: EndgameGroceryConfigEntry,
) -> bool:
    """Unload Endgame Grocery for a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class EndgameGroceryCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator that fetches lists and items from the Endgame Grocery API."""

    config_entry: EndgameGroceryConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: EndgameGroceryApiClient,
        entry: EndgameGroceryConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch all lists and their items from the API."""
        try:
            lists = await self.client.get_lists()
            data: dict[str, dict[str, Any]] = {}
            for grocery_list in lists:
                items = await self.client.get_items(grocery_list["id"])
                data[grocery_list["id"]] = {"meta": grocery_list, "items": items}
            return data
        except EndgameAuthError as err:
            raise ConfigEntryAuthFailed("API key rejected by server") from err
        except EndgameConnectionError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
