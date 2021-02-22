"""Common classes and functions for Zoom."""
from datetime import timedelta
from logging import getLogger
from typing import Any, Dict
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.nicehash.nicehash import NiceHashPrivateAPI
from custom_components.nicehash.const import (
    ACCOUNT_OBJ,
    DOMAIN,
    RIGS_OBJ,
)

_LOGGER = getLogger(__name__)


class NiceHashSensorDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to hold Zoom user profile data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: NiceHashPrivateAPI,
        update_interval: int,
        fiat="USD",
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval),
            update_method=self._async_update_data,
        )
        self._api = api
        self._fiat = fiat

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(10):
                rigs = await self._api.get_rigs_data()
                account = await self._api.get_account_data(self._fiat)
                return {RIGS_OBJ: rigs, ACCOUNT_OBJ: account}
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
