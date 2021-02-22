"""Support for NiceHash data."""
import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.nicehash.nicehash import NiceHashPrivateAPI
from custom_components.nicehash.const import (
    API,
    CONFIG_FIAT,
    CONFIG_KEY,
    CONFIG_ORG_ID,
    CONFIG_SECRET,
    CONFIG_UPDATE_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    NICEHASH_API_ENDPOINT,
    DOMAIN,
    SENSORS,
    SENSOR_DATA_COORDINATOR,
    UNSUB,
)
from custom_components.nicehash.common import NiceHashSensorDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "switch"]


async def async_setup(hass: HomeAssistant, _):  # config: dict
    """Set up NiceHash sensor based on a config entry."""
    hass.data.setdefault(DOMAIN, {})

    return True


async def _update_coordinator(hass: HomeAssistant, config_entry: ConfigEntry):
    coordinator = hass.data[DOMAIN][config_entry.entry_id].get(SENSOR_DATA_COORDINATOR)
    if coordinator is not None and config_entry.data.get(
        CONFIG_UPDATE_INTERVAL
    ) != config_entry.options.get(CONFIG_UPDATE_INTERVAL):
        coordinator.update_interval = timedelta(
            minutes=config_entry.options[CONFIG_UPDATE_INTERVAL]
        )
        await coordinator.async_request_refresh()
        new_data = config_entry.data.copy()
        new_data[CONFIG_UPDATE_INTERVAL] = config_entry.options.get(
            CONFIG_UPDATE_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        hass.config_entries.async_update_entry(
            entry=config_entry,
            unique_id=config_entry.entry_id,
            data=new_data,
        )


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up NiceHash sensor based on a config entry."""

    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    api = NiceHashPrivateAPI(
        NICEHASH_API_ENDPOINT,
        entry.data[CONFIG_ORG_ID],
        entry.data[CONFIG_KEY],
        entry.data[CONFIG_SECRET],
    )

    coordinator = NiceHashSensorDataUpdateCoordinator(
        hass, api, entry.data[CONFIG_UPDATE_INTERVAL], entry.data[CONFIG_FIAT]
    )

    try:
        await api.get_mining_address()
    except Exception as err:
        raise ConfigEntryNotReady from err

    unsub = entry.add_update_listener(_update_coordinator)
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


async def async_migrate_entry(_, config_entry):
    """Migrate old entry."""
    data = config_entry.data
    version = config_entry.version

    if version == 1:
        new_data = {**data}
        new_data[CONFIG_UPDATE_INTERVAL] = DEFAULT_SCAN_INTERVAL_MINUTES
        config_entry.data = {**new_data}
        version = config_entry.version = 2

    _LOGGER.info(
        "Migration of NiceHash config to version %s successful", config_entry.version
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
