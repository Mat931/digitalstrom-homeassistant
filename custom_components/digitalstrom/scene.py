import logging
from typing import Any

from homeassistant.components.scene import Scene as SceneEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.scene import DigitalstromZoneScene
from .const import DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

GROUP_MAP: dict[str, str] = {
    "g1": "zone_scene_light",
    "g1n": "zone_scene_light_named",
    "g1s0": "zone_scene_light_off",
    "g1p": "zone_scene_light_preset",
    "g2": "zone_scene_cover",
    "g2n": "zone_scene_cover_named",
    "g2s0": "zone_scene_cover_off",
    "g2p": "zone_scene_cover_preset",
    "g3": "zone_scene_heating",
    "g3n": "zone_scene_heating_named",
    "g4": "zone_scene_audio",
    "g4n": "zone_scene_audio_named",
    "g4s0": "zone_scene_audio_off",
    "g4p": "zone_scene_audio_preset",
    "g5": "zone_scene_video",
    "g5n": "zone_scene_video_named",
    "g5s0": "zone_scene_video_off",
    "g5p": "zone_scene_video_preset",
    "g6": "zone_scene_security",
    "g6n": "zone_scene_security_named",
    "g7": "zone_scene_access",
    "g7n": "zone_scene_access_named",
    "g8": "zone_scene_joker",
    "g8n": "zone_scene_joker_named",
    "g9": "zone_scene_cooling",
    "g9n": "zone_scene_cooling_named",
    "g10": "zone_scene_ventilation",
    "g10n": "zone_scene_ventilation_named",
    "g11": "zone_scene_window",
    "g11n": "zone_scene_window_named",
    "g12": "zone_scene_recirculation",
    "g12n": "zone_scene_recirculation_named",
    "g13": "zone_scene_awnings",
    "g13n": "zone_scene_awnings_named",
    "g48": "zone_scene_temperature_control",
    "g48n": "zone_scene_temperature_control_named",
}

SCENE_TO_PRESET_MAP: dict[int, int] = {
    0: 0,
    5: 1,
    17: 2,
    18: 3,
    19: 4,
    32: 10,
    33: 11,
    20: 12,
    21: 13,
    22: 14,
    34: 20,
    35: 21,
    23: 22,
    24: 23,
    25: 24,
    36: 30,
    37: 31,
    26: 32,
    27: 33,
    28: 34,
    38: 40,
    39: 41,
    29: 42,
    30: 43,
    31: 44,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    apartment = hass.data[DOMAIN][config_entry.unique_id]["apartment"]

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
        self._attr_has_entity_name = True
        if self.scene.name is not None:
            self._attr_translation_placeholders = {"name": self.scene.name}
            self._attr_translation_key = GROUP_MAP.get(
                f"g{self.scene.group}n", "zone_scene_unknown_named"
            )
        else:
            self._attr_translation_placeholders = {"scene": str(self.scene.number)}
            key = GROUP_MAP.get(f"g{self.scene.group}", "zone_scene_unknown")
            if self.scene.number in SCENE_TO_PRESET_MAP.keys():
                key = GROUP_MAP.get(f"g{self.scene.group}p", key)
                self._attr_translation_placeholders["preset"] = str(
                    SCENE_TO_PRESET_MAP.get(self.scene.number, "")
                )
            self._attr_translation_key = GROUP_MAP.get(
                f"g{self.scene.group}s{self.scene.number}", key
            )

            if self.scene.group not in [1, 2]:
                self._attr_entity_registry_enabled_default = False
        if self._attr_translation_key in [
            "zone_scene_unknown",
            "zone_scene_unknown_named",
        ]:
            self._attr_translation_placeholders["group"] = str(self.scene.group)
        self._attr_should_poll = False
        self._attr_unique_id: str = (
            f"{self.scene.zone.apartment.dsuid}_zone{self.scene.zone.zone_id}_group{self.scene.group}_scene{self.scene.number}"
        )

    async def async_activate(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.scene.call()

    @property
    def device_info(self) -> DeviceInfo:
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
