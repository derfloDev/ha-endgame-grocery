"""Validation tests for the Endgame Grocery config flow."""

from __future__ import annotations

import importlib
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class AbortFlowResult(Exception):
    """Exception used by the fake ConfigFlow to simulate HA abort handling."""

    def __init__(self, result: dict[str, object]) -> None:
        super().__init__("Flow aborted")
        self.result = result


class FakeRequiredKey(str):
    """Marker type for voluptuous required keys."""


class FakeSchema:
    """Small stand-in for voluptuous Schema."""

    def __init__(self, schema: dict[object, object]) -> None:
        self.schema = schema


class FakeConfigFlow:
    """Minimal Home Assistant ConfigFlow base class for unit tests."""

    def __init_subclass__(cls, *, domain: str | None = None, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls.DOMAIN = domain

    def __init__(self) -> None:
        self.hass = object()
        self._configured_ids: set[str] = set()
        self._unique_id: str | None = None

    async def async_set_unique_id(self, unique_id: str) -> None:
        """Store the normalized unique id."""
        self._unique_id = unique_id

    def _abort_if_unique_id_configured(self) -> None:
        """Abort if the server is already configured."""
        if self._unique_id in self._configured_ids:
            raise AbortFlowResult(self.async_abort(reason="already_configured"))

    def async_abort(self, *, reason: str) -> dict[str, str]:
        """Return a Home Assistant-style abort result."""
        return {"type": "abort", "reason": reason}

    def async_create_entry(
        self,
        *,
        title: str,
        data: dict[str, str],
    ) -> dict[str, object]:
        """Return a Home Assistant-style create entry result."""
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: FakeSchema,
        errors: dict[str, str],
    ) -> dict[str, object]:
        """Return a Home Assistant-style form result."""
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors,
        }


class FakeApiClient:
    """Configurable stand-in for the Endgame API client."""

    response: list[dict[str, str]] = []
    error: Exception | None = None
    instances: list[FakeApiClient] = []

    def __init__(self, session: object, base_url: str, api_key: str) -> None:
        self.session = session
        self.base_url = base_url
        self.api_key = api_key
        self.__class__.instances.append(self)

    async def get_lists(self) -> list[dict[str, str]]:
        """Return the configured list payload or raise the configured error."""
        if self.__class__.error is not None:
            raise self.__class__.error
        return self.__class__.response


