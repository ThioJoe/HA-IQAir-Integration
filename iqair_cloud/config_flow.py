"""Config flow for IQAir Cloud."""
import logging
from typing import Any

import httpx
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_AUTH_TOKEN,
    CONF_LOGIN_TOKEN,
    CONF_USER_ID,
    CONF_DEVICE_ID,
    CONF_SERIAL_NUMBER,
    GRPC_API_HEADERS,
)
from .api import IQAirApiClient

_LOGGER = logging.getLogger(__name__)


def _create_validation_clients(
    data: dict[str, Any]
) -> tuple[httpx.AsyncClient, httpx.AsyncClient]:
    """Create temporary httpx clients for validation in a thread-safe way."""
    command_client = httpx.AsyncClient(
        http2=True,
        headers={**GRPC_API_HEADERS, "Authorization": f"Bearer {data[CONF_AUTH_TOKEN]}"},
    )
    state_client = httpx.AsyncClient(headers={"x-login-token": data[CONF_LOGIN_TOKEN]})
    return command_client, state_client


async def validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> list[dict[str, Any]]:
    """Validate the user input allows us to connect."""
    command_client, state_client = await hass.async_add_executor_job(
        _create_validation_clients, data
    )

    # We don't have the serial number here, so we pass None
    api_client = IQAirApiClient(
        command_client=command_client,
        state_client=state_client,
        user_id=data[CONF_USER_ID],
        serial_number=None,
    )

    try:
        devices = await api_client.async_get_devices()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            raise InvalidAuth from exc
        raise CannotConnect from exc
    except httpx.RequestError as exc:
        raise CannotConnect from exc
    finally:
        await command_client.aclose()
        await state_client.aclose()

    if not devices:
        raise NoDevicesFound

    return devices


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IQAir Cloud."""

    VERSION = 1
    _user_input: dict[str, Any] = {}
    _devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._user_input = user_input
            try:
                self._devices = await validate_input(self.hass, user_input)
                return await self.async_step_select_device()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except NoDevicesFound:
                errors["base"] = "no_devices"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AUTH_TOKEN): str,
                    vol.Required(CONF_LOGIN_TOKEN): str,
                    vol.Required(CONF_USER_ID): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the device selection step."""
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            device = next(dev for dev in self._devices if dev["id"] == device_id)
            device_name = device["name"]
            serial_number = device["serialNumber"]

            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            data = {
                **self._user_input,
                CONF_DEVICE_ID: device_id,
                CONF_SERIAL_NUMBER: serial_number,
            }

            return self.async_create_entry(title=device_name, data=data)

        device_options = {dev["id"]: dev["name"] for dev in self._devices}
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(device_options)}),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class NoDevicesFound(HomeAssistantError):
    """Error to indicate no devices were found."""