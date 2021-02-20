"""Support for Neato sensors."""
from datetime import timedelta
import logging
import async_timeout
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from custom_components.nicehash.NiceHash import NiceHashPrivateAPI

from .const import DOMAIN, SCAN_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=SCAN_INTERVAL_MINUTES)

PLATFORM = "sensor"
RIG_DATA_ATTRIBUTES = [
    {"localProfitability": {"numerical": True, "unit": "BTC"}},
    {"profitability": {"numerical": True, "unit": "BTC"}},
    {"minerStatus": {"numerical": False, "unit": None}},
]

RIG_STATS_ATTRIBUTES = [{"speedAccepted": {}}, {"speedRejectedTotal": {}}]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the NiceHash sensor using config entry."""
    api: NiceHashPrivateAPI = hass.data[DOMAIN][entry.entry_id]

    async def async_update_data():
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(10):
                rigs = await api.get_rigs_data()
                return rigs
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sensor",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    # Fetch initial data so we have data when entities subscribe
    dev = []
    await coordinator.async_refresh()
    for rig in coordinator.data.get("miningRigs"):
        rig_id = rig.get("rigId")
        for data_type in RIG_DATA_ATTRIBUTES:
            dev.append(NiceHashRigSensor(coordinator, rig_id, data_type))
        for stat in rig.get("stats", []):
            alg = stat.get("algorithm")
            for data_type in RIG_STATS_ATTRIBUTES:
                dev.append(
                    NiceHashRigStatSensor(
                        coordinator, rig_id, alg.get("enumName"), data_type
                    )
                )

    async_add_entities(dev)


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


class NiceHashRigSensor(NiceHashSensor, CoordinatorEntity, Entity):
    """Sensor representing NiceHash data."""

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


class NiceHashRigStatSensor(NiceHashSensor, CoordinatorEntity, Entity):
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
