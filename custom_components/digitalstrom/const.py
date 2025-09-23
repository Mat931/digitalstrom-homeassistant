"""Constants for the digitalSTROM integration."""

from datetime import timedelta

CONF_DSUID: str = "dsuid"
CONF_SSL: str = "ssl"

DEFAULT_HOST: str = "dss.local"
DEFAULT_PORT: int = 8080
DEFAULT_USERNAME: str = "dssadmin"
IGNORE_SSL_VERIFICATION = "ignore"

DOMAIN = "digitalstrom"

WEBSOCKET_WATCHDOG_INTERVAL = timedelta(seconds=10)

APARTMENT_SCENE_UPDATE_INTERVAL = timedelta(seconds=59)
APARTMENT_SCENE_UPDATE_INTERVAL_IF_CHANGED = timedelta(seconds=29)
