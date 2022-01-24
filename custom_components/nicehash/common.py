"""Common classes and functions for NiceHash."""
from datetime import timedelta
from logging import getLogger
from typing import Any, Dict
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import HomeAssistantError

from custom_components.nicehash.nicehash import NiceHashPrivateAPI
from custom_components.nicehash.const import (
    ACCOUNT_OBJ,
    DOMAIN,
    RIGS_OBJ,
)

_LOGGER = getLogger(__name__)


class NiceHashSensorDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to hold NiceHash data."""

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

    async def set_power_mode(self, input: dict):
        """Set a device power mode"""
        rig_name = input.data.get('rig_name')
        device_name = input.data.get('device_name')
        power_mode = input.data.get('power_mode')

        rig_id = None
        device_id = None

        for rig in self.data.get(RIGS_OBJ).get("miningRigs"):
            if rig.get('name') == rig_name:
                rig_id = rig.get('rigId')
                for device in rig.get('devices'):
                    if device.get('name') == device_name:
                        device_id = device.get('id')
                        break
                break

        if not rig_id:
            raise HomeAssistantError(f'Could not find rig with name {rig_name}')
        if not device_id:
            raise HomeAssistantError(f'Could not find device with name {device_name}')

        response = await self._api.set_power_mode(rig_id, device_id, power_mode)
        if not response.get('success'):
            raise HomeAssistantError(f'Could not set power mode: {response}')