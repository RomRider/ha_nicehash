"""Config flow to configure the NiceHash integration."""
import logging
from homeassistant import config_entries, core
import voluptuous as vol
from .const import DOMAIN, NICEHASH_API_ENDPOINT
from .NiceHash import NiceHashPrivateAPI

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = {
    vol.Required("name"): str,
    vol.Required("key"): str,
    vol.Required("secret"): str,
    vol.Required("org_id"): str,
}


async def validate_input(hass: core.HomeAssistant, data: dict):
    """Validate the user input allows us to connect.
    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    private = NiceHashPrivateAPI(
        NICEHASH_API_ENDPOINT, data["org_id"], data["key"], data["secret"]
    )
    private.get_mining_address()
    return


class NiceHashConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
                return self.async_create_entry(
                    title=user_input["name"], data=user_input
                )
            except Exception as e:
                errors["key"] = "invalid_cred"
                _LOGGER.exception(str(e))

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(DATA_SCHEMA), errors=errors
        )
