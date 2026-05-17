"""Config flow for Endgame Grocery."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EndgameAuthError, EndgameConnectionError, EndgameGroceryApiClient
from .const import CONF_API_KEY, CONF_BASE_URL, DOMAIN

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
        self,
        user_input: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        """Handle the user configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL]

            await self.async_set_unique_id(base_url.rstrip("/"))
            self._abort_if_unique_id_configured()

            try:
                client = EndgameGroceryApiClient(
                    async_get_clientsession(self.hass),
                    base_url,
                    user_input[CONF_API_KEY],
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
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
