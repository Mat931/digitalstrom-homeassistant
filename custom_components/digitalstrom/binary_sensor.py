import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.channel import DigitalstromBinaryInputChannel
from .const import DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

BINARY_SENSORS_MAP: dict[int, BinarySensorEntityDescription] = {
    -1: BinarySensorEntityDescription(
        key="unknown",
        name="Unknown binary input",
        translation_key="unknown_binary_input",
    ),
    0: BinarySensorEntityDescription(
        key="0",
        name="Binary input",
        translation_key="binary_input",
    ),
    1: BinarySensorEntityDescription(
        key="1",
        name="Presence",
        translation_key="presence",
        device_class=BinarySensorDeviceClass.PRESENCE,
    ),
    2: BinarySensorEntityDescription(
        key="2",
        name="Brightness",
        translation_key="brightness",
        device_class=BinarySensorDeviceClass.LIGHT,
    ),
    3: BinarySensorEntityDescription(
        key="3",
        name="Presence in darkness",
        translation_key="presence_in_darkness",
        device_class=BinarySensorDeviceClass.PRESENCE,
    ),
    4: BinarySensorEntityDescription(
        key="4",
        name="Twilight",
        translation_key="twilight",
        device_class=BinarySensorDeviceClass.LIGHT,
    ),
    5: BinarySensorEntityDescription(
        key="5",
        name="Motion",
        translation_key="motion",
        device_class=BinarySensorDeviceClass.MOTION,
    ),
    6: BinarySensorEntityDescription(
        key="6",
        name="Motion in darkness",
        translation_key="motion_in_darkness",
        device_class=BinarySensorDeviceClass.MOTION,
    ),
    7: BinarySensorEntityDescription(
        key="7",
        name="Smoke",
        translation_key="smoke",
        device_class=BinarySensorDeviceClass.SMOKE,
    ),
    8: BinarySensorEntityDescription(
        key="8",
        name="Wind strength above limit",
        translation_key="wind_strength_above_limit",
        device_class=BinarySensorDeviceClass.SAFETY,
    ),
    9: BinarySensorEntityDescription(
        key="9",
        name="Rain",
        translation_key="rain",
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
    10: BinarySensorEntityDescription(
        key="10",
        name="Sun",
        translation_key="sun",
        device_class=BinarySensorDeviceClass.LIGHT,
    ),
    11: BinarySensorEntityDescription(
        key="11",
        name="Temperature below limit",
        translation_key="temperature_below_limit",
        device_class=BinarySensorDeviceClass.COLD,
    ),
    12: BinarySensorEntityDescription(
        key="12",
        name="Battery",
        translation_key="battery",
        device_class=BinarySensorDeviceClass.BATTERY,
    ),
    13: BinarySensorEntityDescription(
        key="13",
        name="Window",
        translation_key="window",
        device_class=BinarySensorDeviceClass.WINDOW,
    ),
    14: BinarySensorEntityDescription(
        key="14",
        name="Door",
        translation_key="door",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    15: BinarySensorEntityDescription(
        key="15",
        name="Window tilt",
        translation_key="window_tilt",
        device_class=BinarySensorDeviceClass.WINDOW,
    ),
    16: BinarySensorEntityDescription(
        key="16",
        name="Garage door",
        translation_key="garage_door",
        device_class=BinarySensorDeviceClass.GARAGE_DOOR,
    ),
    17: BinarySensorEntityDescription(
        key="17",
        name="Sun protection",
        translation_key="sun_protection",
        device_class=BinarySensorDeviceClass.SAFETY,
    ),
    18: BinarySensorEntityDescription(
        key="18",
        name="Frost",
        translation_key="frost",
        device_class=BinarySensorDeviceClass.COLD,
    ),
    19: BinarySensorEntityDescription(
        key="19",
        name="Heating system",
        translation_key="heating_system",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    20: BinarySensorEntityDescription(
        key="20",
        name="Warm water",
        translation_key="warm_water",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    21: BinarySensorEntityDescription(
        key="21",
        name="Initialization",
        translation_key="initialization",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    22: BinarySensorEntityDescription(
        key="22",
        name="Malfunction",
        translation_key="malfunction",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    23: BinarySensorEntityDescription(
        key="23",
        name="Service required",
        translation_key="service_required",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    apartment = hass.data[DOMAIN][config_entry.unique_id]["apartment"]
    binary_sensors = []
    for device in apartment.devices.values():
        for binary_sensor in device.binary_inputs.values():
            binary_sensors.append(DigitalstromBinarySensor(binary_sensor))
    _LOGGER.debug("Adding %i binary sensors", len(binary_sensors))
    async_add_entities(binary_sensors)


class DigitalstromBinarySensor(BinarySensorEntity, DigitalstromEntity):
    def __init__(self, binary_input_channel: DigitalstromBinaryInputChannel):
        super().__init__(binary_input_channel.device, f"S{binary_input_channel.index}")
        self._attributes: dict[str, Any] = {}
        self._state: bool | None = None
        self.channel = binary_input_channel
        self.index = binary_input_channel.index
        self.set_type(binary_input_channel.input_type)
        self._attr_suggested_display_precision = 1
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}_{self.index}"

    def set_type(self, sensor_type: int) -> None:
        self.sensor_type = sensor_type
        self.entity_description = BINARY_SENSORS_MAP.get(
            sensor_type, BINARY_SENSORS_MAP[-1]
        )
        self._attr_translation_key = self.entity_description.translation_key
        name = f" ({self.device.name})"
        if len(self.device.name) == 0:
            name = ""
        if len(self.device.get_parent().unique_device_names) < 2:
            name = ""
        self._attr_translation_placeholders = {"name": name}
        self._attr_device_class = self.entity_description.device_class
        self._attr_entity_category = self.entity_description.entity_category
        self._attr_has_entity_name = True
        if self.entity_description.key == "unknown":
            self._attr_translation_placeholders["sensor_type"] = str(sensor_type)
            self._attr_entity_registry_enabled_default = False
        if (
            (self.entity_description.key == "0")
            and (self.index == 0)
            and (self.device.button is not None)
            and (not self.device.button_used)
        ):
            self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.update_callback(self.channel.last_value)
        self.async_on_remove(
            self.channel.register_update_callback(self.update_callback)
        )

    def update_callback(self, state: bool | None, raw_state: int | None = None) -> None:
        if not self.enabled:
            return
        if state is None:
            self._state = None
        self._state = state != self.channel.inverted
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        # self.device.client.unregister_event_callback(self.event_callback)
        pass

    @property
    def is_on(self) -> bool | None:
        """Return the state of the sensor."""
        return self._state
