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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import EndgameApiError
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
        """Initialize a todo entity for one grocery list."""
        super().__init__(coordinator)
        self._list_id = list_id
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{list_id}"
        self._attr_name = coordinator.data[list_id]["meta"]["name"]

    @property
    def device_info(self) -> DeviceInfo:
        """Group all lists under a single Endgame Grocery service device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name="Endgame Grocery",
            manufacturer="Endgame Grocery",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return list items mapped from API status values to HA status values."""
        raw_items = self.coordinator.data.get(self._list_id, {}).get("items", [])
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
        """Create a new list item and refresh coordinator data."""
        await self.coordinator.client.create_item(self._list_id, item.summary)
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Rename and/or toggle an existing list item, then refresh."""
        current_items = self.coordinator.data.get(self._list_id, {}).get("items", [])
        current = next((entry for entry in current_items if entry["id"] == item.uid), None)
        if current is None:
            _LOGGER.warning(
                "Item %s not found in list %s, skipping update",
                item.uid,
                self._list_id,
            )
            return

        if item.summary is not None and item.summary != current["name"]:
            await self.coordinator.client.patch_item(
                self._list_id,
                item.uid,
                item.summary,
            )

        if item.status is not None:
            desired_raw_status = (
                "open"
                if item.status == TodoItemStatus.NEEDS_ACTION
                else "done"
            )
            if desired_raw_status != current["status"]:
                await self.coordinator.client.toggle_item(self._list_id, item.uid)

        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete one or more list items and surface API failures as HA errors."""
        try:
            for uid in uids:
                await self.coordinator.client.delete_item(self._list_id, uid)
        except EndgameApiError as err:
            _LOGGER.exception("Failed to delete item(s) from list %s", self._list_id)
            raise HomeAssistantError(
                f"Could not delete item from list {self._list_id}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
