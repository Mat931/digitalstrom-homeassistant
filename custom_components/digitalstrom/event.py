import logging

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.channel import DigitalstromButtonChannel
from .const import CONF_DSUID, DOMAIN
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
    1: "Light",
    2: "Cover",
    3: "Heating",
    4: "Audio",
    5: "Video",
    8: "Joker",
    9: "Cooling",
    10: "Ventilation",
    11: "Window",
    12: "Recirculation",
    13: "Awnings",
    48: "Temperature Control",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the event platform."""
    client = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["client"]
    apartment = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["apartment"]
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
        self._attr_name = self.device.name
        self._attr_has_entity_name = False
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
        if self.group not in [0, 255]:
            group = GROUP_MAP.get(self.group, f"Group {self.group}")
            self._attr_name += f" ({group})"

    @callback
    def update_callback(self, event: str, extra_data: dict = None) -> None:
        if event == "button":
            event = BUTTON_PRESS_TYPES.get(extra_data["click_type"], "unknown")
            if not event == "unknown":
                extra_data.pop("click_type")
        self._trigger_event(event, extra_data)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.channel.register_update_callback(self.update_callback)
        )
