"""Support for Neato sensors."""

from datetime import timedelta
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.core import callback

# from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.helpers.typing import HomeAssistantType

from custom_components.nicehash.common import NiceHashSensorDataUpdateCoordinator
from custom_components.nicehash.const import (
    DOMAIN,
    SCAN_INTERVAL_MINUTES,
    SENSOR_DATA_COORDINATOR,
    UNSUB,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=SCAN_INTERVAL_MINUTES)

PLATFORM = "sensor"
GLOBAL_ATTRIBUTES = [
    {"unpaidAmount": {"unit": "BTC"}},
    {"totalProfitability": {"unit": "BTC"}},
    {"totalProfitabilityLocal": {"unit": "BTC"}},
]
RIG_DATA_ATTRIBUTES = [
    {"localProfitability": {"numerical": True, "unit": "BTC"}},
    {"profitability": {"numerical": True, "unit": "BTC"}},
    {"minerStatus": {"numerical": False, "unit": None}},
]

RIG_STATS_ATTRIBUTES = [{"speedAccepted": {}}, {"speedRejectedTotal": {}}]


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the NiceHash sensor using config entry."""
    coordinator: NiceHashSensorDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ][SENSOR_DATA_COORDINATOR]

    # Fetch initial data so we have data when entities subscribe
    @callback
    def _update_entities():
        if not hasattr(_update_entities, "dev"):
            _update_entities.dev = []

        new_dev = []
        for attr in GLOBAL_ATTRIBUTES:
            sensor = NiceHashGlobalSensor(coordinator, config_entry, attr)
            if sensor.unique_id not in _update_entities.dev:
                new_dev.append(sensor)
                _update_entities.dev.append(sensor.unique_id)
        for rig in coordinator.data.get("miningRigs"):
            rig_id = rig.get("rigId")
            for data_type in RIG_DATA_ATTRIBUTES:
                sensor = NiceHashRigSensor(coordinator, rig_id, data_type)
                if sensor.unique_id not in _update_entities.dev:
                    new_dev.append(sensor)
                    _update_entities.dev.append(sensor.unique_id)
            for stat in rig.get("stats", []):
                alg = stat.get("algorithm")
                for data_type in RIG_STATS_ATTRIBUTES:
                    sensor = NiceHashRigStatSensor(
                        coordinator, rig_id, alg.get("enumName"), data_type
                    )
                    if sensor.unique_id not in _update_entities.dev:
                        new_dev.append(sensor)
                        _update_entities.dev.append(sensor.unique_id)

        async_add_entities(new_dev)

    unsub = coordinator.async_add_listener(_update_entities)
    hass.data[DOMAIN][config_entry.entry_id][UNSUB].append(unsub)
    await coordinator.async_refresh()

    # @callback
    # def update_sensor_entities(entry: ConfigEntry) -> None:
    #     _LOGGER.warning("called")

    # hass.data[DOMAIN][entry.entry_id][UNSUB].append(
    #     async_dispatcher_connect(hass, entry.entry_id, update_sensor_entities)
    # )


class NiceHashGlobalSensor(CoordinatorEntity, Entity):
    """Sensor reprensenting all rigs data"""

    domain = PLATFORM

    def __init__(self, coordinator, config_entry: ConfigEntry, info_type):
        super().__init__(coordinator)
        self._info_type = list(info_type.keys())[0]
        self._info = info_type[self._info_type]
        self._config_entry = config_entry

    @property
    def unique_id(self):
        return f"nh-{self._config_entry.data['name']}-{self._info_type}"

    @property
    def name(self):
        return f"NH - {self._config_entry.data['name']} - {self._info_type}"

    @property
    def state(self):
        """State of the sensor."""
        return self.coordinator.data[self._info_type]

    @property
    def available(self):
        """Return availability"""
        return self.coordinator.last_update_success

    @property
    def unit_of_measurement(self):
        """Return unit of measurement."""
        return self._info.get("unit", None)

    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {
                (
                    DOMAIN,
                    f"{self._config_entry.entry_id}_{self._config_entry.data['name']}",
                )
            },
            "name": f"{self._config_entry.data['name']} Account",
            "sw_version": "",
            "model": "",
            "manufacturer": "NiceHash",
        }


class NiceHashSensor(CoordinatorEntity, Entity):
    """Representation of a NiceHash Sensor"""

    domain = PLATFORM
    name = None
    unique_id = None

    def __init__(self, coordinator, rigId, info_type):
        super().__init__(coordinator)
        self._rig_id = rigId
        self._info_type = list(info_type.keys())[0]
        self._info = info_type[self._info_type]

    @property
    def unit_of_measurement(self):
        """Return unit of measurement."""
        return self._info.get("unit", None)

    @property
    def available(self):
        """Return availability"""
        return self.coordinator.last_update_success and self.get_rig() is not None

    def get_rig(self):
        """Return the rig object."""
        rig = None
        for rig_entry in self.coordinator.data.get("miningRigs"):
            if rig_entry.get("rigId") == self._rig_id:
                rig = rig_entry
        return rig

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


class NiceHashRigSensor(NiceHashSensor):
    """Sensor representing NiceHash rig data."""

    @property
    def unique_id(self):
        return f"nh-{self._rig_id}-{self._info_type}"

    @property
    def name(self):
        rig = self.get_rig()
        if rig is not None:
            return f"NH - {rig.get('name')} - {self._info_type}"
        return None

    @property
    def state(self):
        """State of the sensor."""
        return self.get_rig()[self._info_type]


class NiceHashRigStatSensor(NiceHashSensor):
    """Representation of a NiceHash Stat Sensor"""

    def __init__(self, coordinator, rigId, alg, info_type):
        super().__init__(coordinator, rigId, info_type)
        self._alg = alg

    @property
    def unique_id(self):
        return f"nh-{self._rig_id}-{self._alg}-{self._info_type}"

    @property
    def name(self):
        rig = self.get_rig()
        if rig is not None:
            return f"NH - {rig.get('name')} - {self._alg} - {self._info_type}"
        return None

    def get_alg(self):
        """Return the stat object."""
        rig = self.get_rig()
        alg = None
        stats = stats = rig.get("stats")
        if stats:
            for stat in stats:
                alg = stat.get("algorithm")
                if alg and alg.get("enumName") == self._alg:
                    alg = stat
        return alg

    @property
    def state(self):
        """State of the sensor."""
        alg = self.get_alg()
        if alg is not None:
            return alg.get(self._info_type)
        return None

    @property
    def available(self):
        """Return availability"""
        return super().available and self.get_alg() is not None

    @property
    def unit_of_measurement(self):
        """Return unit of measurement."""
        if self._alg == "DAGGERHASHIMOTO":
            return "MH/s"
        return super().unit_of_measurement
