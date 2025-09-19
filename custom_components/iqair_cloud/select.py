"""Select platform for IQAir Cloud."""
import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_DEVICE_ID, AUTO_MODE_PROFILE_MAP, LIGHT_LEVEL_MAP
from .api import IQAirApiClient
from .coordinator import IQAirDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IQAir select entity."""
    coordinator: IQAirDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    api_client: IQAirApiClient = hass.data[DOMAIN][entry.entry_id]["api_client"]
    device_id = entry.data[CONF_DEVICE_ID]

    async_add_entities(
        [
            IQAirAutoModeProfileSelect(coordinator, api_client, device_id, entry),
            IQAirLightLevelSelect(coordinator, api_client, device_id, entry),
        ]
    )


class IQAirAutoModeProfileSelect(SelectEntity):
    """Representation of an IQAir Cloud auto mode profile select entity."""

    _attr_has_entity_name = True
    _attr_name = "Smart Mode Profile"
    _attr_icon = "mdi:tune"
    _attr_should_poll = False
    _attr_options = list(AUTO_MODE_PROFILE_MAP.values())

    def __init__(
        self,
        coordinator: IQAirDataUpdateCoordinator,
        api_client: IQAirApiClient,
        device_id: str,
        entry: ConfigEntry,
    ):
        """Initialize the select entity."""
        self.coordinator = coordinator
        self._api = api_client
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_auto_mode_profile"
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
    def current_option(self) -> str | None:
        """Return the selected option."""
        if not self.available or self.coordinator.data is None:
            return None
        profile_id = self.coordinator.data.get("remote", {}).get("autoModeProfile")
        return AUTO_MODE_PROFILE_MAP.get(profile_id)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Find the profile ID for the selected option name
        profile_id = next(
            (k for k, v in AUTO_MODE_PROFILE_MAP.items() if v == option), None
        )
        if profile_id is not None:
            update_data = await self._api.set_auto_mode_profile(profile_id)
            if update_data is not None:
                self.coordinator.update_from_command(update_data)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class IQAirLightLevelSelect(SelectEntity):
    """Representation of an IQAir Cloud light level select entity."""

    _attr_has_entity_name = True
    _attr_name = "Display Brightness"
    _attr_icon = "mdi:brightness-6"
    _attr_should_poll = False
    _attr_options = list(LIGHT_LEVEL_MAP.values())

    def __init__(
        self,
        coordinator: IQAirDataUpdateCoordinator,
        api_client: IQAirApiClient,
        device_id: str,
        entry: ConfigEntry,
    ):
        """Initialize the select entity."""
        self.coordinator = coordinator
        self._api = api_client
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_light_level"
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
    def current_option(self) -> str | None:
        """Return the selected option."""
        if not self.available or self.coordinator.data is None:
            return None
        level_id = self.coordinator.data.get("remote", {}).get("lightLevel")
        return LIGHT_LEVEL_MAP.get(level_id)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Find the level ID for the selected option name
        level_id = next(
            (k for k, v in LIGHT_LEVEL_MAP.items() if v == option), None
        )
        if level_id is not None:
            update_data = await self._api.set_light_level(level_id)
            if update_data is not None:
                self.coordinator.update_from_command(update_data)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

