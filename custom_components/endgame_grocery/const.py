"""Constants for the Endgame Grocery integration."""

from datetime import timedelta

DOMAIN = "endgame_grocery"
PLATFORMS: list[str] = ["todo"]

CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
