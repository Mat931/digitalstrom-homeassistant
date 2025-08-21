import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    DEGREE,
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfMass,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSoundPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.channel import DigitalstromMeterSensorChannel, DigitalstromSensorChannel
from .const import CONF_DSUID, DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

SENSORS_MAP: dict[int, SensorEntityDescription] = {
    -1: SensorEntityDescription(
        key="unknown",
        name="Unknown sensor",
    ),
    4: SensorEntityDescription(
        key="4",
        name="Active Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    5: SensorEntityDescription(
        key="5",
        name="Output Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    6: SensorEntityDescription(
        key="6",
        name="Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    9: SensorEntityDescription(
        key="9",
        name="Room Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    10: SensorEntityDescription(
        key="10",
        name="Outdoor Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    11: SensorEntityDescription(
        key="11",
        name="Room Brightness",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    12: SensorEntityDescription(
        key="12",
        name="Outdoor Brightness",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    13: SensorEntityDescription(
        key="13",
        name="Room Relative Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    14: SensorEntityDescription(
        key="14",
        name="Outdoor Relative Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    15: SensorEntityDescription(
        key="15",
        name="Air pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    16: SensorEntityDescription(
        key="16",
        name="Wind gust speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    17: SensorEntityDescription(
        key="17",
        name="Wind gust direction",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    18: SensorEntityDescription(
        key="18",
        name="Wind speed average",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    19: SensorEntityDescription(
        key="19",
        name="Wind direction",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    20: SensorEntityDescription(
        key="20",
        name="Precipitation intensity of last hour",
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    21: SensorEntityDescription(
        key="21",
        name="Room Carbon Dioxide Concentration",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    22: SensorEntityDescription(
        key="22",
        name="Room Carbon Monoxide Concentration",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    25: SensorEntityDescription(
        key="25",
        name="Sound Pressure Level",
        native_unit_of_measurement=UnitOfSoundPressure.DECIBEL,
        device_class=SensorDeviceClass.SOUND_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    50: SensorEntityDescription(
        key="50",
        name="Room Temperature Set Point",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    51: SensorEntityDescription(
        key="51",
        name="Room Temperature Control Variable",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    64: SensorEntityDescription(
        key="64",
        name="Output Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    65: SensorEntityDescription(
        key="65",
        name="Apparent Power",
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    66: SensorEntityDescription(
        key="66",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    67: SensorEntityDescription(
        key="67",
        name="Brightness",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    68: SensorEntityDescription(
        key="68",
        name="Relative Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    69: SensorEntityDescription(
        key="69",
        name="Generated Active Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    70: SensorEntityDescription(
        key="70",
        name="Generated Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    71: SensorEntityDescription(
        key="71",
        name="Water Quantity",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    72: SensorEntityDescription(
        key="72",
        name="Water Flow Rate",
        # Conversion from "L/s" to CUBIC_METERS_PER_HOUR: (value * 3.6)
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    73: SensorEntityDescription(
        key="73",
        name="Length",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    74: SensorEntityDescription(
        key="74",
        name="Mass",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    75: SensorEntityDescription(
        key="75",
        name="Time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    76: SensorEntityDescription(
        key="76",
        name="Sun azimuth",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    77: SensorEntityDescription(
        key="77",
        name="Sun elevation",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    apartment = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["apartment"]
    circuit_sensors = []
    for circuit in apartment.circuits.values():
        for sensor in circuit.sensors.values():
            circuit_sensors.append(DigitalstromMeterSensor(sensor))
    _LOGGER.debug("Adding %i circuit sensors", len(circuit_sensors))
    async_add_entities(circuit_sensors)

    sensors = []
    for device in apartment.devices.values():
        for sensor in device.sensors.values():
            sensors.append(DigitalstromSensor(sensor))
    _LOGGER.debug("Adding %i sensors", len(sensors))
    async_add_entities(sensors)


class DigitalstromSensor(SensorEntity, DigitalstromEntity):
    def __init__(self, sensor_channel: DigitalstromSensorChannel):
        super().__init__(sensor_channel.device, f"S{sensor_channel.index}")
        self._attributes: dict[str, Any] = {}
        self._state: int | None = None
        self.channel = sensor_channel
        self.index = sensor_channel.index
        self.valid = False
        self.set_type(sensor_channel.sensor_type)
        self._attr_suggested_display_precision = 1
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}_{self.index}"

    def set_type(self, sensor_type: int) -> None:
        self.sensor_type = sensor_type
        self.entity_description = SENSORS_MAP.get(sensor_type, SENSORS_MAP[-1])
        self._attr_name = self.entity_description.name
        self._attr_has_entity_name = True
        if self.entity_description.key == "unknown":
            self._attr_name += f" (type {sensor_type})"
            self._attr_entity_registry_enabled_default = False
        self._attr_native_unit_of_measurement = (
            self.entity_description.native_unit_of_measurement
        )
        self._attr_device_class = self.entity_description.device_class
        self._attr_state_class = self.entity_description.state_class

    async def async_added_to_hass(self) -> None:
        self.update_callback(self.channel.last_value)
        self.async_on_remove(
            self.channel.register_update_callback(self.update_callback)
        )

    def update_callback(self, state: float, raw_state: float = None) -> None:
        if state is None:
            return
        if self.entity_description.key == "72":
            # Water Flow Rate: Convert from L/s to m3/h
            state *= 3.6
        self._state = state
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        # self.device.client.unregister_event_callback(self.event_callback)
        pass

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self._state


class DigitalstromMeterSensor(SensorEntity):
    def __init__(self, sensor_channel: DigitalstromMeterSensorChannel):
        self.channel = sensor_channel
        self.circuit = sensor_channel.device
        self._attr_unique_id: str = f"{self.circuit.dsuid}_{self.channel.index}"
        self.entity_id = f"{DOMAIN}.{self._attr_unique_id}"
        self._attr_should_poll = True
        self._has_state = False
        self._attributes: dict[str, Any] = {}
        self._state: int | None = None
        self.valid = False
        self.entity_id = f"{DOMAIN}.{self.circuit.dsuid}_{self.channel.index}"
        self._state = None
        self._attr_has_entity_name = True

        if self.channel.index == "power":
            self._attr_name = "Power"
            self._attr_native_unit_of_measurement = UnitOfPower.WATT
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 0
        elif self.channel.index == "energy":
            self._attr_name = "Energy"
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_suggested_display_precision = 3

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.circuit.dsuid)},
            name=self.circuit.name,
            manufacturer=self.circuit.manufacturer,
            model=self.circuit.hw_name,
            hw_version=self.circuit.hw_version,
            sw_version=self.circuit.sw_version,
        )

    @property
    def available(self) -> bool:
        return self.circuit.available

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self._state

    async def async_update(self, **kwargs) -> None:
        value = await self.channel.get_value()
        if self.channel.index == "energy" and value is not None:
            self._state = value / 3600000
        else:
            self._state = value
