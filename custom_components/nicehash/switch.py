"""Support for NiceHash switches."""

import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv, entity_platform, service
import voluptuous as vol

from homeassistant.exceptions import HomeAssistantError

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
    SERVICE_SET_POWER_MODE
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

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_POWER_MODE, { vol.Required("power_mode"): cv.string}, "set_power_mode",
    )

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

            rig_devices = rig.get("devices")
            if rig_devices:
                for dev in rig_devices:
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

    async def set_power_mode(self, power_mode):
        # Not implemented for RigSwitch
        raise HomeAssistantError("Rig PowerMode service not supported")


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

        if "nhqm" in device:
            # NiceHash QuickMiner
            data = self.parse_nhqm_string(device.get("nhqm"))
            power_mode_raw = data.get("OP")
            opa = data.get("OPA", {})
            power_mode = dict(map(reversed, opa.items())).get(power_mode_raw, "UNKNOWN")
            supported_power_modes = list(opa.keys())
        else:
            # Regular NiceHash miner
            power_mode = device.get("powerMode", {}).get("enumName", "UNKNOWN")
            supported_power_modes = ["HIGH", "MEDIUM", "LOW"]

        return {
            "rig_name": rig.get("name"),
            "device_name": device.get("name"),
            "temperature": self.normalize_value(device.get("temperature")),
            "load": self.normalize_value(device.get("load")),
            "fan_speed": device.get("revolutionsPerMinute"),
            "fan_speed_percentage": device.get("revolutionsPerMinutePercentage"),
            "power_usage": device.get("powerUsage"),
            "power_mode": power_mode,
            "supported_power_modes": ", ".join(supported_power_modes),
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

    async def set_power_mode(self, power_mode):
        """Set a device power mode"""
        power_mode = power_mode.upper()
        rig = self.get_rig()
        device = self.get_device()

        rig_id = rig.get("rigId")
        device_id = device.get("id")

        # Regular NiceHash miner
        version = None
        power_mode_id = None
        supported_power_modes = ["HIGH", "MEDIUM", "LOW"]

        # NiceHash QuickMiner alternative logic
        nhqm = device.get("nhqm")
        if nhqm:
            data = self.parse_nhqm_string(nhqm)

            version = data.get("V")
            op_supported_power_modes = data.get("OPA", {})
            power_mode_id = op_supported_power_modes.get(power_mode)
            supported_power_modes = list(op_supported_power_modes.keys())

        if power_mode not in supported_power_modes:
            raise HomeAssistantError(f"Unsupported power mode [{power_mode}]. "
                                     f"Supported power modes for this device are {', '.join(supported_power_modes)}")

        if nhqm and version is None:
            _LOGGER.error(f"Could not determine version! Report this message to developer. nhqm_string: {nhqm}")
            raise HomeAssistantError(f"Internal error, cannot determine version for power mode [{power_mode}], check the logs.")
        if nhqm and power_mode_id is None:
            _LOGGER.error(f"Could not determine power_mode_id for requested power mode {power_mode}! Report this message to developer. "
                          f"nhqm_string: {nhqm}")
            raise HomeAssistantError(f"Internal error, cannot determine power_mode_id for power mode [{power_mode}], check the logs.")

        if nhqm:
            response = await self._api.set_power_mode_nhqm(rig_id, device_id, version, power_mode_id)
        else:
            response = await self._api.set_power_mode(rig_id, device_id, power_mode)
        if not response.get("success"):
            raise HomeAssistantError(f"API error: {response}")

    @staticmethod
    def parse_nhqm_string(nhqm: str) -> dict:
        ret = {}
        if not nhqm:
            return ret

        str_params = list(filter(None, nhqm.split(";")))
        if str_params:
            ret = dict(s.split("=") for s in str_params)
            opa = ret.get("OPA")
            if opa:
                alt_opa = {}
                for opa_item in opa.split(","):
                    opa_items = opa_item.split(":")
                    if len(opa_items) == 2:
                        opa_name, opa_id = opa_item.split(":")
                        alt_opa[opa_name.upper()] = opa_id

                alt_opa["MANUAL"] = "0"
                ret["OPA"] = alt_opa

        return ret

    @staticmethod
    def normalize_value(value: int) -> int:
        if 0 >= value <= 500:
            return value
        return value % 65536
