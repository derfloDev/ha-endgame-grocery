"""Validation tests for the Endgame Grocery API client."""

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


class FakeClientError(Exception):
    """Stand-in for aiohttp.ClientError in unit tests."""


class FakeResponse:
    """Minimal response object for the API client's request helper."""

    def __init__(
        self,
        *,
        status: int,
        payload: dict | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self.status = status
        self._payload = payload
        self._raise_error = raise_error

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    def raise_for_status(self) -> None:
        """Raise the injected HTTP error, if any."""
        if self._raise_error is not None:
            raise self._raise_error

    async def json(self) -> dict:
        """Return the JSON payload for successful requests."""
        return self._payload or {}


class FakeSession:
    """Track request inputs and return queued fake responses."""

    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict[str, str], dict | None]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict | None = None,
    ) -> FakeResponse:
        """Record the request and return the next fake response."""
        self.calls.append((method, url, headers, json))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class TestEndgameGroceryApiClient(unittest.IsolatedAsyncioTestCase):
    """Verify the T-002 API client behavior and error mapping."""

    @classmethod
    def setUpClass(cls) -> None:
        """Import the API module with a fake aiohttp dependency."""
        fake_aiohttp = types.SimpleNamespace(
            ClientError=FakeClientError,
            ClientSession=object,
        )
        cls._aiohttp_patcher = patch.dict(sys.modules, {"aiohttp": fake_aiohttp})
        cls._aiohttp_patcher.start()
        sys.modules.pop("custom_components.endgame_grocery.api", None)
        cls.api = importlib.import_module("custom_components.endgame_grocery.api")

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up the injected aiohttp module after the test run."""
        sys.modules.pop("custom_components.endgame_grocery.api", None)
        cls._aiohttp_patcher.stop()

    async def test_get_lists_uses_injected_session_and_normalized_base_url(self) -> None:
        """The client should call the injected session with stripped base URL."""
        session = FakeSession(
            [FakeResponse(status=200, payload={"lists": [{"id": "list-1"}]})]
        )
        client = self.api.EndgameGroceryApiClient(
            session,
            "https://grocery.example.com/",
            "secret-key",
        )

        lists = await client.get_lists()

        self.assertEqual(lists, [{"id": "list-1"}])
        self.assertEqual(
            session.calls,
            [
                (
                    "GET",
                    "https://grocery.example.com/api/v1/lists",
                    {"X-Api-Key": "secret-key", "Content-Type": "application/json"},
                    None,
                )
            ],
        )

    async def test_item_methods_map_payloads_and_paths(self) -> None:
        """Each public item method should call the expected API endpoint."""
        session = FakeSession(
            [
                FakeResponse(status=200, payload={"items": [{"id": "item-1"}]}),
                FakeResponse(status=200, payload={"item": {"id": "item-2"}}),
                FakeResponse(status=200, payload={"item": {"id": "item-3"}}),
                FakeResponse(status=200, payload={"item": {"id": "item-4"}}),
                FakeResponse(status=204),
            ]
        )
        client = self.api.EndgameGroceryApiClient(
            session,
            "https://grocery.example.com",
            "secret-key",
        )

        items = await client.get_items("list-1")
        created = await client.create_item("list-1", "Milk")
        toggled = await client.toggle_item("list-1", "item-2")
        patched = await client.patch_item("list-1", "item-3", "Oat Milk")
        deleted = await client.delete_item("list-1", "item-4")

        self.assertEqual(items, [{"id": "item-1"}])
        self.assertEqual(created, {"id": "item-2"})
        self.assertEqual(toggled, {"id": "item-3"})
        self.assertEqual(patched, {"id": "item-4"})
        self.assertIsNone(deleted)
        self.assertEqual(
            session.calls,
            [
                (
                    "GET",
                    "https://grocery.example.com/api/v1/lists/list-1/items",
                    {"X-Api-Key": "secret-key", "Content-Type": "application/json"},
                    None,
                ),
                (
                    "POST",
                    "https://grocery.example.com/api/v1/lists/list-1/items",
                    {"X-Api-Key": "secret-key", "Content-Type": "application/json"},
                    {"name": "Milk"},
                ),
                (
                    "POST",
                    "https://grocery.example.com/api/v1/lists/list-1/items/item-2/toggle",
                    {"X-Api-Key": "secret-key", "Content-Type": "application/json"},
                    None,
                ),
                (
                    "PATCH",
                    "https://grocery.example.com/api/v1/lists/list-1/items/item-3",
                    {"X-Api-Key": "secret-key", "Content-Type": "application/json"},
                    {"name": "Oat Milk"},
                ),
                (
                    "DELETE",
                    "https://grocery.example.com/api/v1/lists/list-1/items/item-4",
                    {"X-Api-Key": "secret-key", "Content-Type": "application/json"},
                    None,
                ),
            ],
        )

    async def test_401_maps_to_auth_error(self) -> None:
        """HTTP 401 should surface as EndgameAuthError."""
        session = FakeSession([FakeResponse(status=401)])
        client = self.api.EndgameGroceryApiClient(
            session,
            "https://grocery.example.com",
            "secret-key",
        )

        with self.assertRaises(self.api.EndgameAuthError):
            await client.get_lists()

    async def test_403_maps_to_forbidden_error(self) -> None:
        """HTTP 403 should surface as EndgameForbiddenError."""
        session = FakeSession([FakeResponse(status=403)])
        client = self.api.EndgameGroceryApiClient(
            session,
            "https://grocery.example.com",
            "secret-key",
        )

        with self.assertRaises(self.api.EndgameForbiddenError):
            await client.get_items("list-1")

    async def test_404_maps_to_not_found_error(self) -> None:
        """HTTP 404 should surface as EndgameNotFoundError."""
        session = FakeSession([FakeResponse(status=404)])
        client = self.api.EndgameGroceryApiClient(
            session,
            "https://grocery.example.com",
            "secret-key",
        )

        with self.assertRaises(self.api.EndgameNotFoundError):
            await client.delete_item("list-1", "item-1")

    async def test_network_errors_map_to_connection_error(self) -> None:
        """Transport errors should surface as EndgameConnectionError."""
        session = FakeSession([FakeClientError("connection dropped")])
        client = self.api.EndgameGroceryApiClient(
            session,
            "https://grocery.example.com",
            "secret-key",
        )

        with self.assertRaises(self.api.EndgameConnectionError):
            await client.get_lists()

    async def test_http_errors_from_raise_for_status_map_to_connection_error(
        self,
    ) -> None:
        """Unexpected HTTP failures should be wrapped consistently."""
        session = FakeSession(
            [FakeResponse(status=500, raise_error=FakeClientError("server error"))]
        )
        client = self.api.EndgameGroceryApiClient(
            session,
            "https://grocery.example.com",
            "secret-key",
        )

        with self.assertRaises(self.api.EndgameConnectionError):
            await client.get_lists()


if __name__ == "__main__":
    unittest.main()
