"""Constants for the Endgame Grocery integration."""

from datetime import timedelta

DOMAIN = "endgame_grocery"
PLATFORMS: list[str] = ["todo"]

CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL_SECONDS = 60
DEFAULT_SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS)
