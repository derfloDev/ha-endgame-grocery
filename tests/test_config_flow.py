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

UNSET = object()


class AbortFlowResult(Exception):
    """Exception used by the fake ConfigFlow to simulate HA abort handling."""

    def __init__(self, result: dict[str, object]) -> None:
        super().__init__("Flow aborted")
        self.result = result


class FakeInvalid(Exception):
    """Exception used by the fake voluptuous validators."""


class FakeRequiredKey:
    """Marker type for voluptuous required keys."""

    def __init__(self, key: str, default: object = UNSET) -> None:
        self.key = key
        self.default = default

    def __hash__(self) -> int:
        return hash((self.key, self.default))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FakeRequiredKey)
            and self.key == other.key
            and self.default == other.default
        )


class FakeSchema:
    """Small stand-in for voluptuous Schema."""

    def __init__(self, schema: dict[object, object]) -> None:
        self.schema = schema


class FakeFlowBase:
    """Shared fake flow behavior for config and options flows."""

    def async_create_entry(
        self,
        *,
        title: str,
        data: dict[str, object],
    ) -> dict[str, object]:
        """Return a Home Assistant-style create entry result."""
        if hasattr(self, "config_entry"):
            self.config_entry.options = data
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


class FakeConfigFlow(FakeFlowBase):
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


class FakeOptionsFlow(FakeFlowBase):
    """Minimal Home Assistant OptionsFlow base class for unit tests."""


class FakeConfigEntry:
    """Small config entry stub for options flow tests."""

    def __init__(
        self,
        *,
        data: dict[str, object] | None = None,
        options: dict[str, object] | None = None,
    ) -> None:
        self.data = data or {}
        self.options = options or {}


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


def fake_required(key: str, default: object = UNSET) -> FakeRequiredKey:
    """Create a fake voluptuous required marker."""
    return FakeRequiredKey(key, default)


def fake_coerce(target_type: type[int]) -> object:
    """Return a fake voluptuous coercion validator."""

    def validator(value: object) -> int:
        try:
            return target_type(value)
        except (TypeError, ValueError) as err:
            raise FakeInvalid(str(err)) from err

    return validator


def fake_range(*, min: int | None = None, max: int | None = None) -> object:
    """Return a fake voluptuous range validator."""

    def validator(value: int) -> int:
        if min is not None and value < min:
            raise FakeInvalid(f"{value} is lower than {min}")
        if max is not None and value > max:
            raise FakeInvalid(f"{value} is higher than {max}")
        return value

    return validator


def fake_all(*validators: object) -> object:
    """Compose fake voluptuous validators."""

    def validator(value: object) -> object:
        result = value
        for current in validators:
            result = current(result)
        return result

    return validator


