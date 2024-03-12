from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.apartment import DigitalstromApartment
from .api.channel import DigitalstromOutputChannel
from .api.exceptions import ServerError
from .const import CONF_DSUID, DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

APARTMENT_SCENES: dict[int, str] = {
    64: "Auto Standby",
    65: "Panic",
    67: "Standby",
    68: "Deep Off",
    69: "Sleeping",
    70: "Wakeup",
    71: "Present",
    72: "Absent",
    73: "Door Bell",
    74: "Alarm 1",
    75: "Zone Active",
    76: "Fire",
    83: "Alarm 2",
    84: "Alarm 3",
    85: "Alarm 4",
    86: "Wind",
    87: "No Wind",
    88: "Rain",
    89: "No Rain",
    90: "Hail",
    91: "No Hail",
    92: "Pollution",
    93: "Burglary",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    client = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["client"]
    apartment = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["apartment"]

    switches = []
    for device in apartment.devices.values():
        for channel in device.output_channels.values():
            if channel.channel_type == "powerLevel":
                switches.append(DigitalstromSwitch(channel))
    _LOGGER.debug("Adding %i switches", len(switches))
    async_add_entities(switches)

    apartment_scenes = []
    for scene_id, scene_name in APARTMENT_SCENES.items():
        apartment_scenes.append(
            DigitalstromApartmentScene(apartment, scene_id, scene_name)
        )
    _LOGGER.debug("Adding %i apartment scenes", len(apartment_scenes))
    async_add_entities(apartment_scenes)


class DigitalstromSwitch(SwitchEntity, DigitalstromEntity):
    def __init__(self, channel: DigitalstromOutputChannel):
        super().__init__(channel.device, f"O{channel.index}")
        self.channel = channel
        self.device = channel.device
        self.client = self.device.client
        self._attr_should_poll = True
        self.last_value = None
        self._attr_has_entity_name = False
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}_{channel.index}"
        self._attr_name = self.device.name
        self.supports_target_value = True

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

    async def async_update(self, **kwargs: Any) -> None:
        if not self.supports_target_value:
            return
        try:
            result = await self.client.request(
                f"property/getFloating?path=/apartment/zones/zone{self.device.zone_id}/devices/{self.device.dsuid}/status/outputs/powerState/targetValue"
            )
            self.last_value = result.get("value", None)
        except ServerError:
            self.supports_target_value = False


class DigitalstromApartmentScene(SwitchEntity):
    def __init__(
        self, apartment: DigitalstromApartment, scene_id: int, scene_name: str
    ):
        self.scene_id = scene_id
        self.scene_name = scene_name
        self.apartment = apartment
        self.client = self.apartment.client
        self.entity_id = f"{DOMAIN}.{self.apartment.dsuid}_{self.scene_id}"
        self._attr_name = self.scene_name
        self._attr_should_poll = False
        self._attr_unique_id: str = f"{self.apartment.dsuid}_scene{self.scene_id}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.client.request(f"apartment/callScene?sceneNumber={self.scene_id}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.client.request(f"apartment/undoScene?sceneNumber={self.scene_id}")

    @property
    def device_info(self) -> dict:
        return DeviceInfo(
            identifiers={(DOMAIN, self.apartment.dsuid)},
            name="Apartment",
            manufacturer="digitalSTROM",
        )
