"""Support for NiceHash data."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.nicehash.nicehash import NiceHashPrivateAPI
from custom_components.nicehash.const import (
    API,
    NICEHASH_API_ENDPOINT,
    DOMAIN,
    SENSORS,
    SENSOR_DATA_COORDINATOR,
    UNSUB,
)
from custom_components.nicehash.common import NiceHashSensorDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, _):  # config: dict
    """Set up NiceHash sensor based on a config entry."""
    hass.data.setdefault(DOMAIN, {})

    return True


@callback
async def _async_send_update_options_signal(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Send update event when NiceHash Sensor config entry is updated."""
    async_dispatcher_send(hass, config_entry.entry_id, config_entry)


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up NiceHash sensor based on a config entry."""
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    api = NiceHashPrivateAPI(
        NICEHASH_API_ENDPOINT,
        entry.data["org_id"],
        entry.data["key"],
        entry.data["secret"],
    )

    coordinator = NiceHashSensorDataUpdateCoordinator(hass, api)

    try:
        await coordinator.async_refresh()
    except Exception as err:
        raise ConfigEntryNotReady from err

    unsub = entry.add_update_listener(_async_send_update_options_signal)
    hass.data[DOMAIN][entry.entry_id].update(
        {
            SENSOR_DATA_COORDINATOR: coordinator,
            API: api,
            UNSUB: [unsub],
            SENSORS: [],
        }
    )
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


async def async_unload_entry(hass, config_entry: ConfigEntry):
    """Unload a config entry."""
    for unsub in hass.data[DOMAIN][config_entry.entry_id][UNSUB]:
        unsub()

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, platform)
                for platform in PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_listener(hass, config_entry):
    """Reload device tracker if change option."""
    await hass.config_entries.async_reload(config_entry.entry_id)
