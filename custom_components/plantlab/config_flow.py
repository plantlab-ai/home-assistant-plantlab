import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PlantLabApiClient, PlantLabAuthError, PlantLabConnectionError
from .const import CONF_API_KEY, CONF_HOST, DEFAULT_HOST, DOMAIN


class PlantLabConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_reauth(self, entry_data):
        """Ask the user to replace an invalid API key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Validate and save a replacement API key."""
        entry = self._get_reauth_entry()

        errors = {}
        if user_input is not None:
            client = PlantLabApiClient(
                session=async_get_clientsession(self.hass),
                api_key=user_input[CONF_API_KEY],
                host=entry.data.get(CONF_HOST, DEFAULT_HOST),
            )
            try:
                await client.async_validate()
            except PlantLabAuthError:
                errors["base"] = "invalid_auth"
            except PlantLabConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_API_KEY: user_input[CONF_API_KEY]},
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            client = PlantLabApiClient(
                session=async_get_clientsession(self.hass),
                api_key=user_input[CONF_API_KEY],
                host=user_input.get(CONF_HOST, DEFAULT_HOST),
            )
            try:
                await client.async_validate()
            except PlantLabAuthError:
                errors["base"] = "invalid_auth"
            except PlantLabConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="PlantLab",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Optional(CONF_HOST, default=DEFAULT_HOST): str,
                }
            ),
            errors=errors,
        )
