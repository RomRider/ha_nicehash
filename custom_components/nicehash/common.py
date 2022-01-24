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
        rig_id = input.data.get('rig_id')
        device_id = input.data.get('device_id')
        power_mode = input.data.get('power_mode').upper()

        nhqm_ver = None
        nhqm_op = None
        supported_power_modes = ["HIGH", "MEDIUM", "LOW"]
        try:
            for rig in self.data.get(RIGS_OBJ).get("miningRigs"):
                if rig.get('rigId') != rig_id:
                    continue

                for device in rig.get('devices'):
                    if device.get('id') != device_id:
                        continue

                    if 'nhqm' in device:
                        supported_power_modes = []
                        nhqm = device.get('nhqm')
                        v_pos = nhqm.find('V=')
                        if v_pos > -1:
                            sub = nhqm[v_pos+2:]
                            delim = sub.find(';')
                            nhqm_ver = sub[:delim]

                            opa_pos = nhqm.find('OPA=')
                            if opa_pos > -1:
                                sub = nhqm[opa_pos+4:]
                                delim = sub.find(';')
                                sub = sub[:delim]
                                for pm in sub.split(','):
                                    name, id = pm.split(':')
                                    supported_power_modes.append(name.upper())
                                    if name.upper() == power_mode:
                                        nhqm_op = id
                                        break
        except Exception as e:
            _LOGGER.error(f"Could not parse powerMode for NiceHashQuickMiner -> {type(e)} -> {e.args}")

        if power_mode not in supported_power_modes:
            raise HomeAssistantError(f'Unsupported power mode [{power_mode}]. Supported power modes for this device are {", ".join(supported_power_modes)}')

        if nhqm_ver and not nhqm_op:
            raise HomeAssistantError(f'Internal error, cannot determine operation id for power mode [{power_mode}]!')

        _LOGGER.info(f"Calling with {rig_id}, {device_id}, {power_mode}, {nhqm_ver}, {nhqm_op}")

        if nhqm_ver:
            response = await self._api.set_power_mode_nhqm(rig_id, device_id, nhqm_ver, nhqm_op)
        else:
            response = await self._api.set_power_mode(rig_id, device_id, power_mode)
        if not response.get('success'):
            raise HomeAssistantError(f'API error: {response}')