class TestEndgameGroceryConfigFlow(unittest.IsolatedAsyncioTestCase):
    """Verify the T-001 config flow behavior and translation files."""

    @classmethod
    def setUpClass(cls) -> None:
        """Import the config flow module with fake HA dependencies."""
        fake_vol = types.SimpleNamespace(
            Required=fake_required,
            Schema=lambda schema: FakeSchema(schema),
            All=fake_all,
            Coerce=fake_coerce,
            Range=fake_range,
            Invalid=FakeInvalid,
        )

        fake_config_entries = types.SimpleNamespace(
            ConfigFlow=FakeConfigFlow,
            ConfigFlowResult=dict,
            OptionsFlow=FakeOptionsFlow,
            ConfigEntry=FakeConfigEntry,
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

    @staticmethod
    def _schema_fields(
        schema: FakeSchema,
    ) -> dict[str, tuple[object, object]]:
        """Return schema fields keyed by the user-facing field name."""
        return {
            key.key: (key.default, validator)
            for key, validator in schema.schema.items()
            if isinstance(key, FakeRequiredKey)
        }

    async def _run_user_step(
        self,
        flow: FakeConfigFlow,
        user_input: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Run the user step and normalize fake abort handling."""
        try:
            return await flow.async_step_user(user_input)
        except AbortFlowResult as err:
            return err.result

    async def _run_options_step(
        self,
        flow: FakeOptionsFlow,
        user_input: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Run the options step."""
        return await flow.async_step_init(user_input)

    async def test_show_form_without_input(self) -> None:
        """The initial user step should render the form schema."""
        flow = self.config_flow.EndgameGroceryConfigFlow()

        result = await self._run_user_step(flow)
        schema_fields = self._schema_fields(result["data_schema"])

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "user")
        self.assertEqual(result["errors"], {})
        self.assertEqual(set(schema_fields), {"base_url", "api_key", "scan_interval"})
        self.assertEqual(schema_fields["scan_interval"][0], 60)

    async def test_success_creates_entry_using_first_list_name(self) -> None:
        """A valid connection should create an entry titled from the first list."""
        flow = self.config_flow.EndgameGroceryConfigFlow()
        FakeApiClient.response = [{"id": "list-1", "name": "Weekly Shopping"}]

        result = await self._run_user_step(
            flow,
            {
                "base_url": "https://grocery.example.com/",
                "api_key": "secret-key",
                "scan_interval": 60,
            },
        )

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "Weekly Shopping")
        self.assertEqual(
            result["data"],
            {
                "base_url": "https://grocery.example.com/",
                "api_key": "secret-key",
                "scan_interval": 60,
            },
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
            {
                "base_url": "https://grocery.example.com",
                "api_key": "secret-key",
                "scan_interval": 60,
            },
        )

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "https://grocery.example.com")

    async def test_invalid_auth_maps_to_form_error(self) -> None:
        """Authentication failures should show the invalid_auth error."""
        flow = self.config_flow.EndgameGroceryConfigFlow()
        FakeApiClient.error = self.EndgameAuthError("bad key")

        result = await self._run_user_step(
            flow,
            {
                "base_url": "https://grocery.example.com",
                "api_key": "secret-key",
                "scan_interval": 60,
            },
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "invalid_auth"})

    async def test_connection_error_maps_to_form_error(self) -> None:
        """Connection failures should show the cannot_connect error."""
        flow = self.config_flow.EndgameGroceryConfigFlow()
        FakeApiClient.error = self.EndgameConnectionError("offline")

        result = await self._run_user_step(
            flow,
            {
                "base_url": "https://grocery.example.com",
                "api_key": "secret-key",
                "scan_interval": 60,
            },
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "cannot_connect"})

    async def test_duplicate_server_aborts(self) -> None:
        """A duplicate normalized base URL should abort the flow."""
        flow = self.config_flow.EndgameGroceryConfigFlow()
        flow._configured_ids.add("https://grocery.example.com")

        result = await self._run_user_step(
            flow,
            {
                "base_url": "https://grocery.example.com/",
                "api_key": "secret-key",
                "scan_interval": 60,
            },
        )

        self.assertEqual(result, {"type": "abort", "reason": "already_configured"})

    async def test_scan_interval_below_range_maps_to_form_error(self) -> None:
        """Scan intervals below the supported range should be rejected."""
        flow = self.config_flow.EndgameGroceryConfigFlow()

        result = await self._run_user_step(
            flow,
            {
                "base_url": "https://grocery.example.com",
                "api_key": "secret-key",
                "scan_interval": 9,
            },
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "invalid_scan_interval"})
        self.assertEqual(FakeApiClient.instances, [])

    async def test_scan_interval_above_range_maps_to_form_error(self) -> None:
        """Scan intervals above the supported range should be rejected."""
        flow = self.config_flow.EndgameGroceryConfigFlow()

        result = await self._run_user_step(
            flow,
            {
                "base_url": "https://grocery.example.com",
                "api_key": "secret-key",
                "scan_interval": 601,
            },
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "invalid_scan_interval"})
        self.assertEqual(FakeApiClient.instances, [])

    async def test_unexpected_error_maps_to_unknown(self) -> None:
        """Unexpected exceptions should show the generic unknown error."""
        flow = self.config_flow.EndgameGroceryConfigFlow()
        FakeApiClient.error = RuntimeError("unexpected")

        result = await self._run_user_step(
            flow,
            {
                "base_url": "https://grocery.example.com",
                "api_key": "secret-key",
                "scan_interval": 60,
            },
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "unknown"})

    async def test_options_flow_prefills_current_interval(self) -> None:
        """The options form should show the current scan interval."""
        entry = FakeConfigEntry(
            data={"scan_interval": 30},
            options={"scan_interval": 45},
        )
        flow = self.config_flow.EndgameGroceryConfigFlow.async_get_options_flow(entry)

        result = await self._run_options_step(flow)
        schema_fields = self._schema_fields(result["data_schema"])

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "init")
        self.assertEqual(result["errors"], {})
        self.assertEqual(schema_fields["scan_interval"][0], 45)

    async def test_options_flow_saves_scan_interval(self) -> None:
        """The options flow should store the chosen scan interval in entry options."""
        entry = FakeConfigEntry(data={"scan_interval": 30})
        flow = self.config_flow.EndgameGroceryConfigFlow.async_get_options_flow(entry)

        result = await self._run_options_step(flow, {"scan_interval": 120})

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"], {"scan_interval": 120})
        self.assertEqual(entry.options, {"scan_interval": 120})

    async def test_options_flow_rejects_out_of_range_interval(self) -> None:
        """The options flow should return a localized error for invalid values."""
        entry = FakeConfigEntry(data={"scan_interval": 30})
        flow = self.config_flow.EndgameGroceryConfigFlow.async_get_options_flow(entry)

        result = await self._run_options_step(flow, {"scan_interval": 601})

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "init")
        self.assertEqual(result["errors"], {"base": "invalid_scan_interval"})

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
        self.assertEqual(strings["config"]["error"]["invalid_scan_interval"], "Scan interval must be between 10 and 600 seconds.")
        self.assertEqual(strings["options"]["step"]["init"]["title"], "Update Endgame Grocery options")
        self.assertEqual(strings["options"]["step"]["init"]["data"]["scan_interval"], "Scan interval")
        self.assertEqual(strings["options"]["error"]["invalid_scan_interval"], "Scan interval must be between 10 and 600 seconds.")


if __name__ == "__main__":
    unittest.main()
