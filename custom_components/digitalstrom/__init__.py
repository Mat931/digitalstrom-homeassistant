"""The digitalSTROM integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

from .api.apartment import DigitalstromApartment
from .api.client import DigitalstromClient
from .api.exceptions import CannotConnect, InvalidAuth, InvalidCertificate, ServerError
from .const import CONF_DSUID, CONF_SSL, DOMAIN, WEBSOCKET_WATCHDOG_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.COVER,
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.SCENE,
    Platform.CLIMATE,
    Platform.UPDATE,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """
    load configuration for digitalSTROM component
    """
    # not configured
    if DOMAIN not in config:
        return True

    # already imported
    if hass.config_entries.async_entries(DOMAIN):
        return True

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up digitalSTROM from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    client = DigitalstromClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        ssl=entry.data[CONF_SSL],
        loop=hass.loop,
    )
    client.set_app_token(entry.data[CONF_TOKEN])

    try:
        apartment = DigitalstromApartment(client, entry.data[CONF_DSUID])
        hass.data[DOMAIN].setdefault(entry.data[CONF_DSUID], dict())
        hass.data[DOMAIN][entry.data[CONF_DSUID]]["client"] = client
        hass.data[DOMAIN][entry.data[CONF_DSUID]]["apartment"] = apartment
        await apartment.get_zones()
        await apartment.get_circuits()
        await apartment.get_devices()
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except (InvalidAuth, InvalidCertificate) as ex:
        raise ConfigEntryAuthFailed(ex) from ex
    except (CannotConnect, ServerError) as ex:
        raise ConfigEntryNotReady(ex) from ex

    async def start_watchdog(event=None):
        """Start websocket watchdog."""
        if "watchdog" not in hass.data[DOMAIN][entry.data[CONF_DSUID]]:
            hass.data[DOMAIN][entry.data[CONF_DSUID]]["watchdog"] = (
                async_track_time_interval(
                    hass,
                    client.event_listener_watchdog,
                    WEBSOCKET_WATCHDOG_INTERVAL,
                    cancel_on_shutdown=True,
                )
            )

    async def stop_watchdog(event=None):
        await async_unload_entry(hass, entry)

    # If Home Assistant is already in a running state, start the watchdog
    # immediately, else trigger it after Home Assistant has finished starting.
    if hass.state == CoreState.running:
        await start_watchdog()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, start_watchdog)
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, client.event_listener_watchdog
        )
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_watchdog)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if (
            (entry.data[CONF_DSUID] in hass.data[DOMAIN])
            and (
                remove_watchdog := hass.data[DOMAIN][entry.data[CONF_DSUID]]["watchdog"]
            )
        ) is not None:
            remove_watchdog()
        await hass.data[DOMAIN][entry.data[CONF_DSUID]]["client"].stop_event_listener()
        hass.data[DOMAIN].pop(entry.data[CONF_DSUID])
    return unload_ok
