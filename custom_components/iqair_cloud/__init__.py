"""The IQAir Cloud integration."""
from __future__ import annotations
from typing import Any

import httpx
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IQAirApiClient
from .const import (
    DOMAIN,
    CONF_LOGIN_TOKEN,
    CONF_USER_ID,
    CONF_AUTH_TOKEN,
    CONF_SERIAL_NUMBER,
    GRPC_API_HEADERS,
)
from .coordinator import IQAirDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.SWITCH,
    Platform.SELECT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IQAir Cloud from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    login_token = entry.data[CONF_LOGIN_TOKEN]
    user_id = entry.data[CONF_USER_ID]
    auth_token = entry.data[CONF_AUTH_TOKEN]
    serial_number = entry.data[CONF_SERIAL_NUMBER]

    def _create_clients() -> tuple[httpx.AsyncClient, httpx.AsyncClient]:
        """Create the httpx clients in a thread-safe way."""
        command_client = httpx.AsyncClient(
            http2=True,
            headers={**GRPC_API_HEADERS, "Authorization": f"Bearer {auth_token}"},
        )
        state_client = httpx.AsyncClient(headers={"x-login-token": login_token})
        return command_client, state_client

    command_client, state_client = await hass.async_add_executor_job(_create_clients)

    api_client = IQAirApiClient(
        command_client=command_client,
        state_client=state_client,
        user_id=user_id,
        serial_number=serial_number,
    )

    coordinator = IQAirDataUpdateCoordinator(
        hass, api=api_client, device_id=entry.data["device_id"]
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "api_client": api_client,
        "coordinator": coordinator,
    }

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_close_clients(_: Any) -> None:
        """Close the httpx clients."""
        await command_client.aclose()
        await state_client.aclose()

    entry.async_on_unload(async_close_clients)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok