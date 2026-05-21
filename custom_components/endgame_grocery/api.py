"""Async API client for the Endgame Grocery integration."""

from __future__ import annotations

from typing import Any

import aiohttp

_UNSET = object()


class EndgameApiError(Exception):
    """Base exception for all Endgame Grocery API errors."""


class EndgameAuthError(EndgameApiError):
    """Raised when the API key is invalid or missing."""


class EndgameForbiddenError(EndgameApiError):
    """Raised when the API key cannot access the requested resource."""


class EndgameNotFoundError(EndgameApiError):
    """Raised when the requested list or item does not exist."""


class EndgameConnectionError(EndgameApiError):
    """Raised when the client cannot complete an API request."""


class EndgameGroceryApiClient:
    """Thin async wrapper around the Endgame Grocery HTTP API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        api_key: str,
    ) -> None:
        """Initialize the API client with an injected aiohttp session."""
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Send an API request and tolerate successful responses without JSON bodies."""
        url = f"{self._base_url}/api/v1{path}"

        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers,
                json=json,
            ) as response:
                if response.status == 401:
                    raise EndgameAuthError("Invalid or missing API key")
                if response.status == 403:
                    raise EndgameForbiddenError(f"Access denied to {path}")
                if response.status == 404:
                    raise EndgameNotFoundError(f"Resource not found: {path}")
                if response.status == 204:
                    return None

                response.raise_for_status()
                try:
                    return await response.json(content_type=None)
                except ValueError:
                    return None
        except EndgameApiError:
            raise
        except aiohttp.ClientError as err:
            raise EndgameConnectionError(f"Connection error: {err}") from err

    async def get_lists(self) -> list[dict[str, Any]]:
        """Fetch all accessible grocery lists."""
        data = await self._request("GET", "/lists")
        return data["lists"]

    async def get_items(self, list_id: str) -> list[dict[str, Any]]:
        """Fetch all items for a list."""
        data = await self._request("GET", f"/lists/{list_id}/items")
        return data["items"]

    async def create_item(
        self,
        list_id: str,
        name: str,
        *,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new grocery item in a list."""
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        data = await self._request(
            "POST",
            f"/lists/{list_id}/items",
            json=body,
        )
        return data["item"]

    async def toggle_item(self, list_id: str, item_id: str) -> dict[str, Any]:
        """Toggle a grocery item's completion status."""
        data = await self._request(
            "POST",
            f"/lists/{list_id}/items/{item_id}/toggle",
        )
        return data["item"]

    async def patch_item(
        self,
        list_id: str,
        item_id: str,
        name: str,
        *,
        description: str | None | object = _UNSET,
    ) -> dict[str, Any]:
        """Rename a grocery item and optionally update its description."""
        body: dict[str, Any] = {"name": name}
        if description is not _UNSET:
            body["description"] = description
        data = await self._request(
            "PATCH",
            f"/lists/{list_id}/items/{item_id}",
            json=body,
        )
        return data["item"]

    async def delete_item(self, list_id: str, item_id: str) -> None:
        """Delete a grocery item."""
        await self._request("DELETE", f"/lists/{list_id}/items/{item_id}")
