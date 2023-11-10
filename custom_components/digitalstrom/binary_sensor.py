import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DSUID, DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

BINARY_SENSORS_MAP: dict[int, BinarySensorEntityDescription] = {
    -1: BinarySensorEntityDescription(
        key="unknown",
        name="Unknown",
    ),
    0: BinarySensorEntityDescription(
        key="0",
        name="Binary input",
    ),
    1: BinarySensorEntityDescription(
        key="1",
        name="Presence",
        device_class=BinarySensorDeviceClass.PRESENCE,
    ),
    2: BinarySensorEntityDescription(
        key="2",
        name="Brightness",
        device_class=BinarySensorDeviceClass.LIGHT,
    ),
    3: BinarySensorEntityDescription(
        key="3",
        name="Presence in darkness",
        device_class=BinarySensorDeviceClass.PRESENCE,
    ),
    4: BinarySensorEntityDescription(
        key="4",
        name="Twilight",
        device_class=BinarySensorDeviceClass.LIGHT,
    ),
    5: BinarySensorEntityDescription(
        key="5",
        name="Motion",
        device_class=BinarySensorDeviceClass.MOTION,
    ),
    6: BinarySensorEntityDescription(
        key="6",
        name="Motion in darkness",
        device_class=BinarySensorDeviceClass.MOTION,
    ),
    7: BinarySensorEntityDescription(
        key="7",
        name="Smoke",
        device_class=BinarySensorDeviceClass.SMOKE,
    ),
    8: BinarySensorEntityDescription(
        key="8",
        name="Wind strength above limit",
        device_class=BinarySensorDeviceClass.SAFETY,
    ),
    9: BinarySensorEntityDescription(
        key="9",
        name="Rain",
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
    10: BinarySensorEntityDescription(
        key="10",
        name="Sun",
        device_class=BinarySensorDeviceClass.LIGHT,
    ),
    11: BinarySensorEntityDescription(
        key="11",
        name="Temperature below limit",
        device_class=BinarySensorDeviceClass.COLD,
    ),
    12: BinarySensorEntityDescription(
        key="12",
        name="Battery",
        device_class=BinarySensorDeviceClass.BATTERY,
    ),
    13: BinarySensorEntityDescription(
        key="13",
        name="Window",
        device_class=BinarySensorDeviceClass.WINDOW,
    ),
    14: BinarySensorEntityDescription(
        key="14",
        name="Door",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    15: BinarySensorEntityDescription(
        key="15",
        name="Window tilt",
        device_class=BinarySensorDeviceClass.WINDOW,
    ),
    16: BinarySensorEntityDescription(
        key="16",
        name="Garage door",
        device_class=BinarySensorDeviceClass.GARAGE_DOOR,
    ),
    17: BinarySensorEntityDescription(
        key="17",
        name="Sun protection",
        device_class=BinarySensorDeviceClass.SAFETY,
    ),
    18: BinarySensorEntityDescription(
        key="18",
        name="Frost",
        device_class=BinarySensorDeviceClass.COLD,
    ),
    19: BinarySensorEntityDescription(
        key="19",
        name="Heating system",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    20: BinarySensorEntityDescription(
        key="20",
        name="Warm water",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    21: BinarySensorEntityDescription(
        key="21",
        name="Initialization",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    22: BinarySensorEntityDescription(
        key="22",
        name="Malfunction",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    23: BinarySensorEntityDescription(
        key="23",
        name="Service required",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    client = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["client"]
    apartment = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["apartment"]
    binary_sensors = []
    for device in apartment.devices.values():
        for binary_sensor in device.binary_inputs.values():
            binary_sensors.append(DigitalstromBinarySensor(binary_sensor))
    _LOGGER.debug("Adding %i binary sensors", len(binary_sensors))
    async_add_entities(binary_sensors)


class DigitalstromBinarySensor(BinarySensorEntity, DigitalstromEntity):
    def __init__(self, binary_input_channel):
        super().__init__(binary_input_channel.device, f"S{binary_input_channel.index}")
        self._attributes: dict[str, Any] = {}
        self._state: int | None = None
        self.channel = binary_input_channel
        self.index = binary_input_channel.index
        self.valid = False
        self.inverted = binary_input_channel.inverted
        self.set_type(binary_input_channel.input_type)
        self._attr_suggested_display_precision = 1
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}_{self.index}"

    def set_type(self, sensor_type):
        self.sensor_type = sensor_type
        self.entity_description = BINARY_SENSORS_MAP.get(
            sensor_type, BINARY_SENSORS_MAP[-1]
        )
        self._attr_name = self.entity_description.name
        self._attr_device_class = self.entity_description.device_class
        self._attr_entity_category = self.entity_description.entity_category

    def set_state(self, state: bool, raw_state, valid=True):
        self._state = state if valid else None
        self.valid = valid
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.update_callback(self.channel.last_state)
        self.async_on_remove(
            self.channel.register_update_callback(self.update_callback)
        )

    def update_callback(self, state, raw_state=None):
        self._state = state
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        # self.device.client.unregister_event_callback(self.event_callback)
        pass

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        return self._state
