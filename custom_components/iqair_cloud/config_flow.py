"""Config flow for IQAir Cloud."""
import logging
from typing import Any

import httpx
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_LOGIN_TOKEN,
    CONF_USER_ID,
    CONF_AUTH_TOKEN,
    CONF_DEVICE_ID,
    CONF_SERIAL_NUMBER,
)
from .api import IQAirApiClient, async_signin, async_get_cloud_api_auth_token
from .exceptions import CannotConnect, InvalidAuth, NoDevicesFound

_LOGGER = logging.getLogger(__name__)


async def create_state_client(hass: HomeAssistant, login_token: str) -> httpx.AsyncClient:
    """Create the httpx state client in a thread-safe way."""

    def _create_client() -> httpx.AsyncClient:
        """Create the httpx client."""
        return httpx.AsyncClient(headers={"x-login-token": login_token})

    return await hass.async_add_executor_job(_create_client)


async def validate_connection(
    hass: HomeAssistant, login_token: str, user_id: str
) -> list[dict[str, Any]]:
    """Validate the user input allows us to connect."""
    state_client = await create_state_client(hass, login_token)
    api_client = IQAirApiClient(
        command_client=None,  # Not needed for validation
        state_client=state_client,
        user_id=user_id,
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
        await state_client.aclose()

    if not devices:
        raise NoDevicesFound

    return devices


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IQAir Cloud."""

    VERSION = 1
    _user_input: dict[str, Any] = {}
    _devices: list[dict[str, Any]] = []

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "IQAirOptionsFlowHandler":
        """Get the options flow for this handler."""
        return IQAirOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step to choose auth method."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["credentials", "tokens"],
        )

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the email and password step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            signin_data = await async_signin(
                session, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            )

            if signin_data:
                self._user_input[CONF_LOGIN_TOKEN] = signin_data["loginToken"]
                self._user_input[CONF_USER_ID] = signin_data["id"]

                auth_token = await async_get_cloud_api_auth_token(session)
                if not auth_token:
                    errors["base"] = "cannot_connect"
                    return self.async_show_form(
                        step_id="credentials",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONF_EMAIL): str,
                                vol.Required(CONF_PASSWORD): str,
                            }
                        ),
                        errors=errors,
                    )
                self._user_input[CONF_AUTH_TOKEN] = auth_token

                try:
                    self._devices = await validate_connection(
                        self.hass,
                        self._user_input[CONF_LOGIN_TOKEN],
                        self._user_input[CONF_USER_ID],
                    )
                    return await self.async_step_select_device()
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except NoDevicesFound:
                    errors["base"] = "no_devices"
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_tokens(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the manual token entry step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._user_input = user_input
            try:
                self._devices = await validate_connection(
                    self.hass, user_input[CONF_LOGIN_TOKEN], user_input[CONF_USER_ID]
                )
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
            step_id="tokens",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOGIN_TOKEN): str,
                    vol.Required(CONF_USER_ID): str,
                    vol.Required(CONF_AUTH_TOKEN): str,
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

            if self.context.get("source") == config_entries.SOURCE_REAUTH:
                existing_entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_LOGIN_TOKEN: self._user_input[CONF_LOGIN_TOKEN],
                        CONF_USER_ID: self._user_input[CONF_USER_ID],
                        CONF_AUTH_TOKEN: self._user_input[CONF_AUTH_TOKEN],
                    }
                )
                self.hass.config_entries.async_update_entry(
                    existing_entry,
                    data={
                        **existing_entry.data,
                        CONF_LOGIN_TOKEN: self._user_input[CONF_LOGIN_TOKEN],
                        CONF_USER_ID: self._user_input[CONF_USER_ID],
                        CONF_AUTH_TOKEN: self._user_input[CONF_AUTH_TOKEN],
                    },
                )
                await self.hass.config_entries.async_reload(existing_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

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

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle re-authentication."""
        return await self.async_step_user(entry_data)


class IQAirOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for IQAir Cloud."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            self.config_entry.async_start_reauth(self.hass)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "name": self.config_entry.title,
            },
        )