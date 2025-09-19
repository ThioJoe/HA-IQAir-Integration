"""API client for the IQAir Cloud service."""
import base64
import logging
import re
import struct
from typing import Any

import httpx

from .const import (
    GRPC_API_URL,
    WEB_API_URL,
    WEB_API_PARAMS,
    ENDPOINT_FAN_SPEED,
    ENDPOINT_POWER,
    ENDPOINT_AUTO_MODE,
    ENDPOINT_AUTO_MODE_PROFILE,
    ENDPOINT_LIGHT_INDICATOR,
    ENDPOINT_LIGHT_LEVEL,
    ENDPOINT_LOCKS,
    FIELD_POWER,
    FIELD_FAN_SPEED,
    FIELD_LIGHT_INDICATOR,
    FIELD_LIGHT_LEVEL,
    FIELD_AUTO_MODE,
    FIELD_AUTO_MODE_PROFILE,
    FIELD_LOCKS,
)

_LOGGER = logging.getLogger(__name__)


def _decode_grpc_response(base64_string: str) -> str:
    """Decodes a gRPC-Web Base64 response into a human-readable string."""
    if not base64_string:
        return "  [Empty Response Body]"

    # Split concatenated base64 strings into frames
    delimited_input = re.sub(r"(=+)([A-Za-z0-9+/])", r"\1\n\2", base64_string)
    base64_frames = [frame for frame in delimited_input.split("\n") if frame]
    if not base64_frames and base64_string:
        base64_frames.append(base64_string)

    decoded_output = []
    for frame_b64 in base64_frames:
        try:
            frame_bytes = base64.b64decode(frame_b64)
            if len(frame_bytes) < 5:
                decoded_output.append(
                    f"  [Invalid Frame: Too short ({len(frame_bytes)} bytes)]"
                )
                continue

            frame_type = frame_bytes[0]
            # Unpack the 4-byte length header (big-endian)
            length = struct.unpack(">I", frame_bytes[1:5])[0]
            payload = frame_bytes[5:]

            if frame_type == 0x00:
                frame_type_str = "DATA (0x00)"
                # Data payload is binary, show as hex
                payload_str = " ".join(f"{b:02x}" for b in payload)
            elif frame_type == 0x80:
                frame_type_str = "TRAILERS (0x80)"
                # Trailers payload is text
                payload_str = f"'{payload.decode('utf-8').strip()}'"
            else:
                frame_type_str = f"Unknown (0x{frame_type:02x})"
                payload_str = " ".join(f"{b:02x}" for b in payload)

            decoded_output.append(
                f"  [Frame: {frame_type_str}, Length: {length}, Payload: {payload_str}]"
            )

        except Exception as e:
            decoded_output.append(f"  [Decoding Error: {e}]")

    return "\n".join(decoded_output)


