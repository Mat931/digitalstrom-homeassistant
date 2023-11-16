from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DSUID, DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the event platform."""
    client = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["client"]
    apartment = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["apartment"]
    switches = []
    for device in apartment.devices.values():
        for channel in device.output_channels.values():
            if channel.channel_type == "powerLevel":
                switches.append(DigitalstromSwitch(channel))
    _LOGGER.debug("Adding %i switches", len(switches))
    async_add_entities(switches)


class DigitalstromSwitch(SwitchEntity, DigitalstromEntity):
    def __init__(self, channel):
        super().__init__(channel.device, f"O{channel.index}")
        self.channel = channel
        self.device = channel.device
        self.client = self.device.client
        self._attr_should_poll = True
        self.last_value = None
        self._attr_has_entity_name = False
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}_{channel.index}"
        self._attr_name = self.device.name

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if self.last_value is None:
            return None
        return self.last_value > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.client.request(
            f"device/setOutputChannelValue?dsuid={self.device.dsuid}&channelvalues={self.channel.channel_id}=100&applyNow=1"
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.client.request(
            f"device/setOutputChannelValue?dsuid={self.device.dsuid}&channelvalues={self.channel.channel_id}=0&applyNow=1"
        )

    async def async_update(self, **kwargs: Any):
        result = await self.client.request(
            f"property/getFloating?path=/apartment/zones/zone{self.device.zone_id}/devices/{self.device.dsuid}/status/outputs/powerState/targetValue"
        )
        self.last_value = result.get("value", None)
