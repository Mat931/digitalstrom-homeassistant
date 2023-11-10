import logging

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.apartment import DigitalstromButton
from .const import CONF_DSUID, DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

BUTTON_PRESS_TYPES = {
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
    def __init__(self, button) -> None:
        super().__init__(button.device, "E")
        self.channel = button
        self._attr_name = "Button"
        self._attr_device_class = EventDeviceClass.BUTTON
        self._attr_event_types = list(
            set(
                ["call_device_scene", "call_group_scene", "unknown"]
                + list(BUTTON_PRESS_TYPES.values())
            )
        )
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}"

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
