"""Constants for the IQAir Cloud integration."""
from typing import Final
from datetime import timedelta

DOMAIN: Final = "iqair_cloud"
SCAN_INTERVAL = timedelta(seconds=30)

# --- Configuration Keys ---
CONF_AUTH_TOKEN: Final = "auth_token"
CONF_LOGIN_TOKEN: Final = "login_token"
CONF_USER_ID: Final = "user_id"
CONF_DEVICE_ID: Final = "device_id"
CONF_SERIAL_NUMBER: Final = "serial_number"

# --- gRPC API Details ---
GRPC_API_URL: Final = "https://cloud-api.iqair.io/grpc.ui2.v1.UI2Service"
GRPC_API_HEADERS: Final = {
    "Content-Type": "application/grpc-web-text",
    "X-User-Agent": "grpc-web-javascript/0.1",
    "Accept": "application/grpc-web-text",
}

# --- Web API Details ---
WEB_API_URL: Final = "https://website-api.airvisual.com/v1/users/{user_id}/devices"
WEB_API_PARAMS: Final = {
    "page": "1",
    "perPage": "15",
    "units.system": "imperial",
    "AQI": "US",
    "language": "en",
}

# --- API Endpoints ---
ENDPOINT_FAN_SPEED: Final = "/SetFanSpeed"
ENDPOINT_POWER: Final = "/SetPowerMode"
ENDPOINT_LIGHT_INDICATOR: Final = "/SetLightIndicator"
ENDPOINT_LIGHT_LEVEL: Final = "/SetLightLevel"
ENDPOINT_AUTO_MODE: Final = "/SetAutoMode"
ENDPOINT_AUTO_MODE_PROFILE: Final = "/SetAutoModeProfile"
ENDPOINT_LOCKS: Final = "/SetDefaultLocks"

# --- gRPC Payload Fields ---
FIELD_POWER: Final = 0x10
FIELD_FAN_SPEED: Final = 0x18
FIELD_LIGHT_INDICATOR: Final = 0x10
FIELD_LIGHT_LEVEL: Final = 0x10
FIELD_AUTO_MODE: Final = 0x10
FIELD_AUTO_MODE_PROFILE: Final = 0x10
FIELD_LOCKS: Final = 0x10

# --- Mappings ---
LIGHT_LEVEL_MAP: Final = {1: "Low", 2: "Medium", 3: "High"}
AUTO_MODE_PROFILE_MAP: Final = {1: "Quiet", 2: "Balanced", 3: "Max"}