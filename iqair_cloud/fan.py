"""Fan platform for IQAir Cloud."""
import logging
import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_DEVICE_ID
from .api import IQAirApiClient
from .coordinator import IQAirDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SPEED_COUNT = 6  # There are 6 speed levels


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IQAir fan entity."""
    api_client: IQAirApiClient = hass.data[DOMAIN][entry.entry_id]["api_client"]
    coordinator: IQAirDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    device_id = entry.data[CONF_DEVICE_ID]

    async_add_entities([IQAirFan(coordinator, api_client, device_id, entry)])


class IQAirFan(FanEntity):
    """Representation of an IQAir Cloud fan."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        coordinator: IQAirDataUpdateCoordinator,
        api_client: IQAirApiClient,
        device_id: str,
        entry: ConfigEntry,
    ):
        """Initialize the fan."""
        self.coordinator = coordinator
        self._api = api_client
        self._device_id = device_id
        self._attr_unique_id = device_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": entry.title,
            "manufacturer": "IQAir",
            "model": self.coordinator.data.get("modelLabel"),
        }

    def _update_state_from_response(self, update_data: dict[str, Any]):
        """Update coordinator data from a command response."""
        self.coordinator.update_from_command(update_data)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool | None:
        """Return true if the fan is on."""
        if not self.available or self.coordinator.data is None:
            return None
        # powerMode is 2 when on, 3 when off
        return self.coordinator.data.get("remote", {}).get("powerMode") == 2

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if not self.available or self.coordinator.data is None:
            return None
        return self.coordinator.data.get("remote", {}).get("speedPercent")

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return SPEED_COUNT

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the fan on."""
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            update_data = await self._api.set_power(True, context="fan.turn_on")
            if update_data is not None:
                self._update_state_from_response(update_data)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        update_data = await self._api.set_power(False, context="fan.turn_off")
        if update_data is not None:
            self._update_state_from_response(update_data)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan."""
        if percentage == 0:
            await self.async_turn_off()
            return

        speed_level = math.ceil(percentage / 100 * SPEED_COUNT)
        speed_level = max(1, min(SPEED_COUNT, speed_level))

        update_data = await self._api.set_fan_speed(
            speed_level, context="fan.set_percentage"
        )
        if update_data is not None:
            # We got the level, now map it back to the specific percentage
            speed_level_from_api = update_data.get("speedLevel")
            if speed_level_from_api and self.coordinator.data:
                man_speed_table = self.coordinator.data.get("remote", {}).get(
                    "manSpeedTable", []
                )
                if (
                    isinstance(man_speed_table, list)
                    and 0 < speed_level_from_api <= len(man_speed_table)
                ):
                    update_data["speedPercent"] = man_speed_table[
                        speed_level_from_api - 1
                    ]

            self._update_state_from_response(update_data)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self) -> None:
        """Update the entity. Only used by the generic entity update service."""
        await self.coordinator.async_request_refresh()