class TestEndgameGroceryConfigFlow(unittest.IsolatedAsyncioTestCase):
    """Verify the T-003 config flow behavior and translation files."""

    @classmethod
    def setUpClass(cls) -> None:
        """Import the config flow module with fake HA dependencies."""
        fake_vol = types.SimpleNamespace(
            Required=lambda key: FakeRequiredKey(key),
            Schema=lambda schema: FakeSchema(schema),
        )

        fake_config_entries = types.SimpleNamespace(
            ConfigFlow=FakeConfigFlow,
            ConfigFlowResult=dict,
        )

        cls._session_sentinel = object()
        fake_aiohttp_client = types.SimpleNamespace(
            async_get_clientsession=lambda hass: cls._session_sentinel
        )

        fake_api = types.SimpleNamespace(
            EndgameGroceryApiClient=FakeApiClient,
            EndgameAuthError=type("EndgameAuthError", (Exception,), {}),
            EndgameConnectionError=type("EndgameConnectionError", (Exception,), {}),
        )

        cls._module_patcher = patch.dict(
            sys.modules,
            {
                "voluptuous": fake_vol,
                "homeassistant": types.ModuleType("homeassistant"),
                "homeassistant.config_entries": fake_config_entries,
                "homeassistant.helpers": types.ModuleType("homeassistant.helpers"),
                "homeassistant.helpers.aiohttp_client": fake_aiohttp_client,
                "custom_components.endgame_grocery.api": fake_api,
            },
        )
        cls._module_patcher.start()
        sys.modules.pop("custom_components.endgame_grocery.config_flow", None)
        cls.config_flow = importlib.import_module(
            "custom_components.endgame_grocery.config_flow"
        )
        cls.EndgameAuthError = fake_api.EndgameAuthError
        cls.EndgameConnectionError = fake_api.EndgameConnectionError

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up fake dependency modules."""
        sys.modules.pop("custom_components.endgame_grocery.config_flow", None)
        cls._module_patcher.stop()

    def setUp(self) -> None:
        """Reset fake API behavior before each test."""
        FakeApiClient.response = []
        FakeApiClient.error = None
        FakeApiClient.instances = []

    async def _run_user_step(
        self,
        flow: FakeConfigFlow,
        user_input: dict[str, str] | None = None,
    ) -> dict[str, object]:
        """Run the user step and normalize fake abort handling."""
        try:
            return await flow.async_step_user(user_input)
        except AbortFlowResult as err:
            return err.result

    async def test_show_form_without_input(self) -> None:
        """The initial user step should render the form schema."""
        flow = self.config_flow.EndgameGroceryConfigFlow()

        result = await self._run_user_step(flow)

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "user")
        self.assertEqual(result["errors"], {})
        self.assertEqual(
            result["data_schema"].schema,
            {
                "base_url": str,
                "api_key": str,
            },
        )

    async def test_success_creates_entry_using_first_list_name(self) -> None:
        """A valid connection should create an entry titled from the first list."""
        flow = self.config_flow.EndgameGroceryConfigFlow()
        FakeApiClient.response = [{"id": "list-1", "name": "Weekly Shopping"}]

        result = await self._run_user_step(
            flow,
            {"base_url": "https://grocery.example.com/", "api_key": "secret-key"},
        )

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "Weekly Shopping")
        self.assertEqual(
            result["data"],
            {"base_url": "https://grocery.example.com/", "api_key": "secret-key"},
        )
        self.assertEqual(flow._unique_id, "https://grocery.example.com")
        self.assertIs(FakeApiClient.instances[0].session, self._session_sentinel)
        self.assertEqual(
            FakeApiClient.instances[0].base_url,
            "https://grocery.example.com/",
        )
        self.assertEqual(FakeApiClient.instances[0].api_key, "secret-key")

    async def test_success_falls_back_to_base_url_when_no_lists(self) -> None:
        """An empty list response should fall back to the configured base URL."""
        flow = self.config_flow.EndgameGroceryConfigFlow()
        FakeApiClient.response = []

        result = await self._run_user_step(
            flow,
            {"base_url": "https://grocery.example.com", "api_key": "secret-key"},
        )

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "https://grocery.example.com")

    async def test_invalid_auth_maps_to_form_error(self) -> None:
        """Authentication failures should show the invalid_auth error."""
        flow = self.config_flow.EndgameGroceryConfigFlow()
        FakeApiClient.error = self.EndgameAuthError("bad key")

        result = await self._run_user_step(
            flow,
            {"base_url": "https://grocery.example.com", "api_key": "secret-key"},
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "invalid_auth"})

    async def test_connection_error_maps_to_form_error(self) -> None:
        """Connection failures should show the cannot_connect error."""
        flow = self.config_flow.EndgameGroceryConfigFlow()
        FakeApiClient.error = self.EndgameConnectionError("offline")

        result = await self._run_user_step(
            flow,
            {"base_url": "https://grocery.example.com", "api_key": "secret-key"},
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "cannot_connect"})

    async def test_duplicate_server_aborts(self) -> None:
        """A duplicate normalized base URL should abort the flow."""
        flow = self.config_flow.EndgameGroceryConfigFlow()
        flow._configured_ids.add("https://grocery.example.com")

        result = await self._run_user_step(
            flow,
            {"base_url": "https://grocery.example.com/", "api_key": "secret-key"},
        )

        self.assertEqual(result, {"type": "abort", "reason": "already_configured"})

    async def test_unexpected_error_maps_to_unknown(self) -> None:
        """Unexpected exceptions should show the generic unknown error."""
        flow = self.config_flow.EndgameGroceryConfigFlow()
        FakeApiClient.error = RuntimeError("unexpected")

        result = await self._run_user_step(
            flow,
            {"base_url": "https://grocery.example.com", "api_key": "secret-key"},
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "unknown"})

    def test_strings_and_translation_files_match(self) -> None:
        """The English translation must match strings.json exactly."""
        strings_path = (
            REPO_ROOT / "custom_components" / "endgame_grocery" / "strings.json"
        )
        translation_path = (
            REPO_ROOT
            / "custom_components"
            / "endgame_grocery"
            / "translations"
            / "en.json"
        )

        self.assertTrue(strings_path.exists())
        self.assertTrue(translation_path.exists())

        strings = json.loads(strings_path.read_text(encoding="utf-8"))
        translation = json.loads(translation_path.read_text(encoding="utf-8"))

        self.assertEqual(strings, translation)
        self.assertEqual(strings["config"]["step"]["user"]["title"], "Connect to Endgame Grocery")


if __name__ == "__main__":
    unittest.main()
