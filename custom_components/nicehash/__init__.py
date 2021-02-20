"""Support for NiceHash data."""
import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.exceptions import ConfigEntryNotReady
from custom_components.nicehash.NiceHash import NiceHashPrivateAPI
from .const import NICEHASH_API_ENDPOINT, DOMAIN


_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, _):  # config: dict
    """Set up NiceHash sensor based on a config entry."""
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up NiceHash sensor based on a config entry."""
    hass.data.setdefault(DOMAIN, {})
    api = NiceHashPrivateAPI(
        NICEHASH_API_ENDPOINT,
        entry.data["org_id"],
        entry.data["key"],
        entry.data["secret"],
    )
    hass.data[DOMAIN][entry.entry_id] = api
    try:
        await api.get_mining_address()
    except Exception as err:
        raise ConfigEntryNotReady from err

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_listener(hass, config_entry):
    """Reload device tracker if change option."""
    await hass.config_entries.async_reload(config_entry.entry_id)
