import logging

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.channel import DigitalstromButtonChannel
from .const import DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

BUTTON_PRESS_TYPES: dict[int, str] = {
    0: "single_press",
    1: "double_press",
    2: "triple_press",
    3: "quadruple_press",
    4: "hold_start",
    5: "hold_repeat",
    6: "hold_end",
    7: "single_click",
    8: "double_click",
    9: "triple_click",
    11: "single_press",
    12: "single_press",
    14: "single_press",
}

GROUP_MAP: dict[int, str] = {
    1: "button_event_light",
    2: "button_event_cover",
    3: "button_event_heating",
    4: "button_event_audio",
    5: "button_event_video",
    6: "button_event_security",
    7: "button_event_access",
    8: "button_event_joker",
    9: "button_event_cooling",
    10: "button_event_ventilation",
    11: "button_event_window",
    12: "button_event_recirculation",
    13: "button_event_awnings",
    48: "button_event_temperature_control",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the event platform."""
    apartment = hass.data[DOMAIN][config_entry.unique_id]["apartment"]
    events = []
    for device in apartment.devices.values():
        if device.button:
            events.append(DigitalstromButtonEvent(device.button))
    _LOGGER.debug("Adding %i events", len(events))
    async_add_entities(events)


class DigitalstromButtonEvent(EventEntity, DigitalstromEntity):
    def __init__(self, button: DigitalstromButtonChannel) -> None:
        super().__init__(button.device, "E")
        self.channel = button
        self.group = button.device.button_group
        self._attr_device_class = EventDeviceClass.BUTTON
        self._attr_event_types = list(
            set(
                ["call_device_scene", "call_group_scene", "unknown"]
                + list(BUTTON_PRESS_TYPES.values())
            )
        )
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}"
        if not self.device.button_used:
            self._attr_entity_registry_enabled_default = False
        self._attr_has_entity_name = True
        self._attr_translation_key = GROUP_MAP.get(self.group, "button_event_unknown")
        name = f" ({self.device.name})"
        if len(self.device.name) == 0:
            name = ""
        if len(self.device.get_parent().unique_device_names) < 2:
            name = ""
        self._attr_translation_placeholders = {"name": name}
        if self._attr_translation_key == "button_event_unknown":
            self._attr_translation_placeholders["group"] = str(self.group)

    @callback
    def update_callback(self, event: str, extra_data: dict[str, int]) -> None:
        if not self.enabled:
            return
        if event == "button":
            event = BUTTON_PRESS_TYPES.get(extra_data["click_type"], "unknown")
            if not event == "unknown":
                extra_data.pop("click_type")
        self._trigger_event(event, extra_data)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.channel.register_update_callback(self.update_callback)
        )
