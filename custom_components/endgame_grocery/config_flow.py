"""Config flow for Endgame Grocery."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EndgameAuthError, EndgameConnectionError, EndgameGroceryApiClient
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)

SCAN_INTERVAL_VALIDATOR = vol.All(vol.Coerce(int), vol.Range(min=10, max=600))


def _build_user_data_schema(
    scan_interval: int = DEFAULT_SCAN_INTERVAL_SECONDS,
) -> vol.Schema:
    """Build the setup form schema."""
    return vol.Schema(
        {
            vol.Required(CONF_BASE_URL): str,
            vol.Required(CONF_API_KEY): str,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=scan_interval,
            ): SCAN_INTERVAL_VALIDATOR,
        }
    )


def _build_options_schema(scan_interval: int) -> vol.Schema:
    """Build the options form schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=scan_interval,
            ): SCAN_INTERVAL_VALIDATOR,
        }
    )


STEP_USER_DATA_SCHEMA = _build_user_data_schema()


def _validate_scan_interval(user_input: dict[str, object]) -> int:
    """Normalize the configured scan interval."""
    return SCAN_INTERVAL_VALIDATOR(user_input[CONF_SCAN_INTERVAL])


class EndgameGroceryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Endgame Grocery config flow."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, object] | None = None,
    ) -> ConfigFlowResult:
        """Handle the user configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                scan_interval = _validate_scan_interval(user_input)
            except vol.Invalid:
                errors["base"] = "invalid_scan_interval"
            else:
                normalized_input = {**user_input, CONF_SCAN_INTERVAL: scan_interval}
                base_url = str(normalized_input[CONF_BASE_URL])

                await self.async_set_unique_id(base_url.rstrip("/"))
                self._abort_if_unique_id_configured()

                try:
                    client = EndgameGroceryApiClient(
                        async_get_clientsession(self.hass),
                        base_url,
                        str(normalized_input[CONF_API_KEY]),
                    )
                    lists = await client.get_lists()
                except EndgameAuthError:
                    errors["base"] = "invalid_auth"
                except EndgameConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001
                    errors["base"] = "unknown"
                else:
                    title = lists[0]["name"] if lists else base_url
                    return self.async_create_entry(title=title, data=normalized_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class OptionsFlowHandler(OptionsFlow):
    """Handle Endgame Grocery options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Store the config entry for the options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, object] | None = None,
    ) -> ConfigFlowResult:
        """Handle the options step."""
        errors: dict[str, str] = {}
        current_interval = int(
            self.config_entry.options.get(
                CONF_SCAN_INTERVAL,
                self.config_entry.data.get(
                    CONF_SCAN_INTERVAL,
                    DEFAULT_SCAN_INTERVAL_SECONDS,
                ),
            )
        )

        if user_input is not None:
            try:
                scan_interval = _validate_scan_interval(user_input)
            except vol.Invalid:
                errors["base"] = "invalid_scan_interval"
            else:
                return self.async_create_entry(
                    title="",
                    data={CONF_SCAN_INTERVAL: scan_interval},
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(current_interval),
            errors=errors,
        )
