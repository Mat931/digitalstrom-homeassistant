import logging
from typing import Any

from homeassistant.components.scene import Scene as SceneEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.scene import DigitalstromZoneScene
from .const import CONF_DSUID, DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    client = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["client"]
    apartment = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["apartment"]

    zone_scenes = []
    for zone in apartment.zones.values():
        for zone_scene in zone.scenes.values():
            zone_scenes.append(DigitalstromZoneSceneEntity(zone_scene))
    _LOGGER.debug("Adding %i zone scenes", len(zone_scenes))
    async_add_entities(zone_scenes)


class DigitalstromZoneSceneEntity(SceneEntity):
    def __init__(self, zone_scene: DigitalstromZoneScene):
        self.scene = zone_scene
        self.entity_id = f"{DOMAIN}.{self.scene.zone.apartment.dsuid}_zone{self.scene.zone.zone_id}_group{self.scene.group}_scene{self.scene.number}"
        if self.scene.name is not None:
            self._attr_name = self.scene.name
        else:
            self._attr_name = (
                f"Unnamed scene (group {self.scene.group} scene {self.scene.number})"
            )
            self._attr_entity_registry_enabled_default = False
        self._attr_should_poll = False
        self._attr_unique_id: str = f"{self.scene.zone.apartment.dsuid}_zone{self.scene.zone.zone_id}_group{self.scene.group}_scene{self.scene.number}"

    async def async_activate(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.scene.call()

    @property
    def device_info(self) -> dict:
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{self.scene.zone.apartment.dsuid}_zone{self.scene.zone.zone_id}",
                )
            },
            name=self.scene.zone.name,
            model="Zone",
            manufacturer="digitalSTROM",
            suggested_area=self.scene.zone.name,
            via_device=(DOMAIN, self.scene.zone.apartment.dsuid),
        )
