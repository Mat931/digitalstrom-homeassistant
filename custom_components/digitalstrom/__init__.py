"""The digitalSTROM integration."""

from __future__ import annotations

import logging
from typing import Any

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
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .api.apartment import DigitalstromApartment
from .api.client import DigitalstromClient
from .api.exceptions import CannotConnect, InvalidAuth, InvalidCertificate, ServerError
from .const import CONF_DSUID, CONF_SSL, DOMAIN, WEBSOCKET_WATCHDOG_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.UPDATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.COVER,
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.SCENE,
    Platform.CLIMATE,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
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
        system_dsuid = await client.get_system_dsuid()
        if len(system_dsuid) < 8:  # 34
            raise ConfigEntryError("Invalid system DSUID received")
        if system_dsuid != entry.unique_id:
            _LOGGER.warning(
                f"Your system DSUID changed from {entry.unique_id} to {system_dsuid}"
            )

            if (
                hass.config_entries.async_entry_for_domain_unique_id(
                    DOMAIN, system_dsuid
                )
                is not None
            ):
                _LOGGER.error(f"Multiple config entries found for DSUID {system_dsuid}")
                raise ConfigEntryError(
                    translation_key="config_entry_error_multiple_entries_for_dsuid",
                    translation_placeholders={"dsuid": system_dsuid},
                )
            else:
                await migrate_system_dsuid(hass, entry, system_dsuid)
        apartment = DigitalstromApartment(client, system_dsuid)
        hass.data[DOMAIN].setdefault(entry.unique_id, dict())
        hass.data[DOMAIN][entry.unique_id]["client"] = client
        hass.data[DOMAIN][entry.unique_id]["apartment"] = apartment
        await apartment.get_zones()
        await apartment.get_circuits()
        await apartment.get_devices()
    except (InvalidAuth, InvalidCertificate) as ex:
        raise ConfigEntryAuthFailed(ex) from ex
    except (CannotConnect, ServerError) as ex:
        raise ConfigEntryNotReady(ex) from ex

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def start_watchdog(event: Any = None) -> None:
        """Start websocket watchdog."""
        if "watchdog" not in hass.data[DOMAIN][entry.unique_id]:
            hass.data[DOMAIN][entry.unique_id]["watchdog"] = async_track_time_interval(
                hass,
                client.event_listener_watchdog,
                WEBSOCKET_WATCHDOG_INTERVAL,
                cancel_on_shutdown=True,
            )

    async def stop_watchdog(event: Any = None) -> None:
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
        if entry.unique_id in hass.data[DOMAIN] and (
            (remove_watchdog := hass.data[DOMAIN][entry.unique_id]["watchdog"])
            is not None
        ):
            remove_watchdog()
        await hass.data[DOMAIN][entry.unique_id]["client"].stop_event_listener()
        hass.data[DOMAIN].pop(entry.unique_id)
    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove config entry from a device if it's no longer present."""
    return True


async def migrate_system_dsuid(
    hass: HomeAssistant, config_entry: ConfigEntry, new_dsuid: str
) -> None:
    old_dsuid = config_entry.unique_id
    if old_dsuid is None or old_dsuid == new_dsuid or len(new_dsuid) < 8:
        return

    new_data = dict(config_entry.data)
    new_data[CONF_DSUID] = new_dsuid
    hass.config_entries.async_update_entry(
        config_entry, data=new_data, unique_id=new_dsuid
    )

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    device_entries = dr.async_entries_for_config_entry(
        device_registry, config_entry_id=config_entry.entry_id
    )
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry_id=config_entry.entry_id
    )
    for dev in device_entries:
        new_unique_id = None
        for identifier in dev.identifiers:
            domain, unique_id = identifier
            if domain == DOMAIN and old_dsuid in unique_id:
                new_unique_id = unique_id.replace(old_dsuid, new_dsuid)
                _LOGGER.debug(
                    f'Migrating identifier for device "{dev.name}": {unique_id} to {new_unique_id}'
                )
        if new_unique_id is not None:
            device_registry.async_update_device(
                dev.id, new_identifiers={(DOMAIN, new_unique_id)}
            )
    for ent in entity_entries:
        if old_dsuid in ent.unique_id:
            new_unique_id = ent.unique_id.replace(old_dsuid, new_dsuid)
            name = ent.original_name if ent.name is None else ent.name
            _LOGGER.debug(
                f'Migrating unique_id for entity "{name}": {ent.unique_id} to {new_unique_id}'
            )
            entity_registry.async_update_entity(
                ent.entity_id,
                new_unique_id=ent.unique_id.replace(old_dsuid, new_dsuid),
            )
