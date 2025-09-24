import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.channel import DigitalstromOutputChannel
from .api.scene import DigitalstromApartmentScene
from .const import (
    APARTMENT_SCENE_UPDATE_INTERVAL,
    APARTMENT_SCENE_UPDATE_INTERVAL_IF_CHANGED,
    DOMAIN,
)
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)  # TODO: 10 seconds
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    apartment = hass.data[DOMAIN][config_entry.unique_id]["apartment"]

    switches = []
    for device in apartment.devices.values():
        for channel in device.output_channels.values():
            if channel.channel_type == "powerLevel":
                switches.append(DigitalstromSwitch(channel))
    _LOGGER.debug("Adding %i switches", len(switches))
    async_add_entities(switches)

    apartment_scenes = []
    for apartment_scene in apartment.scenes:
        apartment_scenes.append(DigitalstromApartmentSceneSwitch(apartment_scene))
    _LOGGER.debug("Adding %i apartment scenes", len(apartment_scenes))
    async_add_entities(apartment_scenes)


class DigitalstromSwitch(SwitchEntity, DigitalstromEntity):
    def __init__(self, channel: DigitalstromOutputChannel):
        super().__init__(channel.device, f"O{channel.index}")
        self.channel = channel
        self.device = channel.device
        self.client = self.device.client
        self._attr_should_poll = True
        self.last_power_state: float | None = None
        self._attr_has_entity_name = False
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}_{channel.index}"
        self._attr_name = self.device.name

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if self.last_power_state is None:
            return None
        return self.last_power_state > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.channel.set_value(100)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.channel.set_value(0)

    async def async_update(self, **kwargs: Any) -> None:
        if self.available:
            self.last_power_state = await self.device.get_power_state()
        elif self.device.reading_power_state_supported == False:
            self.device.reading_power_state_supported = None


class DigitalstromApartmentSceneSwitch(SwitchEntity):
    def __init__(self, apartment_scene: DigitalstromApartmentScene):
        self.scene = apartment_scene
        self.entity_id = (
            f"{DOMAIN}.{self.scene.apartment.dsuid}_{self.scene.call_number}"
        )
        self._attr_has_entity_name = True
        self._attr_translation_key = self.scene.name.lower().replace(" ", "_")
        self._attr_should_poll = True
        self._attr_unique_id: str = (
            f"{self.scene.apartment.dsuid}_scene{self.scene.call_number}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self.scene.last_value

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.scene.call(self.scene.call_number == 90)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.scene.undo(self.scene.call_number == 90)

    async def async_update(self, **kwargs: Any) -> None:
        if self.scene.state_name is None:
            return
        do_update = False
        timestamp = datetime.now()
        if self.scene.force_update:
            do_update = True
        elif (
            self.scene.last_update_timestamp == self.scene.last_change_timestamp
            and self.scene.last_update_timestamp
            < timestamp - APARTMENT_SCENE_UPDATE_INTERVAL_IF_CHANGED
        ):
            do_update = True
        elif (
            self.scene.last_update_timestamp
            < timestamp - APARTMENT_SCENE_UPDATE_INTERVAL
        ):
            do_update = True
        if do_update:
            await self.scene.get_value()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.scene.apartment.dsuid)},
            name="Apartment",
            model="Apartment",
            manufacturer="digitalSTROM",
        )
