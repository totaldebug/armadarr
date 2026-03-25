"""Constants for Armadarr."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "armadarr"

CONF_APP_TYPE = "app_type"
CONF_URL = "url"
CONF_API_KEY = "api_key"
CONF_VERIFY_SSL = "verify_ssl"

APP_TYPES = [
    "Sonarr",
    "Radarr",
    "Lidarr",
    "Readarr",
    "Prowlarr",
    "Bazarr",
    "Whisparr",
]
