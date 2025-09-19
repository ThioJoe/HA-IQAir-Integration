"""Switch platform for IQAir Cloud."""
import logging
from typing import Any
from dataclasses import dataclass

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_DEVICE_ID
from .api import IQAirApiClient
from .coordinator import IQAirDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class IQAirSwitchEntityDescription(SwitchEntityDescription):
    """Describes an IQAir switch entity."""

    state_key: str


SWITCH_TYPES: tuple[IQAirSwitchEntityDescription, ...] = (
    IQAirSwitchEntityDescription(
        key="auto_mode",
        name="Smart Mode",
        icon="mdi:fan-auto",
        state_key="autoModeEnabled",
    ),
    IQAirSwitchEntityDescription(
        key="control_panel_lock",
        name="Control Panel Lock",
        icon="mdi:lock",
        state_key="isLocksEnabled",
    ),
    IQAirSwitchEntityDescription(
        key="display_light",
        name="Display Light",
        icon="mdi:lightbulb",
        state_key="lightIndicatorEnabled",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IQAir switch entities."""
    coordinator: IQAirDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    api_client: IQAirApiClient = hass.data[DOMAIN][entry.entry_id]["api_client"]
    device_id = entry.data[CONF_DEVICE_ID]

    entities = [
        IQAirSwitch(coordinator, api_client, device_id, entry, description)
        for description in SWITCH_TYPES
    ]
    async_add_entities(entities)


class IQAirSwitch(SwitchEntity):
    """Representation of an IQAir Cloud switch."""

    entity_description: IQAirSwitchEntityDescription
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: IQAirDataUpdateCoordinator,
        api_client: IQAirApiClient,
        device_id: str,
        entry: ConfigEntry,
        description: IQAirSwitchEntityDescription,
    ):
        """Initialize the switch."""
        self.coordinator = coordinator
        self._api = api_client
        self._device_id = device_id
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": entry.title,
            "manufacturer": "IQAir",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if not self.available or self.coordinator.data is None:
            return None
        return self.coordinator.data.get("remote", {}).get(
            self.entity_description.state_key
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        update_data = None
        if self.entity_description.key == "auto_mode":
            update_data = await self._api.set_auto_mode(True)
        elif self.entity_description.key == "control_panel_lock":
            update_data = await self._api.set_lock(True)
        elif self.entity_description.key == "display_light":
            update_data = await self._api.set_light_indicator(True)

        if update_data is not None:
            self.coordinator.update_from_command(update_data)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        update_data = None
        if self.entity_description.key == "auto_mode":
            update_data = await self._api.set_auto_mode(False)
        elif self.entity_description.key == "control_panel_lock":
            update_data = await self._api.set_lock(False)
        elif self.entity_description.key == "display_light":
            update_data = await self._api.set_light_indicator(False)

        if update_data is not None:
            self.coordinator.update_from_command(update_data)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