class IQAirApiClient:
    """A client to communicate with the IQAir Cloud APIs."""

    def __init__(
        self,
        command_client: httpx.AsyncClient,
        state_client: httpx.AsyncClient,
        user_id: str,
        serial_number: str | None,
    ):
        """Initialize the API client."""
        self._user_id = user_id
        self._command_client = command_client
        self._state_client = state_client
        self._serial_number = serial_number

    def _build_payload(self, field: int, value: int | None = None) -> str:
        """Build the gRPC payload."""
        if not self._serial_number:
            raise ValueError("Serial number is not set")

        # The payload uses the serial number without the "UI2_" prefix
        sn_part = self._serial_number.replace("UI2_", "").encode("utf-8")
        payload_bytes = bytearray([0x0A, len(sn_part)]) + sn_part

        if value is not None:
            payload_bytes += bytearray([field, value])

        # Frame the payload
        length = len(payload_bytes)
        frame = struct.pack(">I", length)  # 4-byte length
        framed_payload = bytearray([0x00]) + frame + payload_bytes  # 1-byte type

        return base64.b64encode(framed_payload).decode("utf-8")

    async def _send_command(
        self, endpoint: str, payload: str, context: str | None = None
    ) -> dict[str, Any] | None:
        """Send a command request to the gRPC API and return the new state."""
        url = f"{GRPC_API_URL}{endpoint}"
        context_str = f" ({context})" if context else ""
        try:
            response = await self._command_client.post(url, content=payload)
            response.raise_for_status()
            decoded_response = _decode_grpc_response(response.text)
            _LOGGER.debug(
                "Command to %s successful%s. Status: %s, Version: %s\nRequest Body: %s\nResponse Body:\n%s",
                url,
                context_str,
                response.status_code,
                response.http_version,
                payload,
                decoded_response,
            )

            # Parse the response to extract the new state
            delimited_input = re.sub(r"(=+)([A-Za-z0-9+/])", r"\1\n\2", response.text)
            base64_frames = [frame for frame in delimited_input.split("\n") if frame]
            if not base64_frames and response.text:
                base64_frames.append(response.text)

            new_state = {}
            if not base64_frames:
                return {}

            first_frame_b64 = base64_frames[0]
            frame_bytes = base64.b64decode(first_frame_b64)

            # Check for empty payload which indicates "off" for some switches
            if len(frame_bytes) == 5:
                if endpoint == ENDPOINT_LIGHT_INDICATOR:
                    return {"lightIndicatorEnabled": False}
                if endpoint == ENDPOINT_AUTO_MODE:
                    return {"autoModeEnabled": False}
                if endpoint == ENDPOINT_LOCKS:
                    return {"isLocksEnabled": False}

            if len(frame_bytes) > 6 and frame_bytes[0] == 0x00:  # DATA Frame
                value = frame_bytes[6]
                if endpoint == ENDPOINT_POWER:
                    new_state = {"powerMode": value}
                elif endpoint == ENDPOINT_FAN_SPEED:
                    new_state = {"speedLevel": value}
                elif endpoint == ENDPOINT_LIGHT_LEVEL:
                    new_state = {"lightLevel": value, "lightIndicatorEnabled": True}
                elif endpoint == ENDPOINT_LIGHT_INDICATOR:
                    new_state = {"lightIndicatorEnabled": value == 1}
                elif endpoint == ENDPOINT_AUTO_MODE:
                    new_state = {"autoModeEnabled": value == 1}
                elif endpoint == ENDPOINT_AUTO_MODE_PROFILE:
                    new_state = {"autoModeProfile": value}
                elif endpoint == ENDPOINT_LOCKS:
                    new_state = {"isLocksEnabled": value == 1}

            return new_state

        except (httpx.RequestError, base64.binascii.Error, IndexError, ValueError) as e:
            _LOGGER.error(
                "Error sending or parsing command to %s%s: %s", url, context_str, e
            )
            return None

    async def set_power(
        self, is_on: bool, context: str | None = None
    ) -> dict[str, Any] | None:
        """Set the power state of the device."""
        value = 2 if is_on else 3
        payload = self._build_payload(FIELD_POWER, value)
        return await self._send_command(ENDPOINT_POWER, payload, context=context)

    async def set_fan_speed(
        self, speed_level: int, context: str | None = None
    ) -> dict[str, Any] | None:
        """Set the fan speed of the device."""
        if not 1 <= speed_level <= 6:
            _LOGGER.error("Invalid fan speed level: %s", speed_level)
            return None
        payload = self._build_payload(FIELD_FAN_SPEED, speed_level)
        return await self._send_command(ENDPOINT_FAN_SPEED, payload, context=context)

    async def set_light_indicator(self, is_on: bool) -> dict[str, Any] | None:
        """Set the light indicator state."""
        value = 1 if is_on else None
        payload = self._build_payload(FIELD_LIGHT_INDICATOR, value)
        return await self._send_command(ENDPOINT_LIGHT_INDICATOR, payload)

    async def set_light_level(self, level: int) -> dict[str, Any] | None:
        """Set the light brightness level."""
        if level not in [1, 2, 3]:
            _LOGGER.error("Invalid light level: %s", level)
            return None
        payload = self._build_payload(FIELD_LIGHT_LEVEL, level)
        return await self._send_command(ENDPOINT_LIGHT_LEVEL, payload)

    async def set_auto_mode(self, is_on: bool) -> dict[str, Any] | None:
        """Set the auto mode state."""
        value = 1 if is_on else None
        payload = self._build_payload(FIELD_AUTO_MODE, value)
        return await self._send_command(ENDPOINT_AUTO_MODE, payload)

    async def set_auto_mode_profile(self, profile_id: int) -> dict[str, Any] | None:
        """Set the auto mode profile."""
        if profile_id not in [1, 2, 3]:
            _LOGGER.error("Invalid auto mode profile ID: %s", profile_id)
            return None
        payload = self._build_payload(FIELD_AUTO_MODE_PROFILE, profile_id)
        return await self._send_command(ENDPOINT_AUTO_MODE_PROFILE, payload)

    async def set_lock(self, is_on: bool) -> dict[str, Any] | None:
        """Set the control panel lock state."""
        value = 1 if is_on else None
        payload = self._build_payload(FIELD_LOCKS, value)
        return await self._send_command(ENDPOINT_LOCKS, payload)

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Fetch all devices from the Web API."""
        url = WEB_API_URL.format(user_id=self._user_id)
        try:
            response = await self._state_client.get(url, params=WEB_API_PARAMS)
            response.raise_for_status()
            return response.json()
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
            _LOGGER.error("Error fetching devices from %s: %s", url, e)
            return []

    async def async_get_device_state(self, device_id: str) -> dict[str, Any] | None:
        """Fetch state for a specific device."""
        devices = await self.async_get_devices()
        return next(
            (device for device in devices if device.get("id") == device_id), None
        )