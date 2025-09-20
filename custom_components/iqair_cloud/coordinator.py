"""Data update coordinator for the IQAir Cloud integration."""
from typing import Any
import copy
import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL
from .api import IQAirApiClient
from .exceptions import InvalidAuth

_LOGGER = logging.getLogger(__name__)


class IQAirDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching IQAir data."""

    def __init__(self, hass: HomeAssistant, api: IQAirApiClient, device_id: str):
        """Initialize."""
        self.api = api
        self.device_id = device_id
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            data = await self.api.async_get_device_state(self.device_id)
            if not data:
                raise UpdateFailed("Device not found or API error")
            return data
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err

    def update_from_command(self, update_data: dict[str, Any]):
        """Update coordinator data from a command response."""
        if self.data and update_data:
            new_data = copy.deepcopy(self.data)
            new_data["remote"].update(update_data)
            self.async_set_updated_data(new_data)