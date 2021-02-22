"""Config flow to configure the NiceHash integration."""
import logging
from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from voluptuous.validators import All, Range
from custom_components.nicehash.const import (
    CONFIG_ENTRY_VERSION,
    CONFIG_FIAT,
    CONFIG_KEY,
    CONFIG_NAME,
    CONFIG_ORG_ID,
    CONFIG_SECRET,
    CONFIG_UPDATE_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    NICEHASH_API_ENDPOINT,
)
from custom_components.nicehash.nicehash import NiceHashPrivateAPI

_LOGGER = logging.getLogger(__name__)


DATA_SCHEMA = {
    vol.Required(CONFIG_NAME): str,
    vol.Required(CONFIG_KEY): str,
    vol.Required(CONFIG_SECRET): str,
    vol.Required(CONFIG_ORG_ID): str,
    vol.Required(CONFIG_FIAT, default="USD"): str,
    vol.Required(CONFIG_UPDATE_INTERVAL, default=DEFAULT_SCAN_INTERVAL_MINUTES): All(
        int, Range(min=1, max=30)
    ),
}


async def validate_input(data: dict):
    """Validate the user input allows us to connect.
    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    private = NiceHashPrivateAPI(
        NICEHASH_API_ENDPOINT,
        data[CONFIG_ORG_ID],
        data[CONFIG_KEY],
        data[CONFIG_SECRET],
    )
    await private.get_mining_address()
    return


class NiceHashConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """NiceHash config flow"""

    VERSION = CONFIG_ENTRY_VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                await validate_input(user_input)
                return self.async_create_entry(
                    title=user_input[CONFIG_NAME], data=user_input
                )
            except Exception as err:
                errors["key"] = "invalid_cred"
                _LOGGER.exception(str(err))

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(DATA_SCHEMA), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return NiceHashOptionsFlowHandler(config_entry)


class NiceHashOptionsFlowHandler(config_entries.OptionsFlow):
    """Class for the Options Handler"""

    def __init__(self, config_entry) -> None:
        super().__init__()
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONFIG_UPDATE_INTERVAL,
                        default=self.config_entry.data.get(CONFIG_UPDATE_INTERVAL),
                    ): All(int, Range(min=1, max=30))
                }
            ),
        )
