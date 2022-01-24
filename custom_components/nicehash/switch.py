"""Support for NiceHash sensors."""

import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.core import callback

# from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.helpers.typing import HomeAssistantType

from custom_components.nicehash.nicehash import NiceHashPrivateAPI
from custom_components.nicehash.common import NiceHashSensorDataUpdateCoordinator
from custom_components.nicehash.const import (
    API,
    DOMAIN,
    RIGS_OBJ,
    SENSOR_DATA_COORDINATOR,
    SWITCH_ASYNC_UPDATE_AFTER_SECONDS,
    UNSUB,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM = "switch"


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the NiceHash sensor using config entry."""
    coordinator: NiceHashSensorDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ][SENSOR_DATA_COORDINATOR]

    @callback
    def _update_entities():
        if not hasattr(_update_entities, "dev"):
            _update_entities.dev = []
        if not coordinator.last_update_success:
            return

        new_dev = []

        for rig in coordinator.data.get(RIGS_OBJ).get("miningRigs"):
            rig_id = rig.get("rigId")
            rig_switch = NiceHashRigSwitch(
                hass.data[DOMAIN][config_entry.entry_id][API],
                coordinator,
                config_entry,
                rig_id,
            )
            if rig_switch.unique_id not in _update_entities.dev:
                new_dev.append(rig_switch)
                _update_entities.dev.append(rig_switch.unique_id)

            for dev in rig.get("devices"):
                device_id = dev.get("id")
                device_switch = NiceHashDeviceSwitch(
                    hass.data[DOMAIN][config_entry.entry_id][API],
                    coordinator,
                    config_entry,
                    rig_id,
                    device_id,
                )
                if device_switch.unique_id not in _update_entities.dev:
                    new_dev.append(device_switch)
                    _update_entities.dev.append(device_switch.unique_id)

        async_add_entities(new_dev)

    unsub = coordinator.async_add_listener(_update_entities)
    hass.data[DOMAIN][config_entry.entry_id][UNSUB].append(unsub)
    await coordinator.async_refresh()


class NiceHashRigSwitch(CoordinatorEntity, ToggleEntity):
    """Class describing a rig switch"""

    DOMAIN = PLATFORM

    def __init__(
        self, api: NiceHashPrivateAPI, coordinator, config_entry, rigId
    ) -> None:
        super().__init__(coordinator)
        self._rig_id = rigId
        self._config_entry = config_entry
        self._data_type = RIGS_OBJ
        self._api = api

    @property
    def available(self):
        """Return availability"""
        rig = self.get_rig()
        return (
            self.coordinator.last_update_success
            and rig is not None
            and rig.get("minerStatus", "UNKNOWN")
            not in ["DISABLED", "TRANSFERED", "UNKNOWN", "OFFLINE"]
        )

    def get_rig(self):
        """Return the rig object."""
        rig = None
        for rig_entry in self.coordinator.data[self._data_type].get("miningRigs", []):
            if rig_entry.get("rigId") == self._rig_id:
                rig = rig_entry
        return rig

    @property
    def name(self):
        rig = self.get_rig()
        if rig is not None:
            name = f"NH - {rig.get('name')} - Power"
            return name
        return None

    @property
    def unique_id(self):
        unique_id = f"nh-{self._rig_id}-power"
        return unique_id

    @property
    def device_info(self):
        """Information about this entity/device."""
        rig = self.get_rig()
        return {
            "identifiers": {(DOMAIN, self._rig_id)},
            # If desired, the name for the device could be different to the entity
            "name": rig.get("name"),
            "sw_version": rig.get("softwareVersions"),
            "model": rig.get("softwareVersions"),
            "manufacturer": "NiceHash",
        }

    @property
    def is_on(self):
        """Return true if switch is on."""
        rig = self.get_rig()
        if rig is not None:
            status = rig.get("minerStatus", "UNKNOWN")
            if status in ["BENCHMARKING", "MINING"]:
                return True
        return False

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        try:
            await self._api.set_rig_status(self._rig_id, True)
            await asyncio.sleep(SWITCH_ASYNC_UPDATE_AFTER_SECONDS)
        except Exception as err:
            _LOGGER.error("Failed to set the status of '%s': %s", self.entity_id, err)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        try:
            await self._api.set_rig_status(self._rig_id, False)
            await asyncio.sleep(SWITCH_ASYNC_UPDATE_AFTER_SECONDS)
        except Exception as err:
            _LOGGER.error("Failed to set the status of '%s': %s", self.entity_id, err)
        await self.coordinator.async_request_refresh()




class NiceHashDeviceSwitch(CoordinatorEntity, ToggleEntity):
    """Class describing a device switch"""

    DOMAIN = PLATFORM

    def __init__(
            self, api: NiceHashPrivateAPI, coordinator, config_entry, rigId, deviceId
    ) -> None:
        super().__init__(coordinator)
        self._rig_id = rigId
        self._device_id = deviceId
        self._config_entry = config_entry
        self._data_type = RIGS_OBJ
        self._api = api

    @property
    def available(self):
        """Return availability"""
        device = self.get_device()
        return (
                self.coordinator.last_update_success
                and device is not None
                and device.get("status", {}).get("enumName", "UNKNOWN")
                not in ["TRANSFERED", "UNKNOWN", "OFFLINE"]
        )

    def get_rig(self):
        """Return the rig object."""
        rig = None
        for rig_entry in self.coordinator.data[self._data_type].get("miningRigs", []):
            if rig_entry.get("rigId") == self._rig_id:
                rig = rig_entry
        return rig

    def get_device(self):
        """Return device object."""

        for rig_entry in self.coordinator.data[self._data_type].get("miningRigs", []):
            if rig_entry.get("rigId") == self._rig_id:
                for device_entry in rig_entry.get("devices"):
                    if device_entry.get("id") == self._device_id:
                        return device_entry

    @property
    def name(self):
        rig = self.get_rig()
        device = self.get_device()
        if rig is not None and device is not None:
            name = f"NH - {rig.get('name')} - {device.get('name')} - Power"
            return name
        return None

    @property
    def unique_id(self):
        unique_id = f"nh-{self._rig_id}-{self._device_id}-power"
        return unique_id

    @property
    def device_info(self):
        """Information about this entity/device."""
        rig = self.get_rig()
        device = self.get_device()
        return {
            "identifiers": {(DOMAIN, self._rig_id)},
            # If desired, the name for the device could be different to the entity
            "rig_name": rig.get("name"),
            "device_name": device.get("name"),
            "manufacturer": "NiceHash",
        }

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        rig = self.get_rig()
        device = self.get_device()

        return {
            "rig_name": rig.get("name"),
            "device_name": device.get("name"),
            "temperature": device.get("temperature"),
            "load": device.get("load"),
            "fan_speed": device.get("revolutionsPerMinute"),
            "fan_speed_percentage": device.get("revolutionsPerMinutePercentage"),
            "powerUsage": device.get("powerUsage"),
            "powerMode": device.get("intensity", {}).get("enumName"),
        }

    @property
    def is_on(self):
        """Return true if switch is on."""
        device = self.get_device()
        if device is not None:
            status = device.get("status", {}).get("enumName", "UNKNOWN")
            if status in ["BENCHMARKING", "MINING"]:
                return True
        return False

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        try:
            await self._api.set_device_status(self._rig_id, self._device_id, True)
            await asyncio.sleep(SWITCH_ASYNC_UPDATE_AFTER_SECONDS)
        except Exception as err:
            _LOGGER.error("Failed to set the status of '%s': %s", self.entity_id, err)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        try:
            await self._api.set_device_status(self._rig_id, self._device_id, False)
            await asyncio.sleep(SWITCH_ASYNC_UPDATE_AFTER_SECONDS)
        except Exception as err:
            _LOGGER.error("Failed to set the status of '%s': %s", self.entity_id, err)
        await self.coordinator.async_request_refresh()
