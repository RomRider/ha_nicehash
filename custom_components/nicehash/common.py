"""Common classes and functions for Zoom."""
from datetime import timedelta
from logging import getLogger
from typing import Any, Dict
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.nicehash.nicehash import NiceHashPrivateAPI
from custom_components.nicehash.const import DOMAIN, SCAN_INTERVAL_MINUTES

_LOGGER = getLogger(__name__)

INTERVAL = timedelta(minutes=SCAN_INTERVAL_MINUTES)


class NiceHashSensorDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to hold Zoom user profile data."""

    def __init__(self, hass: HomeAssistant, api: NiceHashPrivateAPI) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=INTERVAL,
            update_method=self._async_update_data,
        )
        self._api = api
        self.sensor_update = None

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(10):
                rigs = await self._api.get_rigs_data()
                return rigs
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
